from .miner import MinerAgent
from .scientist import ScientistAgent
from .tester import TesterAgent
from .writer import WriterAgent
from .optimizer import OptimizerAgent
from .guard import GuardAgent
from .sage import SageAgent
from .robot import RobotAgent

AGENTS = {
    "miner": MinerAgent,
    "scientist": ScientistAgent,
    "tester": TesterAgent,
    "writer": WriterAgent,
    "optimizer": OptimizerAgent,
    "guard": GuardAgent,
    "sage": SageAgent,
    "robot": RobotAgent,
}


def get_agent(name: str, ia_provider=None, memory=None):
    cls = AGENTS.get(name)
    if cls is None:
        raise ValueError(f"Unknown agent: {name}")
    return cls(ia_provider=ia_provider, memory=memory)


def list_agents():
    return [
        {
            "name": n,
            "emoji": cls.emoji,
            "building": cls.building,
            "description": cls.description,
            "quick_tasks": cls.quick_tasks,
        }
        for n, cls in AGENTS.items()
    ]
