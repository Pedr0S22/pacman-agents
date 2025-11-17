from typing import Optional
from utils.types_utils import Coord, Percept
from ghost_a_kb import KnowledgeBaseA

class GhostA:
    """
    Ghost A (PL Agent)
    
    - get_next_move:
        1. TELLs the KB all new information.
        2. ASKs the KB for one final, safe action.
    """
    def __init__(self, patrol_points: Optional[list[Coord]] = None):
        self.kb = KnowledgeBaseA(patrol_points)

    def get_next_move(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        percepts: Percept
    ) -> str:
        
        # TELL the KB all current facts and let it update its internal state.
        self.kb.tell(my_pos, pacman_pos, percepts)
        
        # ASK the KB for a single, safe, decisive action.
        return self.kb.ask()