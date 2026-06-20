# Review: max_steps 回归 + 工具选择策略修复

## 背景

用户在飞书上发"拉下最新账单邮件，把外币交易搞出来"，agent 走简单 AI Loop 用 `ops_workspace_run` 裸写 Python 查 MongoDB/SQLite，10 步耗光被截断返回"任务执行步骤过多已自动终止"。

用户质疑：以前能跑完，为什么现在不行了？

## 根因链

```
Agent 不知道 billing_fetch/billing_report 是最优工具
  → 选 ops_workspace_run ("执行任意 Python 代码") 当万能默认
    → 每一步: LLM 生成代码 → 执行 → 读结果 → 再生成 (3-17s/步)
      → 14+ 步才完成一个本该 3 步的任务
        ├─ max_steps=30: 能跑完，但 2-5 分钟 → 用户感知为"慢响应"
        └─ max_steps=10: 失败快，但不完成 → 用户感知为"坏了"
```

## 上次的"慢响应修复"回顾

上次诊断正确但处方错误：
- ✅ **诊断对**: agent 确实慢，因为每步 LLM + Python 执行消耗 3-17 秒，30 步上限允许它烧 2-5 分钟
- ❌ **处方错**: 把 `max_steps_per_goal` 从 30 砍到 10。这没修"为什么 agent 选错工具"，只是让它失败得更快

`max_steps` 是上限不是最小步数——agent 完成后立即 `return`，不会白跑满。简单查询（"你好"）1 步返回，10 和 30 完全一样快。

## 改动 (2 处)

### 1. VPS1 `config.json`: `max_steps_per_goal` 10 → 30

**位置**: `session.max_steps_per_goal`

**理由**: 10 是上次错误处方的残留。30 恢复历史可用状态。DAG 编排任务有独立的 `dag_max_total_steps: 30` 不受影响。

### 2. `agent.py` `_build_system_prompt()`: 加工具选择优先级规则

**改动**: 在 admin 系统提示词的"注意事项"段末尾，`"如果工具返回错误…"` 之前，加一条：

```
- 选择工具时，优先使用领域专用工具完成任务，ops_workspace_run 是写代码执行，成本高、步骤多，仅在确实无专用工具可用时作为最后手段。例如：账单任务优先用 billing_fetch/billing_report，系统查询优先用 ops_sys，日志查询优先用 ops_logs
```

**注意**: 示例 (`billing_fetch`, `ops_sys`, `ops_logs`) 仅作说明，让 LLM 理解规则含义——不是硬编码映射。实际工具选择仍由 LLM 根据工具描述决定。

**理由**: 55 个工具平铺列出时，`ops_workspace_run` ("execute arbitrary Python code") 因为图灵完备而被 LLM 当成万能默认。这条规则改变工具选择的优先级排序，是通用工程原则——不针对任何具体场景。

## 预期效果

修复前 (max_steps=10, 无引导):
```
查账单 → ops_workspace_run × 10 → 截断失败
耗时 ~70s, 无结果
```

修复前 (max_steps=30, 无引导):
```
查账单 → ops_workspace_run × 14+ → 勉强完成
耗时 2-5 分钟, 慢
```

修复后 (max_steps=30, 有引导):
```
查账单 → billing_fetch → billing_report → 汇总输出
3-5 步, ~30s, 正常
```

## 不做什么

- 不改 `_is_complex_task()` 关键词列表
- 不给 billing 工具单独改 description
- 不加新的 billing skill
- 这些是 per-case 硬编码，违背用户"让 agent 自己变聪明"的目标
