import os
import sys
import json
import urllib.parse
import subprocess
from html.parser import HTMLParser
from typing import List, Dict, Optional

# Add project root to path (so we can import skill_engine and config_loader)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skill_engine import skill

_config = None

def _load_config():
    global _config
    if _config is None:
        import config_loader
        _config = config_loader.load_config()
    return _config

def _get_proxy() -> Optional[str]:
    """从配置文件中自动检测代理设置"""
    cfg = _load_config()
    # 1. 尝试直接获取顶层 proxy (如果有)
    if "proxy" in cfg:
        return cfg["proxy"]
    
    # 2. 尝试从 llm.models 中查找代理
    llm_models = cfg.get("llm", {}).get("models", {})
    for m_cfg in llm_models.values():
        if isinstance(m_cfg, dict) and "proxy" in m_cfg:
            return m_cfg["proxy"]
            
    # 3. 尝试从 channels 里面找
    channels = cfg.get("channels", {})
    for c_cfg in channels.values():
        if isinstance(c_cfg, dict) and "proxy" in c_cfg:
            return c_cfg["proxy"]
            
    return None

class DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_result = None
        self.in_a = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get('class', '')

        if tag == 'div' and 'result__body' in class_name:
            self.current_result = {'title': '', 'link': '', 'snippet': ''}
            self.results.append(self.current_result)

        elif tag == 'a' and self.current_result is not None:
            if 'result__a' in class_name:
                self.in_a = True
                href = attrs_dict.get('href', '')
                self.current_result['link'] = self._clean_href(href)
            elif 'result__snippet' in class_name:
                self.in_snippet = True

    def handle_endtag(self, tag):
        if tag == 'a':
            self.in_a = False
            self.in_snippet = False

    def handle_data(self, data):
        if self.current_result is not None:
            if self.in_a:
                self.current_result['title'] += data
            elif self.in_snippet:
                self.current_result['snippet'] += data

    def _clean_href(self, href):
        if href.startswith('//'):
            href = 'https:' + href
        elif href.startswith('/'):
            href = 'https://duckduckgo.com' + href
            
        import urllib.parse
        if 'uddg=' in href:
            parsed = urllib.parse.urlparse(href)
            queries = urllib.parse.parse_qs(parsed.query)
            if 'uddg' in queries:
                return queries['uddg'][0]
        return href

def _fetch_ddg_html(query: str, proxy: str = None) -> str:
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    cmd = [
        "curl",
        "-s",
        "-L",
        "--http1.1",
        "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "--connect-timeout", "10",
        "--max-time", "15"
    ]
    if proxy:
        if proxy.startswith("socks5://"):
            proxy = proxy.replace("socks5://", "socks5h://")
        cmd.extend(["-x", proxy])
        
    cmd.append(url)
    
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        err_msg = res.stderr or f"Exit code {res.returncode}"
        raise Exception(f"curl failed: {err_msg}")
    return res.stdout

@skill(
    name="web_search",
    guest_ok=True,
    description="使用搜索引擎在互联网上查找实时事实、最新新闻、时效性数据等信息。",
    params={
        "query": {
            "type": "string",
            "description": "搜索关键词或查询短语，例如：'2026年最新AI大模型排行榜' 或 'Tencent stock price today'"
        }
    },
    tags=["web", "search"]
)
def web_search(query: str) -> str:
    """使用搜索引擎在互联网上查找实时事实和最新数据"""
    try:
        proxy = _get_proxy()
        html_content = _fetch_ddg_html(query, proxy)
        
        parser = DDGParser()
        parser.feed(html_content)
        
        cleaned = []
        for item in parser.results:
            title = item['title'].strip()
            link = item['link'].strip()
            snippet = item['snippet'].strip()
            
            # 过滤掉广告
            if 'duckduckgo.com/y.js' in link or 'ad_provider=' in link:
                continue
            if title and link:
                import re
                title = re.sub(r'\s+', ' ', title)
                snippet = re.sub(r'\s+', ' ', snippet)
                cleaned.append({
                    'title': title,
                    'link': link,
                    'snippet': snippet
                })
        
        results = cleaned[:5]
        if not results:
            return f"🔍 搜索 '{query}' 未找到相关结果。"
            
        output = [f"🔍 **有关 '{query}' 的搜索结果 (前 {len(results)} 条):**\n"]
        for i, item in enumerate(results, 1):
            snippet_str = f"\n   摘要: {item['snippet']}" if item['snippet'] else ""
            output.append(f"{i}. **[{item['title']}]({item['link']})**{snippet_str}\n")
            
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ 联网搜索失败: {e}"
