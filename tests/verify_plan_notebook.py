# -*- coding: utf-8 -*-
"""PlanNotebook integration verification script.

Run this script to verify that PlanNotebook integration is working correctly.
"""

import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors during tests
    format="%(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Enable info logging for test progress only
logging.getLogger("__main__").setLevel(logging.INFO)


async def verify_plan_storage():
    """Verify PlanStorage interface and FilePlanStorage implementation."""
    logger.info("=" * 60)
    logger.info("TEST 1: Verify PlanStorage")
    logger.info("=" * 60)

    from qwenpaw.plan import PlanStorage, FilePlanStorage, PlanData, SubTaskData
    from datetime import datetime

    # Create temporary directory for testing
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Create FilePlanStorage
        storage = FilePlanStorage(base_dir=tmp_path, agent_id="test-agent")
        logger.info(f"✓ Created FilePlanStorage at {storage.plans_dir}")

        # 2. Create a test plan
        plan = PlanData(
            plan_id="test-plan-001",
            name="测试计划",
            description="这是一个测试计划",
            expected_outcome="验证 PlanStorage 功能",
            subtasks=[
                SubTaskData(id=0, name="步骤 1", description="第一步"),
                SubTaskData(id=1, name="步骤 2", description="第二步"),
            ],
            state="active",
        )
        logger.info(f"✓ Created test plan: {plan.name}")

        # 3. Save plan
        await storage.save_plan(plan)
        logger.info(f"✓ Saved plan to {storage.active_dir / 'test-plan-001.json'}")

        # 4. Load plan
        loaded_plan = await storage.load_plan("test-plan-001")
        assert loaded_plan is not None, "Failed to load plan"
        assert loaded_plan.name == "测试计划", "Plan name mismatch"
        assert len(loaded_plan.subtasks) == 2, "Subtask count mismatch"
        logger.info(f"✓ Loaded plan: {loaded_plan.name} ({len(loaded_plan.subtasks)} subtasks)")

        # 5. List plans
        plans = await storage.list_plans()
        assert len(plans) == 1, "Plan count mismatch"
        logger.info(f"✓ Listed plans: {len(plans)} plan(s)")

        # 6. Update plan
        loaded_plan.state = "completed"
        loaded_plan.completed_at = datetime.now()
        await storage.update_plan(loaded_plan)
        logger.info("✓ Updated plan state to 'completed'")

        # 7. Archive plan
        success = await storage.archive_plan("test-plan-001", state="completed")
        assert success, "Failed to archive plan"

        # Verify moved to archive
        archive_path = storage.archive_dir / "test-plan-001.json"
        active_path = storage.active_dir / "test-plan-001.json"
        assert archive_path.exists(), "Archived plan not found"
        assert not active_path.exists(), "Active plan should be deleted"
        logger.info(f"✓ Archived plan to {archive_path}")

        # 8. List by state
        active_plans = await storage.list_plans(state="active")
        completed_plans = await storage.list_plans(state="completed")
        assert len(active_plans) == 0, "Should have no active plans"
        assert len(completed_plans) == 1, "Should have 1 completed plan"
        logger.info(f"✓ Filter by state: {len(active_plans)} active, {len(completed_plans)} completed")

        logger.info("\n✅ PlanStorage verification PASSED\n")
        return True


async def verify_master_skill():
    """Verify MasterSkill base class."""
    logger.info("=" * 60)
    logger.info("TEST 2: Verify MasterSkill Base Class")
    logger.info("=" * 60)

    from qwenpaw.agents.master_skill import MasterSkill, SubtaskExecutionError
    from qwenpaw.plan import FilePlanStorage

    # Create a mock agent
    class MockAgent:
        def __init__(self):
            self.plan_notebook = None
            self._plan_storage = None

        def set_plan_notebook(self, plan):
            old = self.plan_notebook
            self.plan_notebook = plan
            return old

        def get_plan_storage(self):
            return self._plan_storage

        def init_plan_storage(self, storage):
            self._plan_storage = storage
            return storage

        async def create_plan_notebook(self, name, description, expected_outcome, subtasks):
            # Mock PlanNotebook
            class MockPlanNotebook:
                def __init__(self):
                    self._plan_id = "mock-plan-001"
                    # Make plan_id accessible via getattr like the real implementation
                    self.__dict__["_PlanNotebook__plan_id"] = "mock-plan-001"

                async def update_subtask_state(self, subtask_idx, state):
                    logger.info(f"  → Updated subtask {subtask_idx} state: {state}")

                async def finish_subtask(self, subtask_idx, subtask_outcome):
                    logger.info(f"  → Finished subtask {subtask_idx}: {subtask_outcome}")

            return MockPlanNotebook()

        async def archive_plan(self, plan_id, state):
            logger.info(f"  → Archived plan {plan_id} with state {state}")
            return True

    # Create a test MasterSkill
    class TestMasterSkill(MasterSkill):
        def get_skill_name(self) -> str:
            return "test_master"

        async def create_plan(self) -> dict:
            return {
                "name": "测试工作流",
                "description": "测试 MasterSkill 功能",
                "expected_outcome": "验证子任务执行",
                "subtasks": [
                    {"id": "step1", "name": "第一步", "description": "测试步骤 1"},
                    {"id": "step2", "name": "第二步", "description": "测试步骤 2"},
                ],
            }

        async def execute_subtask(self, subtask_id: str, context: dict) -> dict:
            logger.info(f"  → Executing subtask: {subtask_id}")
            output = {
                "success": True,
                "output": {f"{subtask_id}": "ok"},
                "error": None,
            }
            logger.info(f"  → Subtask result: {output}")
            return output

    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agent = MockAgent()
        plan_storage = FilePlanStorage(base_dir=tmp_path, agent_id="test-agent")
        skill = TestMasterSkill(agent=agent, plan_storage=plan_storage)

        # Execute the skill
        result = await skill.execute(context={"test": "data"})

        # Verify result
        assert result["success"] is True, "Skill execution failed"
        assert result["plan_id"] == "mock-plan-001", "Plan ID mismatch"
        assert "step1" in result["output"], f"Missing step1 output, got: {result['output'].keys()}"
        assert "step2" in result["output"], f"Missing step2 output, got: {result['output'].keys()}"
        assert agent.plan_notebook is None, "PlanNotebook should be unbound after execution"

        logger.info(f"✓ MasterSkill executed successfully")
        logger.info(f"  - Plan ID: {result['plan_id']}")
        logger.info(f"  - Success: {result['success']}")
        logger.info(f"  - Output keys: {list(result['output'].keys())}")
        logger.info(f"  - PlanNotebook unbound: {agent.plan_notebook is None}")

        logger.info("\n✅ MasterSkill verification PASSED\n")
        return True


