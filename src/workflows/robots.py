"""
YeyoOS — Workflow Robots
Pool of robot workers assigned to workflow executions.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("yeyoos.workflows.robots")


@dataclass
class Robot:
    """A single robot worker that can be assigned to a workflow execution."""

    id: str
    name: str
    status: str = "idle"
    current_execution_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    completed_count: int = 0

    def to_dict(self) -> dict:
        """Serialize the robot state to a plain dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "current_execution_id": self.current_execution_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "completed_count": self.completed_count,
        }


class RobotPool:
    """Fixed-size pool of :class:`Robot` workers with overflow via temporary robots."""

    def __init__(self, pool_size: int = 5) -> None:
        """Create *pool_size* idle robots named Robot-1 … Robot-{pool_size}."""
        self._robots: list[Robot] = [
            Robot(id=f"robot-{i}", name=f"Robot-{i}")
            for i in range(1, pool_size + 1)
        ]

    def acquire(self, execution_id: str) -> Optional[Robot]:
        """Assign an idle robot to *execution_id* and return it.

        If no idle robot is available a temporary robot is created and a
        warning is logged.  Returns ``None`` only on unexpected errors.
        """
        for robot in self._robots:
            if robot.status == "idle":
                robot.status = "busy"
                robot.current_execution_id = execution_id
                robot.assigned_at = datetime.now(timezone.utc)
                logger.info(f"{robot.name} assigned to execution {execution_id}")
                return robot

        temp_id = f"temp-robot-{uuid.uuid4().hex[:8]}"
        temp_robot = Robot(
            id=temp_id,
            name=temp_id,
            status="busy",
            current_execution_id=execution_id,
            assigned_at=datetime.now(timezone.utc),
        )
        self._robots.append(temp_robot)
        logger.warning(
            f"No idle robots available — created temporary robot {temp_id} "
            f"for execution {execution_id}"
        )
        return temp_robot

    def release(self, robot_id: str) -> None:
        """Mark the robot identified by *robot_id* as idle."""
        robot = self.get_robot(robot_id)
        if robot is None:
            logger.warning(f"Cannot release unknown robot {robot_id}")
            return

        robot.status = "idle"
        robot.current_execution_id = None
        robot.assigned_at = None
        robot.completed_count += 1
        logger.info(f"{robot.name} released (completed: {robot.completed_count})")

    def get_status(self) -> list[dict]:
        """Return the status of every robot in the pool as a list of dicts."""
        return [robot.to_dict() for robot in self._robots]

    def get_robot(self, robot_id: str) -> Optional[Robot]:
        """Find and return a robot by *robot_id*, or ``None`` if not found."""
        for robot in self._robots:
            if robot.id == robot_id:
                return robot
        return None

    def get_busy_count(self) -> int:
        """Return the number of robots currently busy."""
        return sum(1 for r in self._robots if r.status == "busy")
