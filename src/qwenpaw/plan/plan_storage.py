# -*- coding: utf-8 -*-
"""Plan storage interface and data models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class SubTaskData:
    """Subtask data model.

    Attributes:
        id: Subtask identifier (index in subtasks array)
        name: Subtask name
        description: Subtask description
        state: Subtask state (todo, in_progress, done, abandoned)
        outcome: Optional outcome message after completion
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: int
    name: str
    description: str
    state: Literal["todo", "in_progress", "done", "abandoned"] = "todo"
    outcome: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PlanData:
    """Plan data model.

    Attributes:
        plan_id: Unique plan identifier
        name: Plan name
        description: Plan description
        expected_outcome: Expected outcome description
        subtasks: List of subtask data
        state: Plan state (active, completed, archived, cancelled)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        completed_at: Optional completion timestamp
        metadata: Optional metadata dictionary
    """
    plan_id: str
    name: str
    description: str
    expected_outcome: str
    subtasks: list[SubTaskData] = field(default_factory=list)
    state: Literal["active", "completed", "archived", "cancelled"] = "active"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


class PlanStorage(ABC):
    """Abstract base class for plan storage.

    Implementations can use different backends:
    - File system (JSON files)
    - Database (SQLite, PostgreSQL)
    - In-memory (for testing)
    """

    @abstractmethod
    async def save_plan(self, plan: PlanData) -> None:
        """Save a plan to storage.

        Args:
            plan: Plan data to save
        """
        pass

    @abstractmethod
    async def load_plan(self, plan_id: str) -> PlanData | None:
        """Load a plan from storage.

        Args:
            plan_id: Plan identifier

        Returns:
            Plan data if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan from storage.

        Args:
            plan_id: Plan identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def update_plan(self, plan: PlanData) -> None:
        """Update an existing plan.

        Args:
            plan: Plan data with updates
        """
        pass
