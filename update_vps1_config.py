import json
with open('/home/liteagent/lite_agent/config.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
d['edge_token'] = '${EDGE_TOKEN}'
with open('/home/liteagent/lite_agent/config.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=4, ensure_ascii=False)
