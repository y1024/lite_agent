#!/bin/bash
(crontab -l 2>/dev/null | grep -v edge_sentinel.py; echo "*/5 * * * * python3 /opt/edge_sentinel/edge_sentinel.py") | crontab -
