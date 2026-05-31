import json
import time
import urllib.request
import urllib.error
import urllib.parse
import threading
from channels.base import BaseChannel
from agent import IncomingMessage, AgentResponse

class TelegramChannel(BaseChannel):
    """
    Telegram 通道实现 (原生 urllib，支持代理)
    使用 Long Polling (getUpdates) 模式，无需 Webhook
    """

    def __init__(self, config: dict, agent):
        super().__init__('telegram', config, agent)
        self.bot_token = config.get('bot_token', '')
        self.proxy = config.get('proxy', '')  # 例如 http://127.0.0.1:7890
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.running = False
        self._thread = None
        self.offset = 0

        # 配置代理
        if self.proxy:
            proxy_handler = urllib.request.ProxyHandler({
                'http': self.proxy,
                'https': self.proxy
            })
            self.opener = urllib.request.build_opener(proxy_handler)
        else:
            self.opener = urllib.request.build_opener()

    def _api_call(self, method: str, data: dict = None) -> dict:
        url = f"{self.base_url}/{method}"
        try:
            if data:
                req_data = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
            else:
                req = urllib.request.Request(url)
                
            with self.opener.open(req, timeout=40) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.URLError as e:
            if hasattr(e, 'reason') and 'timed out' in str(e.reason).lower():
                pass # Long polling timeout is expected
            else:
                print(f"❌ [Telegram] API Error: {e}")
            return {}
        except Exception as e:
            print(f"❌ [Telegram] Unexpected Error: {e}")
            return {}

    def _poll_loop(self):
        print(f"🚀 Telegram WebSocket(Long Polling) 通道已启动 (代理: {self.proxy or '无'})")
        while self.running:
            try:
                updates = self._api_call('getUpdates', {
                    'offset': self.offset,
                    'timeout': 30,
                    'allowed_updates': ['message']
                })
                
                if not updates or not updates.get('ok'):
                    time.sleep(2)
                    continue

                for update in updates.get('result', []):
                    self.offset = update['update_id'] + 1
                    msg_obj = update.get('message')
                    if not msg_obj or 'text' not in msg_obj:
                        continue
                        
                    chat_id = str(msg_obj['chat']['id'])
                    text = msg_obj['text']
                    msg_id = str(msg_obj['message_id'])
                    
                    # 组装 IncomingMessage
                    incoming = IncomingMessage(
                        channel='telegram',
                        session_key=f"tg_{chat_id}",
                        message_id=f"{chat_id}_{msg_id}",
                        text=text
                    )
                    
                    # 传给 Agent
                    resp = self.agent.handle(incoming)
                    if resp:
                        self.send_response(chat_id, resp)
                        
            except Exception as e:
                print(f"❌ [Telegram] Loop Error: {e}")
                time.sleep(5)

    def start(self):
        if not self.bot_token:
            print("⚠️ Telegram token 未配置，通道无法启动。")
            return
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="TG_Poller")
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)

    def send_response(self, chat_id: str, resp: AgentResponse) -> bool:
        text = resp.text
        if resp.title:
            text = f"**{resp.title}**\n\n{text}"
            
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        res = self._api_call('sendMessage', data)
        if res.get('ok'):
            return True
        else:
            # Markdown 解析失败时，回退到纯文本
            data.pop('parse_mode')
            res = self._api_call('sendMessage', data)
            return bool(res.get('ok'))
