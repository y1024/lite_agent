#!/bin/bash
cd /root/lite_agent
export ALL_PROXY="socks5h://127.0.0.1:18988"
export HTTPS_PROXY="socks5h://127.0.0.1:18988"
export HTTP_PROXY="socks5h://127.0.0.1:18988"
pip3 install --find-links=/root/lite_agent/wheels -r requirements.txt -i https://pypi.org/simple
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"
systemctl restart feishu-bot
sleep 5
journalctl -u feishu-bot -n 30 --no-pager
