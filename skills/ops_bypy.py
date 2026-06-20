import subprocess
from skill_engine import skill

def _run_bypy_cmd(args: list, timeout: int = 600) -> str:
    """Helper to run bypy commands and return output"""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return f"✅ 成功:\n{result.stdout}"
        else:
            return f"❌ 失败 (Exit Code {result.returncode}):\n{result.stderr}\n{result.stdout}"
    except subprocess.TimeoutExpired:
        return f"❌ 执行超时 ({timeout}s)"
    except Exception as e:
        return f"❌ 执行异常: {str(e)}"

@skill(
    name='bypy_info',
    description='查看百度网盘的配额和当前使用情况'
)
def bypy_info() -> str:
    return _run_bypy_cmd(["bypy", "info"], timeout=30)

@skill(
    name='bypy_mkdir',
    description='在百度网盘上创建目录',
    params={
        'remote_dir': {
            'type': 'string',
            'description': '要创建的网盘目录路径，例如 lite_agent'
        }
    }
)
def bypy_mkdir(remote_dir: str) -> str:
    return _run_bypy_cmd(["bypy", "mkdir", remote_dir], timeout=60)

@skill(
    name='bypy_syncup',
    description='将本地目录同步/备份到百度网盘',
    params={
        'local_dir': {
            'type': 'string',
            'description': '本地要备份的目录，例如 /root/.halo'
        },
        'remote_dir': {
            'type': 'string',
            'description': '百度网盘上的目标目录，例如 lite_agent/halo'
        }
    }
)
def bypy_syncup(local_dir: str, remote_dir: str) -> str:
    # bypy syncup 会自动创建不存在的目标目录，并增量上传
    return _run_bypy_cmd(["bypy", "syncup", local_dir, remote_dir], timeout=3600)

@skill(
    name='bypy_syncdown',
    description='将百度网盘上的目录同步/下载到本地',
    params={
        'remote_dir': {
            'type': 'string',
            'description': '百度网盘上的目录，例如 lite_agent/halo'
        },
        'local_dir': {
            'type': 'string',
            'description': '本地目标目录，例如 /root/halo_restore'
        }
    }
)
def bypy_syncdown(remote_dir: str, local_dir: str) -> str:
    return _run_bypy_cmd(["bypy", "syncdown", remote_dir, local_dir], timeout=3600)
