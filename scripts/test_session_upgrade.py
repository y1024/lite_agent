"""
session 升级 (软归档 + kv_state) 的单元测试。

运行: python scripts/test_session_upgrade.py
不依赖 pytest, 纯 assert + 自带 main, 符合项目零外部测试依赖的风格。

覆盖委员会 glm-5.2 建议的三类验证:
  1. 老 DB 自动补列迁移 (kv_state 列)
  2. kv_state 状态读写 (set_state/get_state/del_state)
  3. 软归档: 不删 messages + archived 恢复重置 chatting + 历史连续
"""
import sys
import os
import time
import sqlite3
import tempfile

# 项目根加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from session import SessionManager

_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ✅ {name}")
    else:
        _failed += 1
        print(f"  ❌ {name}")


def _cleanup_db(path):
    """清理临时 DB 及 WAL/SHM 旁文件 (Windows 下连接可能未立即释放, 容错)"""
    for p in [path, path + "-wal", path + "-shm"]:
        try:
            os.remove(p)
        except OSError:
            pass


def fresh_mgr():
    """返回一个用临时 DB 的 SessionManager"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return SessionManager(db_path=path, ttl_minutes=30, max_history=20), path


def test_old_db_migration():
    """1. 老 DB (无 kv_state 列) 应自动补列"""
    print("\n[1] 老 DB 自动补列迁移")
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # 模拟老 schema: sessions 表没有 kv_state 列
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE sessions (
            session_key TEXT PRIMARY KEY, goal TEXT DEFAULT '',
            status TEXT DEFAULT 'chatting', created_at REAL, updated_at REAL,
            tool_calls INTEGER DEFAULT 0, token_usage INTEGER DEFAULT 0
        );
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_key TEXT, role TEXT,
            content TEXT, reasoning_content TEXT, tool_call_id TEXT DEFAULT '',
            name TEXT DEFAULT '', tool_calls_json TEXT DEFAULT '', created_at REAL
        );
    """)
    conn.execute("INSERT INTO sessions (session_key, status) VALUES ('old:sess', 'chatting')")
    conn.commit()
    cols_before = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    conn.close()
    check("老 DB 初始无 kv_state 列", "kv_state" not in cols_before)

    # 初始化 SessionManager 应自动 ALTER 补列
    mgr = SessionManager(db_path=path)
    conn = sqlite3.connect(path)
    cols_after = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    conn.close()
    check("初始化后自动补 kv_state 列", "kv_state" in cols_after)

    # 老 session 仍可正常恢复
    s = mgr.get_or_create("old:sess")
    check("老 session 恢复后 kv_state 为空 dict", s.kv_state == {})
    _cleanup_db(path)


def test_kv_state_rw():
    """2. kv_state 读写 + 持久化"""
    print("\n[2] kv_state 状态读写")
    mgr, path = fresh_mgr()
    key = "test:kv"

    # set + get
    mgr.set_state(key, "stock_price", 12.5)
    check("get_state 读回 set 的值", mgr.get_state(key, "stock_price") == 12.5)
    check("get_state 不存在的 key 返回 default", mgr.get_state(key, "nope", "def") == "def")

    # 覆盖更新
    mgr.set_state(key, "stock_price", 13.0)
    check("覆盖更新生效", mgr.get_state(key, "stock_price") == 13.0)

    # 多 key 共存
    mgr.set_state(key, "count", 100)
    check("多 key 共存", mgr.get_state(key, "count") == 100 and mgr.get_state(key, "stock_price") == 13.0)

    # del
    existed = mgr.del_state(key, "count")
    check("del_state 返回曾存在=True", existed is True)
    check("del 后 get 返回 default", mgr.get_state(key, "count", None) is None)
    existed2 = mgr.del_state(key, "count")
    check("del 不存在的 key 返回 False", existed2 is False)

    # 持久化: 清缓存后重新加载仍能读到
    mgr._cache.clear()
    s = mgr.get_or_create(key)
    check("清缓存重载后 kv_state 持久化保留", s.kv_state.get("stock_price") == 13.0)
    _cleanup_db(path)


