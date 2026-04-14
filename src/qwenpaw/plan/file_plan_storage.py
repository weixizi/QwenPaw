# -*- coding: utf-8 -*-
"""File-based plan storage implementation."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

from .plan_storage import PlanData, PlanStorage, SubTaskData

logger = logging.getLogger(__name__)


class FilePlanStorage(PlanStorage):
    """File-based plan storage using JSON files.

    Directory structure:
    ~/.copaw/workspaces/{agent_id}/plans/
    ├── active/           # Currently active plans
    │   └── {plan_id}.json
    ├── archive/          # Completed/archived plans
    │   └── {plan_id}.json
    └── index.json        # Optional index for quick listing

    Attributes:
        base_dir: Base directory for plan storage
        agent_id: Agent identifier for workspace isolation
    """

    def __init__(self, base_dir: Path, agent_id: str):
        """Initialize file-based plan storage.

        Args:
            base_dir: Base directory (e.g., ~/.copaw/workspaces/)
            agent_id: Agent identifier for workspace isolation
        """
        self.base_dir = base_dir
        self.agent_id = agent_id
        self.plans_dir = base_dir / agent_id / "plans"
        self.active_dir = self.plans_dir / "active"
        self.archive_dir = self.plans_dir / "archive"

        # Ensure directories exist
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _get_plan_path(self, plan_id: str, state: str = "active") -> Path:
        """Get the file path for a plan.

        Args:
            plan_id: Plan identifier
            state: Plan state (active or archive)

        Returns:
            Path to the plan file
        """
        if state == "archived" or state == "completed" or state == "cancelled":
            return self.archive_dir / f"{plan_id}.json"
        return self.active_dir / f"{plan_id}.json"

    def _plan_to_dict(self, plan: PlanData) -> dict:
        """Convert PlanData to dictionary for JSON serialization.

        Args:
            plan: Plan data

        Returns:
            Dictionary representation
        """
        return {
            "plan_id": plan.plan_id,
            "name": plan.name,
            "description": plan.description,
            "expected_outcome": plan.expected_outcome,
            "subtasks": [
                {
                    "id": st.id,
                    "name": st.name,
                    "description": st.description,
                    "state": st.state,
                    "outcome": st.outcome,
                    "created_at": st.created_at.isoformat(),
                    "updated_at": st.updated_at.isoformat(),
                }
                for st in plan.subtasks
            ],
            "state": plan.state,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "completed_at": (
                plan.completed_at.isoformat()
                if plan.completed_at else None
            ),
            "metadata": plan.metadata,
        }

    def _dict_to_plan(self, data: dict) -> PlanData:
        """Convert dictionary to PlanData.

        Args:
            data: Dictionary representation

        Returns:
            Plan data
        """
        subtasks = [
            SubTaskData(
                id=st["id"],
                name=st["name"],
                description=st["description"],
                state=st["state"],
                outcome=st.get("outcome"),
                created_at=datetime.fromisoformat(st["created_at"]),
                updated_at=datetime.fromisoformat(st["updated_at"]),
            )
            for st in data["subtasks"]
        ]

        return PlanData(
            plan_id=data["plan_id"],
            name=data["name"],
            description=data["description"],
            expected_outcome=data["expected_outcome"],
            subtasks=subtasks,
            state=data["state"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at") else None
            ),
            metadata=data.get("metadata", {}),
        )

    async def save_plan(self, plan: PlanData) -> None:
        """Save a plan to storage.

        Args:
            plan: Plan data to save
        """
        path = self._get_plan_path(plan.plan_id, plan.state)
        data = self._plan_to_dict(plan)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved plan '{plan.name}' to {path}")

    async def load_plan(self, plan_id: str) -> PlanData | None:
        """Load a plan from storage.

        Args:
            plan_id: Plan identifier

        Returns:
            Plan data if found, None otherwise
        """
        # Try active directory first
        path = self.active_dir / f"{plan_id}.json"
        if not path.exists():
            # Try archive directory
            path = self.archive_dir / f"{plan_id}.json"

        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._dict_to_plan(data)

    async def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan from storage.

        Args:
            plan_id: Plan identifier

        Returns:
            True if deleted, False if not found
        """
        # Try active directory first
        path = self.active_dir / f"{plan_id}.json"
        if not path.exists():
            # Try archive directory
            path = self.archive_dir / f"{plan_id}.json"

        if not path.exists():
            return False

        path.unlink()
        logger.debug(f"Deleted plan '{plan_id}'")
        return True

    async def list_plans(
        self,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[PlanData]:
        """List plans from storage.

        Args:
            state: Optional state filter
            limit: Optional limit on results

        Returns:
            List of plan data
        """
        plans = []

        # Determine which directories to search
        dirs_to_search = []
        if state == "active":
            dirs_to_search = [self.active_dir]
        elif state in ("archived", "completed", "cancelled"):
            dirs_to_search = [self.archive_dir]
        else:
            # Search both directories
            dirs_to_search = [self.active_dir, self.archive_dir]

        for dir_path in dirs_to_search:
            if not dir_path.exists():
                continue

            for file_path in dir_path.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    plan = self._dict_to_plan(data)

                    # Apply state filter if specified
                    if state and plan.state != state:
                        continue

                    plans.append(plan)
                except Exception as e:
                    logger.warning(
                        f"Failed to load plan from {file_path}: {e}"
                    )

        # Sort by updated_at descending
        plans.sort(key=lambda p: p.updated_at, reverse=True)

        # Apply limit
        if limit:
            plans = plans[:limit]

        return plans

    async def update_plan(self, plan: PlanData) -> None:
        """Update an existing plan.

        Args:
            plan: Plan data with updates
        """
        plan.updated_at = datetime.now()
        await self.save_plan(plan)
        logger.debug(f"Updated plan '{plan.name}'")

    async def archive_plan(self, plan_id: str, state: str = "completed") -> bool:
        """Move a plan from active to archive.

        Args:
            plan_id: Plan identifier
            state: Final state (completed, archived, or cancelled)

        Returns:
            True if archived, False if not found
        """
        plan = await self.load_plan(plan_id)
        if plan is None:
            return False

        # Update state and completed_at
        plan.state = state  # type: ignore[assignment]
        if state in ("completed", "archived"):
            plan.completed_at = datetime.now()

        # Save to archive directory
        await self.save_plan(plan)

        # Delete from active directory
        active_path = self.active_dir / f"{plan_id}.json"
        if active_path.exists():
            active_path.unlink()

        logger.info(f"Archived plan '{plan.name}' with state '{state}'")
        return True

    async def get_active_plan_count(self) -> int:
        """Get the count of active plans.

        Returns:
            Number of active plans
        """
        if not self.active_dir.exists():
            return 0
        return len(list(self.active_dir.glob("*.json")))
