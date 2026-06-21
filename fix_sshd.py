import re
with open('/etc/ssh/sshd_config', 'r') as f:
    content = f.read()
content = re.sub(r'(?m)^#?PasswordAuthentication\s+yes', 'PasswordAuthentication no', content)
with open('/etc/ssh/sshd_config', 'w') as f:
    f.write(content)
