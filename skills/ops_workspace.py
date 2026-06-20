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


@skill(
    name='ops_web_fetch',
    description='''抓取网页 HTML 内容（仅适合静态/简单页面）。先直连，失败则走 SOCKS5 代理 (127.0.0.1:18988)。返回 HTML 纯文本摘要。

⚠️ 以下场景请优先使用 `web_clip` 而不是本工具：
  • 微信公众号文章 (mp.weixin.qq.com)
  • 知乎问答 / 专栏 (zhihu.com / zhuanlan.zhihu.com)
  • B 站视频 / 专栏 (bilibili.com)
  • 小红书 (xiaohongshu.com)
  • V2EX / Linux.do / 机器之心 / 量子位 / 网易等动态加载站点

本工具仅适合：纯静态 HTML 页面、API 接口、RSS feed、简单文档站点。
如果返回空页面 / 反爬墙 / 要求 JS 渲染，请勿反复重试本工具，应改用 web_clip。''',
    params={
        'url': {
            'type': 'string',
            'description': '目标网页 URL'
        },
        'use_proxy': {
            'type': 'boolean',
            'description': '是否使用代理（直连失败后自动尝试）',
            'default': True
        }
    }
)
def ops_web_fetch(url: str, use_proxy: bool = True) -> str:
    import subprocess, re

    if not url.startswith(('http://', 'https://')):
        return "❌ 拒绝访问: url 必须以 http:// 或 https:// 开头"

    def try_fetch(proxy: str = '') -> tuple:
        cmd = ['curl', '-sL', '-m', '15', '--max-filesize', '500000',
               '-H', 'User-Agent: Mozilla/5.0 (compatible; LiteAgent/1.0)']
        if proxy:
            cmd.extend(['-x', proxy])
        cmd.append(url)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            return r.stdout, ''
        except subprocess.TimeoutExpired:
            return '', '请求超时'
        except Exception as e:
            return '', str(e)

    html, err = try_fetch()
    if not html and use_proxy:
        html, err2 = try_fetch('socks5://127.0.0.1:18988')
        if not html:
            return f'❌ 抓取失败: 直连={err or "无内容"}, 代理={err2 or "无内容"}'

    if not html or len(html) < 100:
        return f'❌ 页面内容过短或无内容 ({len(html)} 字符)'

    html = html[:50000]

    title = ''
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
    if m:
        title = re.sub(r'<[^>]+>', '', m.group(1)).strip()

    for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside']:
        html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.I | re.S)

    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    text = re.sub(r'</(p|div|h\d|li|tr)>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())

    if len(text) > 3000:
        text = text[:3000] + '\n\n... (内容过长已截断)'

    if title:
        text = f'📌 {title}\n\n{text}'

    return text