async def verify_recruitment_skill():
    """Verify RecruitmentMasterSkill implementation."""
    logger.info("=" * 60)
    logger.info("TEST 3: Verify RecruitmentMasterSkill")
    logger.info("=" * 60)

    from qwenpaw.agents.skills.recruitment_master.skill import RecruitmentMasterSkill
    from qwenpaw.plan import FilePlanStorage

    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        plan_storage = FilePlanStorage(base_dir=tmp_path, agent_id="test-agent")

        # Create skill without agent (just test static methods)
        class MockAgent:
            pass

        skill = RecruitmentMasterSkill(
            agent=MockAgent(),
            plan_storage=plan_storage,
        )

        # Verify plan definition
        plan_def = await skill.create_plan()
        assert plan_def["name"] == "招聘流程", "Plan name mismatch"
        assert len(plan_def["subtasks"]) == 9, f"Expected 9 subtasks, got {len(plan_def['subtasks'])}"
        logger.info(f"✓ Recruitment plan: {plan_def['name']} ({len(plan_def['subtasks'])} subtasks)")

        # Verify subtask IDs
        expected_ids = [
            "publish_internal", "publish_external", "get_candidates",
            "score_resume", "greet_candidate", "reply_message",
            "get_resume", "upload_resume", "submit_application"
        ]
        actual_ids = [st["id"] for st in plan_def["subtasks"]]
        assert actual_ids == expected_ids, f"Subtask IDs mismatch: {actual_ids}"
        logger.info(f"✓ Subtask IDs verified")

        # Verify skill name
        assert skill.get_skill_name() == "recruitment_master", "Skill name mismatch"
        logger.info(f"✓ Skill name: {skill.get_skill_name()}")

        # Verify execute_subtask (mock implementation) - just test one subtask
        result = await skill.execute_subtask("publish_internal", {})
        assert result["success"] is True, "Subtask execution failed"
        assert "job_id" in result["output"], "Missing job_id in output"
        logger.info(f"✓ Subtask 'publish_internal' executed (mock)")

        logger.info("\n✅ RecruitmentMasterSkill verification PASSED\n")
        return True


async def verify_agent_integration():
    """Verify QwenPawAgent PlanNotebook methods exist."""
    logger.info("=" * 60)
    logger.info("TEST 4: Verify QwenPawAgent Integration")
    logger.info("=" * 60)

    # Just verify the methods exist (can't fully test without full agent setup)
    try:
        from qwenpaw.agents.react_agent import QwenPawAgent

        # Check methods exist
        methods = [
            "init_plan_storage",
            "create_plan_notebook",
            "set_plan_notebook",
            "archive_plan",
            "get_plan_status",
            "list_plans",
            "get_plan_storage",
        ]

        for method_name in methods:
            assert hasattr(QwenPawAgent, method_name), f"Missing method: {method_name}"
            logger.info(f"✓ QwenPawAgent.{method_name} exists")

        logger.info("\n✅ QwenPawAgent integration verification PASSED\n")
        return True

    except Exception as e:
        logger.error(f"❌ QwenPawAgent integration verification FAILED: {e}")
        return False


async def main():
    """Run all verification tests."""
    logger.info("\n" + "=" * 60)
    logger.info("PlanNotebook Integration Verification")
    logger.info("=" * 60 + "\n")

    results = []

    # Test 1: PlanStorage
    results.append(("PlanStorage", await verify_plan_storage()))

    # Test 2: MasterSkill
    results.append(("MasterSkill", await verify_master_skill()))

    # Test 3: RecruitmentMasterSkill
    results.append(("RecruitmentMasterSkill", await verify_recruitment_skill()))

    # Test 4: QwenPawAgent Integration
    results.append(("QwenPawAgent", await verify_agent_integration()))

    # Summary
    logger.info("=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {name}: {status}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 All verifications PASSED! PlanNotebook integration is working correctly.")
        return 0
    else:
        logger.info("\n⚠️ Some verifications FAILED. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
