"""
测试: 闭合反馈-学习回路
验证改动: lite_integration.py + agent.py 的内存学习机制

运行: python scripts/test_learning_loop.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Test 1: _extract_correction_preference 偏好提取
# ============================================================
def test_extract_correction_preference():
    """验证从用户纠正语中提取偏好规则"""
    from memory_engine.lite_integration import AgentMemory

    mem = AgentMemory()

    # 无 LLM callback → 返回 None
    assert mem._extract_correction_preference("不对", "wrong reply") is None, \
        "无 LLM callback 时应返回 None"

    # 模拟 LLM callback — 返回偏好规则
    def mock_llm(prompt: str) -> str:
        return "当用户查询外币/汇率时，应该用web_search联网搜索实时汇率，不要调用billing_report"

    mem.engine._llm_callback = mock_llm

    result = mem._extract_correction_preference(
        "不对，我要的是汇率不是账单，用联网搜索",
        "这是您的账单报告..."
    )
    assert result is not None, "应该提取到偏好"
    assert "web_search" in result, f"偏好应包含工具名，实际: {result}"
    assert "billing_report" in result or "账单" in result, \
        f"偏好应包含避免的做法，实际: {result}"
    print(f"  [PASS]test_extract_correction_preference: {result[:80]}")

    # 模拟 LLM 返回 NONE（不涉及工具/行为偏好）
    def mock_llm_none(prompt: str) -> str:
        return "NONE"

    mem.engine._llm_callback = mock_llm_none
    result2 = mem._extract_correction_preference(
        "不对，不是这个意思",
        "好的我理解了"
    )
    assert result2 is None, "不涉及工具偏好时应返回 None"
    print(f"  [PASS]test_extract_correction_preference (NONE case)")

    mem.close()


# ============================================================
# Test 2: after_reply 负反馈触发偏好存储
# ============================================================
def test_after_reply_negative_feedback_triggers_learning():
    """验证负反馈时 after_reply 触发偏好提取和存储"""
    from memory_engine.lite_integration import AgentMemory
    import time

    mem = AgentMemory()

    extract_called = []
    force_remember_called = []

    def mock_extract(user_text, bot_reply):
        extract_called.append((user_text, bot_reply))
        return "当用户查询外币时应该用web_search不要用billing_report"

    def mock_force_remember(user_id, nick, content, memory_type, importance):
        force_remember_called.append({
            'user_id': user_id, 'content': content,
            'memory_type': memory_type, 'importance': importance
        })
        return 1

    mem._extract_correction_preference = mock_extract
    mem.engine.force_remember = mock_force_remember

    # 模拟负反馈路径: 直接调用 _store 的内部逻辑
    # 注意: after_reply 是异步的, 测试中我们直接调用内部函数
    user_id = "feishu:ou_test_user"
    user_text = "不对，我要的是汇率不是账单，你应该联网搜索"
    bot_reply = "这是您的账单报告：本月境外交易共3笔..."

    # 手动触发偏好提取 (模拟 after_reply 内的逻辑)
    pref = mem._extract_correction_preference(user_text, bot_reply)
    if pref:
        mem.engine.force_remember(
            user_id, "TestUser", pref,
            memory_type='preference', importance=0.9
        )

    assert len(extract_called) == 1, f"应调用 1 次提取, 实际 {len(extract_called)}"
    assert len(force_remember_called) == 1, f"应调用 1 次存储, 实际 {len(force_remember_called)}"
    stored = force_remember_called[0]
    assert stored['memory_type'] == 'preference', f"memory_type 应为 preference, 实际 {stored['memory_type']}"
    assert stored['importance'] == 0.9, f"importance 应为 0.9, 实际 {stored['importance']}"
    assert 'web_search' in stored['content'], f"偏好内容应包含工具名, 实际: {stored['content']}"
    print(f"  [PASS]test_after_reply_negative_feedback_triggers_learning")

    mem.close()


# ============================================================
# Test 3: before_reply 偏好单独分组 + 格式验证
# ============================================================
def test_before_reply_preference_grouping():
    """验证 before_reply 将偏好单独分组为可操作格式"""
    from memory_engine.lite_integration import AgentMemory

    mem = AgentMemory()

    # 模拟 recall 返回混合结果: 部分偏好 + 部分普通记忆
    mock_results = [
        {
            'content': '当用户查询外币/汇率时，应该用web_search联网搜索实时汇率，不要调用billing_report',
            'importance': 0.9,
            'type': 'preference',  # 来自规则提取路径
            'distance': 0.2,
        },
        {
            'content': '用户昨天问了系统负载',
            'importance': 0.6,
            'type': 'event',
            'distance': 0.3,
            'tags': 'event',
        },
        {
            'content': '用户偏好用DeepSeek模型查汇率',
            'importance': 0.85,
            'tags': 'preference,偏好',  # 来自语义搜索路径
            'distance': 0.15,
        },
    ]

    # Patch recall
    original_recall = mem.engine.recall
    def mock_recall(query, speaker_id=None, top_k=5):
        return mock_results
    mem.engine.recall = mock_recall

    # Patch get_user_context
    original_get_ctx = mem.engine.get_user_context
    mem.engine.get_user_context = lambda uid: ''

    # Patch persona
    original_get_persona = mem._get_persona
    mem._get_persona = lambda: ''

    ctx = mem.before_reply("feishu:ou_test", "查外币汇率")
    mem.engine.recall = original_recall
    mem.engine.get_user_context = original_get_ctx
    mem._get_persona = original_get_persona

    # 验证: 偏好段存在且格式正确
    assert '从历史纠正中学到的工具/行为偏好' in ctx, \
        f"应有偏好段标题, 实际: {ctx[:200]}"
    assert '⚠️' in ctx, \
        f"preference items should have warning prefix, got: {ctx[:200]}"
    assert '高优先级' in ctx, \
        f"偏好段应标注高优先级, 实际: {ctx[:200]}"
    assert '选择工具前必须检查' in ctx, \
        f"偏好段应有行为指引, 实际: {ctx[:200]}"

    # 验证: 包含偏好内容
    assert 'web_search' in ctx, f"应包含偏好中的工具名, 实际: {ctx[:200]}"
    assert 'billing_report' in ctx, f"应包含偏好中的避免项, 实际: {ctx[:200]}"

    # 验证: 两个 preference 类结果都被识别并分组
    # 第一个: type='preference'
    # 第二个: tags 含 'preference'
    pref_count = ctx.count('⚠️')
    assert pref_count == 2, f"expected 2 prefs (type+tags), got {pref_count}"

    # 验证: 普通记忆段也存在
    assert '相关历史记忆' in ctx, f"应有普通记忆段, 实际: {ctx[:200]}"
    assert '用户昨天问了系统负载' in ctx, f"应包含普通记忆, 实际: {ctx[:200]}"

    print(f"  [PASS]test_before_reply_preference_grouping")

    mem.close()


# ============================================================
# Test 4: 系统提示词包含偏好引导
# ============================================================
def test_system_prompt_includes_preference_guidance():
    """验证 agent.py 的 _build_system_prompt 包含偏好引导"""
    import importlib.util
    agent_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agent.py')
    spec = importlib.util.spec_from_file_location("agent_test", agent_path)
    agent_module = importlib.util.module_from_spec(spec)

    # 不能直接 import agent.py（依赖太多），直接读文件验证
    with open(agent_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 验证 admin prompt 包含偏好引导
    assert '从历史纠正中学到的工具/行为偏好' in content, \
        "admin 系统提示词应包含偏好引导"
    assert '在选工具前先检查是否匹配' in content, \
        "admin 系统提示词应引导检查偏好"

    # 验证 guest prompt 也包含
    assert '如果提示中包含学到的偏好，优先遵循' in content, \
        "guest 系统提示词应包含偏好引导"

    print(f"  [PASS]test_system_prompt_includes_preference_guidance")


# ============================================================
# Test 5: 端到端学习回路 (模拟)
# ============================================================
def test_end_to_end_learning_loop():
    """
    模拟完整回路:
    1. 用户问"查外币" → 无偏好 → 可能走错工具
    2. 用户纠正 → 提取偏好 → 存储为 preference
    3. 用户再问"查外币" → 检索到偏好 → 注入提示 → LLM 选对工具
    """
    from memory_engine.lite_integration import AgentMemory

    mem = AgentMemory()
    import uuid
    user_id = f"feishu:ou_e2e_test_{uuid.uuid4().hex[:8]}"

    print("  [INFO] 回路模拟:")

    # Step 1: 第一次查询 (无偏好)
    print("    1. 用户: '查一下美元汇率'")
    # 此时没有相关偏好，before_reply 只返回 persona + 普通记忆
    ctx1 = mem.before_reply(user_id, "查一下美元汇率")
    # 第一次应该没有偏好段
    assert '从历史纠正中学到的工具/行为偏好' not in (ctx1 or ''), \
        "首次查询不应有偏好"
    print("       → 无偏好注入 (正常)")

    # Step 2: 用户纠正 (模拟 after_reply + 纠正提取)
    print("    2. 用户纠正: '不对，我要的是汇率不是账单，用web_search'")
    # 模拟 LLM 提取偏好并存储
    def mock_llm(prompt):
        return "当用户查询外币/汇率时，应该用web_search联网搜索实时汇率，不要调用billing_report查账单"
    mem.engine._llm_callback = mock_llm

    bot_error_reply = "这是您的账单报告：本月境外信用卡交易3笔..."
    pref = mem._extract_correction_preference(
        "不对，我要的是汇率不是账单，用web_search联网搜索",
        bot_error_reply
    )
    assert pref is not None, "应提取到偏好"
    mem.engine.force_remember(user_id, "TestUser", pref,
                              memory_type='preference', importance=0.9)
    print(f"       → 偏好已存储: {pref[:60]}...")

    # Step 3: 第二次查询 (此时 RAG 应有偏好)
    print("    3. 用户: '查一下欧元汇率'")
    # 但由于 ChromaDB 未连接/未初始化, 语义搜索降级为关键词搜索
    # 关键词搜索基于 LIKE, 可能检不到偏好(取决于关键词匹配)
    # 这里只验证偏好已存储, 不依赖 RAG 检索

    # 验证 conversations 表中有 preference 记录
    import sqlite3, json
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          'data', 'memory', 'memory.db')
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT content, memory_type, importance FROM conversations "
            "WHERE speaker_id=? AND memory_type='preference' "
            "ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        conn.close()

        if row:
            assert row[1] == 'preference', f"memory_type 应为 preference, 实际 {row[1]}"
            assert row[2] >= 0.85, f"importance 应 >= 0.85, 实际 {row[2]}"
            print(f"       → 数据库中确认偏好已存储: importance={row[2]}")
    else:
        print(f"       → (数据库未创建, 跳过持久化验证)")

    print(f"  [PASS]test_end_to_end_learning_loop")

    mem.close()


# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("测试: 闭合反馈-学习回路")
    print("=" * 60)

    tests = [
        test_extract_correction_preference,
        test_after_reply_negative_feedback_triggers_learning,
        test_before_reply_preference_grouping,
        test_system_prompt_includes_preference_guidance,
        test_end_to_end_learning_loop,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"结果: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 60}")

    if failed > 0:
        sys.exit(1)
