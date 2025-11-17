from typing import Optional
from utils.types_utils import Coord, Percept
from ghost_b_kb import KnowledgeBaseB

class GhostB:
    """
    Ghost B: The "Ambusher" (PL Agent)
    
    This class is now a "dumb" shell that follows the TELL/ASK model.
    - get_next_move:
        1. TELLs the KB all new information.
        2. ASKs the KB for one final, safe action.
    """
    def __init__(self):
        self.kb = KnowledgeBaseB()

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