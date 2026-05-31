# Lite Agent

🚀 **Lite Agent** 是一个轻量级、零外部依赖（仅依赖官方 SDK）、支持深度思考大模型（如 DeepSeek-V4-Pro / R1）的私有化 AI 智能助手引擎。它能够通过 WebSocket 无缝接入飞书机器人，并通过自然语言全自动调度本地服务器的各类运维和账单处理脚本。

## 🌟 核心特性

- **极致轻量 (0 外部依赖)**: 核心框架完全使用 Python 内置库（`urllib`, `sqlite3`, `threading` 等）实现，无需安装庞大的三方框架。
- **动态技能引擎 (Skill Engine)**: 只需要编写普通的 Python 函数并加上 `@skill` 装饰器，即可一秒钟将本地脚本转化为 AI 的可用工具 (Tool Calling)。
- **完美适配 DeepSeek 深度思考模型**: 底层严格遵守 DeepSeek 官方 Tool Calling 规范，支持 `reasoning_content` (思维链) 在多轮工具调用中的无损透传，彻底解决 400 报错，同时自动适配 `reasoning_effort` 注入。
- **跨会话长期记忆 (Memory Engine)**: 本地搭载 Chroma 向量数据库与 SentenceTransformers (bge-small-zh-v1.5) 进行语义向量化，结合 LLM 每天定时执行“记忆蒸馏复盘”，让助手越养越懂你。
- **定时任务引擎 (Cron Engine)**: 内置系统级的定时任务调度器，支持通过对话动态管理（查看、执行、启停）各项自动化任务（如自动备份、证书巡检、每日复盘）。
- **多通道无缝接入**: 突破内网限制，无需繁琐的公网 Webhook 回调，支持通过 WebSocket 直连 **飞书** 和 **钉钉 (Stream 模式)**。
- **完美适配 DeepSeek 深度思考模型**: 底层严格遵守 DeepSeek 官方 Tool Calling 规范，支持 `reasoning_content` (思维链) 在多轮工具调用中的无损透传，彻底解决 400 报错，同时自动适配 `reasoning_effort` 注入。

## 🛠️ 内置技能库 (Skills)

系统已内置多款实用插件，涵盖服务器运维与账单管理：

### 💰 财务与账单管理 (`ops_billing.py`)
- **账单解析入库**: 自动从邮箱抓取信用卡账单并落库入账。
- **财务汇总报表**: 一键生成多维度月度/年度账单报表。
- **对账与提醒**: 支持临期还款自动检查、差异对账、以及大额异常交易筛查。

### 🖥️ 系统与安全运维 (`ops_sys.py`, `ops_security.py`, `ops_logs.py`, `ops_crontab.py`)
- **系统状态看板**: 实时查询系统负载、内存、磁盘以及资源占用 Top 的进程。
- **安全审查**: 自动拦截并扫描近期的 SSH 爆破尝试及异常登录。
- **日志分析**: 支持跨文件、多关键字的高级日志检索。
- **证书监控与脚本执行**: 一键运行 SSL 证书有效期巡检及其他后台脚本。

## 📦 部署指南

### 1. 准备配置文件
在根目录下创建 `config.json`，填入您的配置：
```json
{
    "channels": {
        "feishu": {
            "enabled": true,
            "app_id": "cli_xxxx",
            "app_secret": "xxxx"
        },
        "dingtalk": {
            "enabled": true,
            "client_id": "dingxxxx",
            "client_secret": "xxxx"
        }
    },
    "llm": {
        "api_key": "sk-xxxx",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner"
    },
    "session": {
        "ttl_minutes": 30,
        "max_history": 20,
        "max_steps_per_goal": 10
    }
}
```

### 2. 环境安装与启动
```bash
pip install -r requirements.txt
python3 main.py
```

## 💬 交互指令

- `/remember <type> <内容>` : 强制记录一条关键信息（可选类型: concept, event, preference, troubleshooting）。
- `/memory` : 查看当前长期记忆池的状态与分布。
- `/cron` : 查看当前系统注册的定时任务列表。
- `/cron <序号>` : 手动执行某一项定时任务。
- `/cron toggle <序号>` : 开启或暂停某一项定时任务。
- `/ai <自然语言>` : 强制使用大模型处理（适用于飞书特定场景拦截）。
- `/cmd <脚本指令>` : 绕过大模型，精确触发底层脚本（如 `/cmd report 3`）。
- `/balance` : 查询当前大模型 API 余额。
- `/status` : 查看当前对话目标的进展与 Token 消耗。
- `/history` : 回顾最近对话历史。
- `/new` : 重置当前会话。

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 协议开源。
