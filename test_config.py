import os, sys
sys.path.insert(0, '/home/liteagent/lite_agent')
from config_loader import load_config
print("TOKEN IS:", load_config().get("edge_token"))
