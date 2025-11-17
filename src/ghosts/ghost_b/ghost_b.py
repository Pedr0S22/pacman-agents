from typing import Tuple, List, Optional
from utils.types_utils import Coord, Percept
from utils.path_utils import bfs_pathfinder, get_move_from_path, find_nearest_coord
from ghost_b_kb import KnowledgeBaseB

class GhostB:
    """
    Ghost B: The "Ambusher" (PL Agent)
    - Logic: Propositional Logic (rule-based)
    - KB: Learns map (walls, pellets, junctions) from scratch.
    - Behavior:
        1. Chases Pac-Man on sight.
        2. If pellet clue is found, goes to *nearest junction* to ambush.
        3. If no clues, "patrols" by camping at nearest junction.
        4. If map is small, explores to find junctions.
    """
    def __init__(self):
        self.kb = KnowledgeBaseB()
        self.goal: Optional[Coord] = None
        self.current_path: List[Coord] = []

    def get_next_move(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ) -> str:
        
        # --- 0. Add self to known safe tiles ---
        # This is the "bootstrapping" for the map
        if my_pos not in self.kb.safe_tiles:
            self.kb.safe_tiles.add(my_pos)
            self.kb.unknown_tiles.discard(my_pos)

        # --- 1. Update KB from Percepts ---
        self.kb.update_from_percepts(percepts)
        
        # --- 2. Run Inference Rules (Determine Goal) ---
        new_goal = None
        
        # Rule 1: Chase (Highest Priority)
        if pacman_pos:
            new_goal = pacman_pos
        
        # Rule 2: Ambush (If no sight, but have a clue)
        else:
            clue = self.kb.get_clue()
            if clue:
                # Find nearest junction TO THE CLUE
                ambush_spot = find_nearest_coord(
                    start_pos=clue, 
                    target_coords=self.kb.junctions, 
                    safe_tiles=self.kb.safe_tiles
                )
                if ambush_spot:
                    new_goal = ambush_spot
                else:
                    # No junctions found, just go to the clue
                    new_goal = clue
        
        # Rule 3: Patrol/Explore (No sight, no clue)
        if new_goal is None:
            # Try to patrol (camp at a junction)
            patrol_goal = find_nearest_coord(
                start_pos=my_pos,
                target_coords=self.kb.junctions,
                safe_tiles=self.kb.safe_tiles
            )
            if patrol_goal:
                new_goal = patrol_goal
            else:
                # No junctions found, explore unknown tiles
                explore_goal = find_nearest_coord(
                    start_pos=my_pos,
                    target_coords=self.kb.unknown_tiles,
                    safe_tiles=self.kb.safe_tiles
                )
                if explore_goal:
                    new_goal = explore_goal

        # --- 3. Update Goal and Path ---
        
        # If goal is new or we have no path, find a new path
        if new_goal and (new_goal != self.goal or not self.current_path):
            self.goal = new_goal
            path = bfs_pathfinder(
                start_pos=my_pos,
                goal_pos=self.goal,
                safe_tiles=self.kb.safe_tiles
            )
            self.current_path = path if path else []
        
        # If we reached our goal, clear path
        if my_pos == self.goal:
            self.current_path = []
            
        # --- 4. Get Move from Path ---
        if self.current_path:
            # Pop our current position
            if self.current_path[0] == my_pos:
                self.current_path.pop(0)
            
            if self.current_path:
                return get_move_from_path(my_pos, [my_pos] + self.current_path)

        return 'WAIT'