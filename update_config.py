import json
with open('vps1_config.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
d['llm']['models']['gemini-pro']['model'] = 'gemini-1.5-pro'
with open('vps1_config_updated.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=4, ensure_ascii=False)
