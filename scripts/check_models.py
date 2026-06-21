import os
import json
from google import genai

# read .env
with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('GEMINI_API_KEY='):
            api_key = line.strip().split('=', 1)[1]
            break

proxy = 'socks5://127.0.0.1:18988'
client = genai.Client(api_key=api_key, http_options={"clientArgs": {"proxy": proxy}})
for model in client.models.list():
    if 'pro' in model.name:
        print(model.name)
