import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skill_engine import skill

@skill(
    name='ops_rss_node_status',
    description='检查 RSS 节点的更新状态，找出最后一次更新超过3天的异常节点。'
)
def ops_rss_node_status() -> str:
    """返回超过3天未更新的 RSS 节点列表"""
    try:
        from skills.ops_rss import _get_db
    except ImportError:
        return "❌ 无法加载数据库配置"
        
    c, db_name = _get_db()
    db = c[db_name]
    
    from datetime import datetime, timedelta
    
    # 获取3天前的时间
    threshold_date = datetime.now() - timedelta(days=3)
    nodes = list(db['RssNode'].find({'isEnable': 1}))
    
    outdated_nodes = []
    for node in nodes:
        sitename = node.get('sitename', '未知节点')
        last_update = node.get('lastupdate')
        
        dt = None
        if isinstance(last_update, datetime):
            dt = last_update
        elif isinstance(last_update, str):
            try:
                # 处理带有T的ISO格式和普通格式
                time_str = last_update[:19].replace('T', ' ')
                dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
                
        if dt and dt < threshold_date:
            outdated_nodes.append(f"- **{sitename}**: 最后更新于 {dt.strftime('%Y-%m-%d %H:%M')}")
        elif not dt:
            outdated_nodes.append(f"- **{sitename}**: 暂无更新记录或时间格式异常")

    c.close()
    
    if outdated_nodes:
        return "\n⚠️ **注意：以下 RSS 节点超过3天未更新：**\n" + "\n".join(outdated_nodes)
    else:
        return "\n✅ **所有启用的 RSS 节点都在3天内正常更新。**"

