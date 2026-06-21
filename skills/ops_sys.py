import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.skill_engine import skill
import subprocess
import re
import socket

@skill(
    name='ops_sys_status',
    description='获取VPS系统状态，包括主机名、运行时间、系统负载、CPU使用率、内存和磁盘信息',
    params={
        'detail': {
            'type': 'boolean',
            'description': '是否返回详细信息（包含占用内存和CPU最高的进程列表）',
            'default': False
        }
    }
)
def ops_sys_status(detail: bool = False) -> str:
    sections = []
    
    # 1. 主机名
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "(获取失败)"
    sections.append(f"主机名: {hostname}")
    
    # 2. 运行时间
    try:
        r = subprocess.run(['uptime', '-p'], capture_output=True, text=True, timeout=5)
        uptime = r.stdout.strip() or r.stderr.strip() or "(获取失败)"
    except Exception as e:
        uptime = f"(获取失败: {e})"
    sections.append(f"运行时间: {uptime}")
    
    # 3. 系统负载
    try:
        with open('/proc/loadavg', 'r') as f:
            loadavg = f.read().strip().split()
            load = f"{loadavg[0]} {loadavg[1]} {loadavg[2]}"
    except Exception:
        load = "(获取失败)"
    sections.append(f"系统负载: {load}")
    
    # 4. CPU使用
    try:
        # 运行 top -bn1 并在 python 中做解析
        r = subprocess.run(['top', '-bn1'], capture_output=True, text=True, timeout=5)
        cpu_line = ""
        for line in r.stdout.splitlines():
            if 'Cpu(s)' in line or 'cpu(s)' in line.lower():
                cpu_line = line
                break
        if cpu_line:
            us_match = re.search(r'(\d+\.?\d*)\s*(?:us|用户)', cpu_line)
            sy_match = re.search(r'(\d+\.?\d*)\s*(?:sy|系统)', cpu_line)
            id_match = re.search(r'(\d+\.?\d*)\s*(?:id|空闲)', cpu_line)
            us = us_match.group(1) if us_match else "0.0"
            sy = sy_match.group(1) if sy_match else "0.0"
            idle = id_match.group(1) if id_match else "100.0"
            cpu_status = f"用户{us}%, 系统{sy}%, 空闲{idle}%"
        else:
            cpu_status = "(未找到Cpu(s)行)"
    except Exception as e:
        cpu_status = f"(获取失败: {e})"
    sections.append(f"CPU使用: {cpu_status}")
    
    # 5. 物理内存
    try:
        r = subprocess.run(['free', '-h'], capture_output=True, text=True, timeout=5)
        mem_line = ""
        for line in r.stdout.splitlines():
            if line.startswith('Mem:'):
                mem_line = line
                break
        if mem_line:
            parts = mem_line.split()
            mem_status = f"已用 {parts[2]} / 总计 {parts[1]}"
        else:
            mem_status = "(未找到Mem行)"
    except Exception as e:
        mem_status = f"(获取失败: {e})"
    sections.append(f"物理内存: {mem_status}")
    
    # 6. 根目录磁盘
    try:
        r = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=5)
        lines = r.stdout.splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            disk_status = f"已用 {parts[2]} / 总计 {parts[1]} ({parts[4]})"
        else:
            disk_status = "(输出格式错误)"
    except Exception as e:
        disk_status = f"(获取失败: {e})"
    sections.append(f"根目录磁盘: {disk_status}")
    
    # 7. 详细信息
    if detail:
        sections.append("\n--- 占用资源最高的进程 ---")
        try:
            r = subprocess.run(['ps', 'aux', '--sort=-%mem'], capture_output=True, text=True, timeout=5)
            lines = r.stdout.splitlines()[:6]
            sections.append('\n'.join(lines))
        except Exception as e:
            sections.append(f"(获取失败: {e})")
            
    return '\n'.join(sections)