def test_soft_archive_preserves_messages():
    """3a. 软归档不删 messages"""
    print("\n[3a] 软归档保留 messages")
    mgr, path = fresh_mgr()
    key = "test:archive"
    s = mgr.get_or_create(key)
    mgr.add_message(key, "user", "聊了 OpenRath 文章")
    mgr.add_message(key, "assistant", "结论: session 升级为状态追踪器")

    # 直接查 DB, 确认消息已落库
    conn = sqlite3.connect(path)
    n_before = conn.execute("SELECT COUNT(*) FROM messages WHERE session_key=?", (key,)).fetchone()[0]
    conn.close()
    check("归档前 messages 有 2 条", n_before == 2)

    # 模拟过期: 把 updated_at 拨到 TTL 之前
    with mgr._lock:
        s.updated_at = time.time() - mgr.ttl_seconds - 1
    mgr.cleanup_expired()

    # 归档后 messages 仍在 (核心: 不再 DELETE)
    conn = sqlite3.connect(path)
    n_after = conn.execute("SELECT COUNT(*) FROM messages WHERE session_key=?", (key,)).fetchone()[0]
    status = conn.execute("SELECT status FROM sessions WHERE session_key=?", (key,)).fetchone()[0]
    conn.close()
    check("归档后 messages 仍为 2 条 (未删)", n_after == 2)
    check("归档后 session status='archived'", status == "archived")
    _cleanup_db(path)


def test_archived_restore_resets_chatting():
    """3b. archived session 被重新激活时重置 chatting + 历史连续"""
    print("\n[3b] archived 恢复重置 chatting + 历史连续")
    mgr, path = fresh_mgr()
    key = "test:restore"
    mgr.add_message(key, "user", "之前的对话内容")
    mgr.add_message(key, "assistant", "之前的回复")

    # 归档
    with mgr._lock:
        mgr.get_or_create(key).updated_at = time.time() - mgr.ttl_seconds - 1
    mgr.cleanup_expired()
    mgr._cache.clear()  # 模拟新请求, 从 DB 恢复

    # 重新激活
    s = mgr.get_or_create(key)
    check("恢复后 status 重置为 chatting", s.status == "chatting")
    check("恢复后历史消息连续 (2 条)", len(s.messages) == 2)
    check("恢复后第一条仍是之前 user 消息", s.messages[0]["content"] == "之前的对话内容")
    # DB 中 status 也应为 chatting
    conn = sqlite3.connect(path)
    db_status = conn.execute("SELECT status FROM sessions WHERE session_key=?", (key,)).fetchone()[0]
    conn.close()
    check("DB 中 status 也已重置 chatting", db_status == "chatting")
    _cleanup_db(path)


def test_working_not_archived():
    """3c. working 状态的 session 不被归档"""
    print("\n[3c] working 状态不被归档")
    mgr, path = fresh_mgr()
    key = "test:working"
    mgr.set_goal(key, "执行某个目标")
    with mgr._lock:
        mgr.get_or_create(key).updated_at = time.time() - mgr.ttl_seconds - 1
    mgr.cleanup_expired()
    s = mgr.get_or_create(key)
    check("working 状态 session 超时仍为 working (不归档)", s.status == "working")
    _cleanup_db(path)


def main():
    print("=" * 60)
    print("session 升级测试 (软归档 + kv_state)")
    print("=" * 60)
    test_old_db_migration()
    test_kv_state_rw()
    test_soft_archive_preserves_messages()
    test_archived_restore_resets_chatting()
    test_working_not_archived()
    print("\n" + "=" * 60)
    print(f"结果: ✅ {_passed} 通过, ❌ {_failed} 失败")
    print("=" * 60)
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
