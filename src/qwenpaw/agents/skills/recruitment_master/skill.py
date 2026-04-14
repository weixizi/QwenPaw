# -*- coding: utf-8 -*-
"""Recruitment Master Skill - A complete example of PlanNotebook usage.

This skill demonstrates how to use PlanNotebook for a 9-step recruitment workflow:
1. Publish job in internal system
2. Publish job on recruitment website
3. Get candidate information
4. Score resume
5. Greet qualified candidates
6. Reply to messages
7. Get candidate resume
8. Upload resume to internal system
9. Submit application to the job

The workflow uses PlanNotebook for state tracking and progress visibility.
"""

import logging
from typing import Any

from ...master_skill import MasterSkill, SubtaskExecutionError
from ....plan import PlanStorage

logger = logging.getLogger(__name__)


class RecruitmentMasterSkill(MasterSkill):
    """Master Skill for recruitment workflow.

    This skill orchestrates a 9-step recruitment process using PlanNotebook
    for state management and progress tracking.

    Workflow:
    1. publish_internal: Publish job in internal HR system
    2. publish_external: Publish job on recruitment website
    3. get_candidates: Fetch candidate list from website
    4. score_resume: Score candidate resume (requires >= 70 to proceed)
    5. greet_candidate: Send greeting message to qualified candidates
    6. reply_message: Handle candidate replies
    7. get_resume: Download candidate resume
    8. upload_resume: Upload resume to internal system
    9. submit_application: Submit application to internal job posting

    Attributes:
        agent: QwenPawAgent instance
        plan_storage: Plan storage instance
        hr_system_client: HR system API client (to be implemented)
        recruitment_api_client: Recruitment website API client (to be implemented)
    """

    def __init__(
        self,
        agent: Any,
        plan_storage: PlanStorage,
        hr_system_client: Any | None = None,
        recruitment_api_client: Any | None = None,
    ):
        """Initialize Recruitment Master Skill.

        Args:
            agent: QwenPawAgent instance
            plan_storage: Plan storage instance
            hr_system_client: Optional HR system API client
            recruitment_api_client: Optional recruitment website API client
        """
        super().__init__(agent, plan_storage)

        self.hr_system_client = hr_system_client
        self.recruitment_api_client = recruitment_api_client

        # Execution context (shared across subtasks)
        self._context: dict = {
            "job_id": None,
            "external_job_id": None,
            "candidate_id": None,
            "resume_score": None,
            "resume_file_path": None,
            "application_id": None,
        }

    def get_skill_name(self) -> str:
        """Get skill name."""
        return "recruitment_master"

    async def create_plan(self) -> dict:
        """Create the recruitment plan definition.

        Returns:
            Plan definition with 9 subtasks
        """
        return {
            "name": "招聘流程",
            "description": (
                "执行完整的招聘流程：发布职位 → 招聘网站发布 → 获取候选人 → "
                "简历打分 → 打招呼 → 回复消息 → 获取简历 → 上传简历 → 投递职位"
            ),
            "expected_outcome": (
                "成功将候选人简历投递到目标职位，并在内部系统中创建申请记录"
            ),
            "subtasks": [
                {
                    "id": "publish_internal",
                    "name": "发布内部职位",
                    "description": (
                        "在公司内部 HR 系统中发布职位，获取职位 ID。"
                        "需要提供职位名称、职位描述、任职要求等信息。"
                    ),
                },
                {
                    "id": "publish_external",
                    "name": "招聘网站发布",
                    "description": (
                        "在招聘网站（如 BOSS 直聘、拉勾网等）发布职位。"
                        "需要使用内部职位 ID 关联。"
                    ),
                },
                {
                    "id": "get_candidates",
                    "name": "获取候选人列表",
                    "description": (
                        "从招聘网站获取匹配的候选人列表。"
                        "根据职位要求筛选合适的候选人。"
                    ),
                },
                {
                    "id": "score_resume",
                    "name": "简历打分",
                    "description": (
                        "分析候选人简历并进行打分。"
                        "分数 >= 70 分才会进入下一步，否则跳过该候选人。"
                    ),
                },
                {
                    "id": "greet_candidate",
                    "name": "打招呼",
                    "description": (
                        "向符合条件的候选人发送打招呼消息。"
                        "等待候选人回复。"
                    ),
                },
                {
                    "id": "reply_message",
                    "name": "回复消息",
                    "description": (
                        "处理候选人的回复，进行进一步沟通。"
                        "可能需要多轮对话。"
                    ),
                },
                {
                    "id": "get_resume",
                    "name": "获取简历",
                    "description": (
                        "从招聘网站下载候选人的完整简历。"
                        "保存为 PDF 或 Word 格式。"
                    ),
                },
                {
                    "id": "upload_resume",
                    "name": "上传简历",
                    "description": (
                        "将简历上传到内部 HR 系统。"
                        "系统会进行简历解析和存档。"
                    ),
                },
                {
                    "id": "submit_application",
                    "name": "投递简历",
                    "description": (
                        "将候选人简历投递到目标职位。"
                        "创建申请记录并通知 HR。"
                    ),
                },
            ],
        }

    async def execute_subtask(self, subtask_id: str, context: dict) -> dict:
        """Execute a single recruitment subtask.

        Args:
            subtask_id: Subtask identifier
            context: Execution context (shared across subtasks)

        Returns:
            Subtask result with success, output, and error fields
        """
        logger.info(f"Executing subtask: {subtask_id}")

        try:
            if subtask_id == "publish_internal":
                return await self._publish_internal(context)
            elif subtask_id == "publish_external":
                return await self._publish_external(context)
            elif subtask_id == "get_candidates":
                return await self._get_candidates(context)
            elif subtask_id == "score_resume":
                return await self._score_resume(context)
            elif subtask_id == "greet_candidate":
                return await self._greet_candidate(context)
            elif subtask_id == "reply_message":
                return await self._reply_message(context)
            elif subtask_id == "get_resume":
                return await self._get_resume(context)
            elif subtask_id == "upload_resume":
                return await self._upload_resume(context)
            elif subtask_id == "submit_application":
                return await self._submit_application(context)
            else:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Unknown subtask: {subtask_id}",
                }

        except Exception as e:
            logger.exception(f"Subtask {subtask_id} failed: {e}")
            return {
                "success": False,
                "output": None,
                "error": str(e),
            }

    async def _publish_internal(self, context: dict) -> dict:
        """Step 1: Publish job in internal HR system.

        Args:
            context: Execution context

        Returns:
            Result with job_id
        """
        # TODO: Implement actual HR system integration
        # For now, return a mock result

        logger.info("Publishing job in internal HR system...")

        # Mock implementation
        job_id = "JOB-2026-001"
        context["job_id"] = job_id

        return {
            "success": True,
            "output": {"job_id": job_id, "status": "published"},
            "error": None,
        }

    async def _publish_external(self, context: dict) -> dict:
        """Step 2: Publish job on recruitment website.

        Args:
            context: Execution context

        Returns:
            Result with external_job_id
        """
        # TODO: Implement actual recruitment website API integration

        logger.info(
            f"Publishing job on recruitment website (internal job_id: "
            f"{context.get('job_id')})..."
        )

        # Mock implementation
        external_job_id = "EXT-2026-001"
        context["external_job_id"] = external_job_id

        return {
            "success": True,
            "output": {
                "external_job_id": external_job_id,
                "url": "https://example.com/job/EXT-2026-001",
            },
            "error": None,
        }

    async def _get_candidates(self, context: dict) -> dict:
        """Step 3: Get candidate list from recruitment website.

        Args:
            context: Execution context

        Returns:
            Result with candidate list
        """
        # TODO: Implement actual candidate search

        logger.info("Fetching candidate list from recruitment website...")

        # Mock implementation
        candidates = [
            {
                "id": "CAND-001",
                "name": "张三",
                "position": "Python 开发工程师",
                "years_of_experience": 5,
            },
            {
                "id": "CAND-002",
                "name": "李四",
                "position": "高级 Python 工程师",
                "years_of_experience": 8,
            },
        ]

        # Select first candidate for this demo
        selected_candidate = candidates[0]
        context["candidate_id"] = selected_candidate["id"]

        return {
            "success": True,
            "output": {
                "candidates": candidates,
                "selected": selected_candidate,
            },
            "error": None,
        }

    async def _score_resume(self, context: dict) -> dict:
        """Step 4: Score candidate resume.

        Args:
            context: Execution context

        Returns:
            Result with resume score

        Note:
            If score < 70, the candidate is skipped.
        """
        # TODO: Implement actual resume scoring using LLM

        logger.info(
            f"Scoring resume for candidate {context.get('candidate_id')}..."
        )

        # Mock implementation - score based on years of experience
        mock_score = 85  # Mock score >= 70, so we proceed

        context["resume_score"] = mock_score

        if mock_score < 70:
            logger.warning(
                f"Resume score {mock_score} < 70, skipping this candidate"
            )
            return {
                "success": False,
                "output": {"score": mock_score, "passed": False},
                "error": f"Resume score {mock_score} below threshold (70)",
            }

        return {
            "success": True,
            "output": {"score": mock_score, "passed": True},
            "error": None,
        }

    async def _greet_candidate(self, context: dict) -> dict:
        """Step 5: Send greeting message to candidate.

        Args:
            context: Execution context

        Returns:
            Result with greeting status
        """
        # TODO: Implement actual messaging integration

        logger.info(
            f"Sending greeting to candidate {context.get('candidate_id')}..."
        )

        # Mock implementation
        return {
            "success": True,
            "output": {"status": "sent", "message": "您好，我们对您的简历很感兴趣！"},
            "error": None,
        }

    async def _reply_message(self, context: dict) -> dict:
        """Step 6: Handle candidate reply.

        Args:
            context: Execution context

        Returns:
            Result with conversation status
        """
        # TODO: Implement actual conversation handling

        logger.info("Handling candidate reply...")

        # Mock implementation - simulate a conversation
        return {
            "success": True,
            "output": {
                "status": "replied",
                "conversation": [
                    {"from": "candidate", "text": "谢谢，请问职位描述是什么？"},
                    {"from": "us", "text": "这是一个 Python 开发岗位..."},
                ],
            },
            "error": None,
        }

    async def _get_resume(self, context: dict) -> dict:
        """Step 7: Download candidate resume.

        Args:
            context: Execution context

        Returns:
            Result with resume file path
        """
        # TODO: Implement actual resume download

        logger.info(
            f"Downloading resume for candidate {context.get('candidate_id')}..."
        )

        # Mock implementation
        resume_path = "/tmp/resumes/zhangsan_resume.pdf"
        context["resume_file_path"] = resume_path

        return {
            "success": True,
            "output": {"file_path": resume_path, "format": "pdf"},
            "error": None,
        }

    async def _upload_resume(self, context: dict) -> dict:
        """Step 8: Upload resume to internal HR system.

        Args:
            context: Execution context

        Returns:
            Result with upload status
        """
        # TODO: Implement actual resume upload

        logger.info(
            f"Uploading resume to HR system (file: "
            f"{context.get('resume_file_path')})..."
        )

        # Mock implementation
        resume_id = "RES-2026-001"

        return {
            "success": True,
            "output": {"resume_id": resume_id, "status": "uploaded"},
            "error": None,
        }

    async def _submit_application(self, context: dict) -> dict:
        """Step 9: Submit application to internal job posting.

        Args:
            context: Execution context

        Returns:
            Result with application ID
        """
        # TODO: Implement actual application submission

        logger.info(
            f"Submitting application for job {context.get('job_id')} "
            f"with resume {context.get('resume_id')}..."
        )

        # Mock implementation
        application_id = "APP-2026-001"
        context["application_id"] = application_id

        return {
            "success": True,
            "output": {
                "application_id": application_id,
                "status": "submitted",
                "notification_sent": True,
            },
            "error": None,
        }

    def should_abort_on_failure(self, subtask_id: str, context: dict) -> bool:
        """Determine if execution should abort on subtask failure.

        For recruitment workflow:
        - Abort if resume scoring fails (score < 70)
        - Abort if application submission fails
        - Continue for other failures (logging only)

        Args:
            subtask_id: Failed subtask identifier
            context: Execution context

        Returns:
            True to abort, False to continue
        """
        # Critical failures that should abort the workflow
        critical_subtasks = ["score_resume", "submit_application"]

        if subtask_id in critical_subtasks:
            logger.warning(
                f"Critical subtask '{subtask_id}' failed, aborting workflow"
            )
            return True

        # For other failures, log and continue
        logger.warning(
            f"Non-critical subtask '{subtask_id}' failed, continuing workflow"
        )
        return False


# Factory function for easy instantiation
def create_recruitment_master_skill(
    agent: Any,
    plan_storage: PlanStorage,
    hr_system_client: Any | None = None,
    recruitment_api_client: Any | None = None,
) -> RecruitmentMasterSkill:
    """Create a Recruitment Master Skill instance.

    Args:
        agent: QwenPawAgent instance
        plan_storage: Plan storage instance
        hr_system_client: Optional HR system API client
        recruitment_api_client: Optional recruitment website API client

    Returns:
        RecruitmentMasterSkill instance
    """
    return RecruitmentMasterSkill(
        agent=agent,
        plan_storage=plan_storage,
        hr_system_client=hr_system_client,
        recruitment_api_client=recruitment_api_client,
    )
