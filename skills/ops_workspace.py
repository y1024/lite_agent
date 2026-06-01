import sys, os, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skill_engine import skill

WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'workspace')


@skill(
    name='ops_workspace_run',
    description='在安全工作区内写入并执行 Python 代码，返回执行结果。用于访问 MongoDB、数据分析等复杂操作',
    params={
        'code': {
            'type': 'string',
            'description': '完整的 Python 代码，必须包含必要的 import 和 print 输出。代码将在隔离的工作区目录中执行'
        },
        'timeout': {
            'type': 'integer',
            'description': '执行超时秒数，默认 30',
            'default': 30
        }
    }
)
def ops_workspace_run(code: str, timeout: int = 30) -> str:
    os.makedirs(WORKSPACE, exist_ok=True)
    ts = int(time.time() * 1000)
    script_path = os.path.join(WORKSPACE, f'task_{ts}.py')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(code)

    try:
        r = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=timeout,
            cwd=WORKSPACE
        )
        output = r.stdout.strip()
        if r.stderr.strip():
            output += '\n\n[stderr]:\n' + r.stderr.strip()
        return output or f'(无输出, 退出码: {r.returncode})'
    except subprocess.TimeoutExpired:
        return f'执行超时 ({timeout}s)，已强制终止'
    except Exception as e:
        return f'执行失败: {e}'
