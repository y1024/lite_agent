import sys; sys.path.insert(0, './skills'); sys.path.insert(0, '.')
from ops_web_clipper import _upload_to_hedgedoc
with open('/tmp/plan.md', 'r', encoding='utf-8') as f:
    text = f.read()
url = _upload_to_hedgedoc(text)
print('HedgeDoc URL:', url)
