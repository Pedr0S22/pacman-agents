from typing import Tuple, List, Optional
from utils.types_utils import Coord, Percept
from .KB import KnowledgeBase

class Ghost:
    """
    This is the generic Ghost agent class.
    Its only job is to hold a Knowledge Base and pass messages to it.
    """
    
    kb: KnowledgeBase

    def __init__(self, kb: KnowledgeBase):
        """
        Initializes the Ghost by plugging in the KB.
        
        Args:
            kb: An object that follows the KnowledgeBase protocol
                This can be a KnowledgeBaseA, KnowledgeBaseB, or KnowledgeBaseC.
        """
        self.kb = kb

    def get_next_move(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ) -> str:
        """
        The main loop, following the TELL/ASK model.
        """
        
        # 1. TELL KB all the new facts.
        self.kb.tell(my_pos, pacman_pos, other_ghost_pos, percepts)
        
        # 2. ASK the KB for its final, calculated move.
        return self.kb.ask()