import json
with open('/home/liteagent/lite_agent/config.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
d['llm']['models']['gemini-pro']['model'] = 'gemini-3.1-pro-preview'
with open('/home/liteagent/lite_agent/config.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=4, ensure_ascii=False)
