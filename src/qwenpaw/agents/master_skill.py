# -*- coding: utf-8 -*-
"""Master Skill base class for PlanNotebook-based multi-step workflows.

This module provides the base class for creating master skills that
orchestrate complex multi-step workflows using PlanNotebook.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Literal

from agentscope.message import Msg

from ..plan import PlanStorage, PlanData

logger = logging.getLogger(__name__)


class MasterSkill(ABC):
    """Base class for Master Skills.

    Master Skills are designed for complex multi-step workflows that require:
    - State tracking across multiple steps
    - Progress visibility
    - Conditional branching
    - Long-running execution with waiting periods

    The Master Skill pattern:
    1. Creates a PlanNotebook with defined subtasks
    2. Temporarily binds it to agent.plan_notebook
    3. Executes subtasks in a loop
    4. Archives the plan after completion

    Attributes:
        agent: The agent instance to bind PlanNotebook to
        plan_storage: Plan storage instance
        _original_plan_notebook: Saved plan_notebook for restoration
    """

    def __init__(self, agent: Any, plan_storage: PlanStorage):
        """Initialize Master Skill.

        Args:
            agent: QwenPawAgent instance
            plan_storage: Plan storage instance for persistence
        """
        self.agent = agent
        self.plan_storage = plan_storage
        self._original_plan_notebook = None
        self._current_plan_id: str | None = None

    @abstractmethod
    async def create_plan(self) -> dict:
        """Create the plan definition.

        Returns:
            Plan definition dictionary with:
            - name: str
            - description: str
            - expected_outcome: str
            - subtasks: list[dict] with name, description, id
        """
        pass

    @abstractmethod
    async def execute_subtask(self, subtask_id: str, context: dict) -> dict:
        """Execute a single subtask.

        Args:
            subtask_id: Subtask identifier
            context: Execution context (shared across subtasks)

        Returns:
            Subtask result dictionary with:
            - success: bool
            - output: Any (subtask-specific output)
            - error: str | None (error message if failed)
        """
        pass

    @abstractmethod
    def get_skill_name(self) -> str:
        """Get the skill name for logging and identification.

        Returns:
            Skill name string
        """
        pass

    async def execute(self, context: dict | None = None) -> dict:
        """Execute the master skill workflow.

        This is the main entry point that:
        1. Creates and binds PlanNotebook
        2. Executes subtasks in a loop
        3. Handles failures and retries
        4. Archives the plan on completion

        Args:
            context: Optional initial context (shared across subtasks)

        Returns:
            Execution result with:
            - success: bool
            - plan_id: str
            - output: dict (aggregated outputs)
            - error: str | None
        """
        context = context or {}
        skill_name = self.get_skill_name()
        logger.info(f"Starting {skill_name} execution")

        # Step 1: Create plan definition
        plan_def = await self.create_plan()

        # Step 2: Save the original plan_notebook (usually None)
        self._original_plan_notebook = self.agent.set_plan_notebook(None)

        try:
            # Step 3: Initialize plan storage and create PlanNotebook
            if self.agent.get_plan_storage() is None:
                self.agent.init_plan_storage(self.plan_storage)

            plan_notebook = await self.agent.create_plan_notebook(
                name=plan_def["name"],
                description=plan_def["description"],
                expected_outcome=plan_def["expected_outcome"],
                subtasks=plan_def["subtasks"],
            )

            # Get plan_id from the created plan
            self._current_plan_id = getattr(
                plan_notebook, "_PlanNotebook__plan_id", None
            )

            # Step 4: Bind PlanNotebook to agent
            self.agent.set_plan_notebook(plan_notebook)
            logger.info(
                f"Bound PlanNotebook '{plan_def['name']}' to agent "
                f"({len(plan_def['subtasks'])} subtasks)"
            )

            # Step 5: Execute subtasks in a loop
            subtasks = plan_def["subtasks"]
            outputs = {}
            failed_subtasks = []

            for i, subtask_def in enumerate(subtasks):
                subtask_id = subtask_def.get("id", str(i))
                subtask_name = subtask_def["name"]

                logger.info(
                    f"Executing subtask {i + 1}/{len(subtasks)}: {subtask_name}"
                )

                try:
                    # Update subtask state to in_progress
                    await plan_notebook.update_subtask_state(
                        subtask_idx=i,
                        state="in_progress",
                    )

                    # Execute the subtask
                    result = await self.execute_subtask(subtask_id, context)

                    if result.get("success"):
                        # Mark as done
                        await plan_notebook.finish_subtask(
                            subtask_idx=i,
                            subtask_outcome=result.get("output"),
                        )
                        outputs[subtask_id] = result.get("output")
                        logger.info(f"Subtask '{subtask_name}' completed")
                    else:
                        # Mark as abandoned
                        await plan_notebook.update_subtask_state(
                            subtask_idx=i,
                            state="abandoned",
                        )
                        failed_subtasks.append({
                            "id": subtask_id,
                            "name": subtask_name,
                            "error": result.get("error"),
                        })
                        logger.warning(
                            f"Subtask '{subtask_name}' failed: "
                            f"{result.get('error')}"
                        )

                        # Check if we should abort
                        if self.should_abort_on_failure(subtask_id, context):
                            raise SubtaskExecutionError(
                                f"Subtask '{subtask_name}' failed: "
                                f"{result.get('error')}"
                            )

                except SubtaskExecutionError:
                    raise
                except Exception as e:
                    logger.exception(
                        f"Subtask '{subtask_name}' threw exception: {e}"
                    )
                    await plan_notebook.update_subtask_state(
                        subtask_idx=i,
                        state="abandoned",
                    )
                    failed_subtasks.append({
                        "id": subtask_id,
                        "name": subtask_name,
                        "error": str(e),
                    })

                    if self.should_abort_on_failure(subtask_id, context):
                        raise

            # Step 6: Determine final state
            if failed_subtasks:
                logger.warning(
                    f"{skill_name} completed with {len(failed_subtasks)} "
                    f"failed subtask(s)"
                )
                final_state = "completed"  # Still mark as completed
            else:
                logger.info(f"{skill_name} completed successfully")
                final_state = "completed"

            return {
                "success": len(failed_subtasks) == 0,
                "plan_id": self._current_plan_id,
                "output": outputs,
                "failed_subtasks": failed_subtasks,
                "final_state": final_state,
            }

        except SubtaskExecutionError as e:
            logger.error(f"{skill_name} aborted: {e}")
            return {
                "success": False,
                "plan_id": self._current_plan_id,
                "output": context,
                "error": str(e),
                "final_state": "cancelled",
            }

        except Exception as e:
            logger.exception(f"{skill_name} failed with exception: {e}")
            return {
                "success": False,
                "plan_id": self._current_plan_id,
                "output": context,
                "error": str(e),
                "final_state": "cancelled",
            }

        finally:
            # Step 7: Always restore original plan_notebook
            self.agent.set_plan_notebook(self._original_plan_notebook)
            logger.debug(f"Restored original plan_notebook")

            # Step 8: Archive the plan (non-blocking)
            if self._current_plan_id:
                try:
                    await self._archive_plan(final_state="completed")
                except Exception as e:
                    logger.warning(f"Failed to archive plan: {e}")

    def should_abort_on_failure(
        self,
        subtask_id: str,
        context: dict,
    ) -> bool:
        """Determine if execution should abort on subtask failure.

        Override this method to implement custom failure handling logic.

        Args:
            subtask_id: Failed subtask identifier
            context: Execution context

        Returns:
            True to abort, False to continue with next subtask
        """
        return False  # Default: continue execution

    async def _archive_plan(
        self,
        final_state: Literal["completed", "cancelled"] = "completed",
    ) -> bool:
        """Archive the current plan.

        Args:
            final_state: Final plan state

        Returns:
            True if archived successfully
        """
        if not self._current_plan_id:
            return False

        success = await self.agent.archive_plan(
            plan_id=self._current_plan_id,
            state=final_state,
        )

        if success:
            logger.info(
                f"Archived plan '{self._current_plan_id}' "
                f"with state '{final_state}'"
            )

        return success

    async def get_plan_status(self) -> PlanData | None:
        """Get the current plan status.

        Returns:
            Plan data if available, None otherwise
        """
        if not self._current_plan_id:
            return None
        return await self.agent.get_plan_status(self._current_plan_id)


class SubtaskExecutionError(Exception):
    """Raised when a subtask execution fails."""

    pass
