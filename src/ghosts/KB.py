from typing import Protocol, Tuple, List, Optional
from utils.types_utils import Coord, Percept

class KnowledgeBase(Protocol):
    """
    This Interface defines the "contract" that all our KBs must follow.
    Any class that has a "tell" and "ask" method with
    these exact signatures will be considered a valid KB.
    """

    def tell(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ) -> None:
        """
        TELLs the KB all new facts from the environment.
        The KB updates its internal state (and learned map for ghosts B and C).
        """
        ...

    def ask(self) -> str:
        """
        ASKs the KB for a single, final, safe action.
        All inference, logic, and pathfinding happens here.
        """
        ...