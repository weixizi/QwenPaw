---
name: recruitment_master
description: Master skill for end-to-end recruitment workflow with 9 subtasks using PlanNotebook for state tracking.
metadata:
  builtin_skill_version: "1.0"
  qwenpaw:
    emoji: "📋"
---

# Recruitment Master Skill（招聘流程主控）

## 概述

这是一个 **Master Skill** 示例，展示了如何使用 **PlanNotebook** 来管理复杂的多步骤工作流。

招聘流程包含 9 个子任务：

```
1. 发布内部职位 → 2. 招聘网站发布 → 3. 获取候选人 → 4. 简历打分 → 
5. 打招呼 → 6. 回复消息 → 7. 获取简历 → 8. 上传简历 → 9. 投递简历
```

## 什么时候使用

- 需要执行完整的招聘流程
- 需要跟踪多步骤进度
- 需要条件分支（简历分数 >= 70 才继续）
- 需要长周期等待（等待候选人回复）

## 使用方法

### 基本用法

```python
from qwenpaw.agents.master_skill import create_recruitment_master_skill
from qwenpaw.plan import FilePlanStorage

# 1. 创建 PlanStorage
plan_storage = FilePlanStorage(
    base_dir=Path("~/.copaw/workspaces").expanduser(),
    agent_id="your-agent-id",
)

# 2. 创建 Master Skill
skill = create_recruitment_master_skill(
    agent=agent,
    plan_storage=plan_storage,
)

# 3. 执行
result = await skill.execute(context={
    "job_title": "Python 开发工程师",
    "job_description": "...",
    "requirements": "...",
})

# 4. 检查结果
if result["success"]:
    print(f"招聘完成！申请 ID: {result['output'].get('application_id')}")
else:
    print(f"招聘失败：{result.get('error')}")
```

### 作为 Agent Skill 使用

在对话中直接使用：

```
用户：帮我执行招聘流程，职位是 Python 开发工程师
Assistant: 好的，我将执行招聘流程，包含 9 个步骤...
```

## 子任务详情

| 步骤 | ID | 说明 | 关键输出 |
|------|----|------|----------|
| 1 | publish_internal | 发布内部职位 | job_id |
| 2 | publish_external | 招聘网站发布 | external_job_id |
| 3 | get_candidates | 获取候选人列表 | candidate_id |
| 4 | score_resume | 简历打分 | resume_score (>=70 通过) |
| 5 | greet_candidate | 打招呼 | greeting_status |
| 6 | reply_message | 回复消息 | conversation |
| 7 | get_resume | 获取简历 | resume_file_path |
| 8 | upload_resume | 上传简历 | resume_id |
| 9 | submit_application | 投递简历 | application_id |

## 条件分支

### 简历打分

如果简历分数 < 70：
- 该候选人被跳过
- 继续处理下一个候选人（需要扩展实现）
- 当前实现会中止流程

## 异常处理

以下情况会中止流程：
- 简历打分 < 70
- 申请提交失败

以下情况会记录日志但继续：
- 打招呼失败
- 回复消息失败
- 其他非关键步骤失败

## PlanNotebook 集成

此 Skill 使用 PlanNotebook 来：
1. **跟踪进度**：每个子任务的状态（todo → in_progress → done/abandoned）
2. **提供 Hint**：在每轮 reasoning 时注入当前步骤提示
3. **持久化**：计划状态保存到文件，支持中断恢复
4. **归档历史**：完成后归档到历史记录

## 扩展开发

### 添加新的 Master Skill

1. 继承 `MasterSkill` 基类
2. 实现 `create_plan()` 返回计划定义
3. 实现 `execute_subtask()` 处理每个子任务
4. 可选：重写 `should_abort_on_failure()` 自定义中止逻辑

### 集成真实 API

当前的实现使用 Mock 数据。要集成真实系统：

```python
# 1. 实现 HR 系统客户端
class HRSystemClient:
    async def publish_job(self, job_data) -> str:
        """发布职位，返回职位 ID"""
        pass

# 2. 实现招聘网站 API 客户端
class RecruitmentAPIClient:
    async def publish_job(self, job_data) -> str:
        """发布职位到招聘网站"""
        pass

# 3. 创建 Skill 时传入客户端
skill = RecruitmentMasterSkill(
    agent=agent,
    plan_storage=plan_storage,
    hr_system_client=HRSystemClient(),
    recruitment_api_client=RecruitmentAPIClient(),
)
```

## 配置文件

在 `agent.json` 中启用（如需要）：

```json
{
  "skills": {
    "recruitment_master": {
      "enabled": true,
      "config": {
        "min_resume_score": 70,
        "max_candidates": 10
      }
    }
  }
}
```

## 注意事项

1. **PlanNotebook 绑定**：Master Skill 执行时会临时绑定 PlanNotebook 到 agent，完成后自动解绑
2. **其他 Skill 不受影响**：普通 Skill 执行时 plan_notebook = None
3. **持久化位置**：`~/.copaw/workspaces/{agent_id}/plans/`
4. **恢复机制**：计划中断后可从持久化存储恢复状态

## 相关文件

- 基类：`src/qwenpaw/agents/master_skill.py`
- 存储：`src/qwenpaw/plan/file_plan_storage.py`
- 接口：`src/qwenpaw/plan/plan_storage.py`
- Agent 修改：`src/qwenpaw/agents/react_agent.py`
