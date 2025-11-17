from typing import Tuple, Set, List, Optional
from utils.types_utils import Coord, Percept, MOVES
from utils.path_utils import *
from ghosts.KB import KnowledgeBase
import random

class KnowledgeBaseB(KnowledgeBase):
    """
    KB for Ghost B.
    This is a "smart" PL KB. It learns the map, maintains beliefs, and contains all
    inference and pathfinding logic.
    """
    def __init__(self):
        # --- The Learned Map ---
        self.walls: Set[Coord] = set()
        self.safe_tiles: Set[Coord] = set()
        self.seen_pellets: Set[Coord] = set()
        self.junctions: Set[Coord] = set()
        self.unknown_tiles: Set[Coord] = set() # For exploration
        
        # --- Beliefs ---
        self.pacman_clue: Optional[Coord] = None
        self.clue_age: int = 0
        self.max_clue_age: int = 20 # Give up on a clue after 20 steps
        
        # --- Stored Percepts  ---
        self.my_pos: Coord = (0, 0)
        self.pacman_pos_percept: Optional[Coord] = None
        self.percepts: Percept = {}
        
        # --- Pathfinding State ---
        self.goal: Optional[Coord] = None
        self.current_path: List[Coord] = []
        
        # Add a starting tile to explore from
        self.unknown_tiles.add((0,0))


    def tell(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]], # <-- Added this
        percepts: Percept
    ):
        """
        Stores all new facts and updates the KB's internal map
        and belief state.
        """
        # (Ghost B ignores other_ghost_pos, but it must accept the arg)
        
        # --- 1. Store Current Facts ---
        self.my_pos = my_pos
        self.pacman_pos_percept = pacman_pos
        self.percepts = percepts
        
        # ... (rest of tell method is unchanged) ...
        if my_pos not in self.safe_tiles:
            self._add_safe_tile(my_pos)

        # --- 2. Learn from Percepts (Update Map) ---
        new_clue = None
        for pos, item in percepts.items():
            if item == "WALL":
                self.walls.add(pos)
                self.safe_tiles.discard(pos)
                self.unknown_tiles.discard(pos)
            
            elif item == "PELLET":
                self._add_safe_tile(pos)
                self.seen_pellets.add(pos) # Add to "memory"
            
            elif item == "EMPTY":
                self._add_safe_tile(pos)
                # --- The "Aha!" Moment (Belief Maintenance) ---
                if pos in self.seen_pellets:
                    new_clue = pos # Found a clue! Pac-Man was here.
            
            else: # Pac-Man, Other Ghosts
                self._add_safe_tile(pos)
        
        # --- 3. Update Beliefs (Clues) ---
        if pacman_pos:
            # Direct sight invalidates any old clue
            self.pacman_clue = None
            self.clue_age = 0
        elif new_clue:
            # We found a new clue
            self.pacman_clue = new_clue
            self.clue_age = 0
        elif self.pacman_clue:
            # Age the current clue
            self.clue_age += 1
            if self.clue_age > self.max_clue_age:
                self.pacman_clue = None # Clue is stale
                self.clue_age = 0

    def ask(self) -> str:
        """
        Runs inference on the current KB, determines a goal,
        finds a path, and returns a single, safe action.
        """
        
        # --- 1. Run Inference Rules (Determine Goal) ---
        new_goal = None
        
        # Rule 1: Chase (Highest Priority)
        if self.pacman_pos_percept:
            new_goal = self.pacman_pos_percept
        
        # Rule 2: Ambush (If no sight, but have a clue)
        else:
            if self.pacman_clue:
                # Find nearest junction TO THE CLUE
                ambush_spot = find_nearest_coord(
                    start_pos=self.pacman_clue,
                    target_coords=self.junctions,
                    safe_tiles=self.safe_tiles
                )
                if ambush_spot:
                    new_goal = ambush_spot
                else:
                    # No junctions found, just go to the clue
                    new_goal = self.pacman_clue
        
        # Rule 3: Patrol/Explore (No sight, no clue)
        if new_goal is None:
            # Try to patrol (camp at a junction)
            patrol_goal = find_nearest_coord(
                start_pos=self.my_pos,
                target_coords=self.junctions,
                safe_tiles=self.safe_tiles
            )
            if patrol_goal:
                new_goal = patrol_goal
            else:
                # No junctions found, explore unknown tiles
                explore_goal = find_nearest_coord(
                    start_pos=self.my_pos,
                    target_coords=self.unknown_tiles,
                    safe_tiles=self.safe_tiles
                )
                new_goal = explore_goal # Can be None if map is fully explored

        # --- 2. Update Goal and Path (Pathfinding Logic) ---
        
        # If no goal, we're done
        if new_goal is None:
            # Fully explored and no clues, just wait or move randomly
            return self._get_random_safe_move()

        # If goal is new or we have no path, find a new path
        if new_goal and (new_goal != self.goal or not self.current_path):
            self.goal = new_goal
            path = bfs_pathfinder(
                start_pos=self.my_pos,
                goal_pos=self.goal,
                safe_tiles=self.safe_tiles
            )
            self.current_path = path if path else []
        
        # If we reached our goal, clear path
        if self.my_pos == self.goal:
            self.current_path = []
            
        # --- 3. Get Move from Path ---
        if self.current_path:
            # Handle path consumption
            current_step_index = -1
            try:
                current_step_index = self.current_path.index(self.my_pos)
            except ValueError:
                # We are off-path, recalculate
                self.current_path = []
                if self.goal:
                    path = bfs_pathfinder(self.my_pos, self.goal, self.safe_tiles)
                    self.current_path = path if path else []
                    current_step_index = 0 # We are at the start of the new path
            
            if current_step_index != -1 and current_step_index + 1 < len(self.current_path):
                next_pos = self.current_path[current_step_index + 1]
                return get_move_from_path(self.my_pos, [self.my_pos, next_pos])

        return self._get_random_safe_move()

    # --- Internal KB Helper Functions ---

    def _add_safe_tile(self, pos: Coord):
        """Adds a tile as safe and updates unknown/junction status."""
        if pos in self.safe_tiles:
            return # Already processed
            
        self.safe_tiles.add(pos)
        self.unknown_tiles.discard(pos)
        self.walls.discard(pos) # In case it was inferred wrong
        
        # Add neighbors to 'unknown'
        for neighbor in get_neighbors(pos):
            if neighbor not in self.safe_tiles and neighbor not in self.walls:
                self.unknown_tiles.add(neighbor)

        # Check for junction
        self._check_for_junction(pos)
        # Re-check neighbors too, as this tile might complete them
        for neighbor in get_neighbors(pos):
            if neighbor in self.safe_tiles:
                self._check_for_junction(neighbor)

    def _check_for_junction(self, pos: Coord):
        """Infers if a tile is a junction (3+ safe, non-wall neighbors)."""
        if pos not in self.safe_tiles:
            return

        safe_neighbors = 0
        for neighbor in get_neighbors(pos):
            # A neighbor is "safe" if it's in our safe_tiles set
            # OR if it's in our current percepts and not a wall
            if neighbor in self.safe_tiles:
                safe_neighbors += 1
            elif neighbor in self.percepts and self.percepts[neighbor] != "WALL":
                safe_neighbors += 1
        
        if safe_neighbors >= 3:
            self.junctions.add(pos)
    
    def _get_random_safe_move(self) -> str:
        """Failsafe for when pathfinding fails or no goal exists."""
        possible_moves = []
        for move, (dx, dy) in MOVES.items():
            if move == 'WAIT': continue
            check_pos = (self.my_pos[0] + dx, self.my_pos[1] + dy)
            if check_pos in self.safe_tiles and check_pos not in self.walls:
                possible_moves.append(move)
        
        if possible_moves:
            return random.choice(possible_moves)
        return 'WAIT'