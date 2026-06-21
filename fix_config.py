import json
with open('/home/liteagent/lite_agent/config.json', 'r') as f:
    c = json.load(f)
c['channels']['api']['host'] = '127.0.0.1'
with open('/home/liteagent/lite_agent/config.json', 'w') as f:
    json.dump(c, f, indent=4)
