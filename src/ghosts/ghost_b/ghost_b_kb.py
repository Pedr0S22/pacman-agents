from typing import Set, List, Optional, Dict, Tuple, Deque
from collections import deque
from utils.types_utils import Coord, Percept, MOVES
from utils.path_utils import bfs_pathfinder, get_move_from_path, get_neighbors, find_nearest_coord
from ghosts.KB import KnowledgeBase
import random

class KnowledgeBaseB(KnowledgeBase):
    """
    KB for Ghost B (The Analyst).
    Logic: Optimistic Model-Based Agent.
    FIX: Uses a 'Planning Mesh' (Safe + Unknown) to allow the pathfinder 
    to route through the fog of war.
    Now tracks the last 8 visited junctions to avoid repetitive patrolling.
    """
    def __init__(self):
        # --- World Model ---
        self.walls: Set[Coord] = set()
        self.safe_tiles: Set[Coord] = set()
        self.unknown_tiles: Set[Coord] = set()
        self.junctions: Set[Coord] = set()
        self.believed_pellets: Set[Coord] = set()

        self.initialized = False
        
        # --- Beliefs ---
        self.my_pos: Optional[Coord] = None
        self.pacman_visible: bool = False
        self.pacman_last_pos: Optional[Coord] = None
        self.percepts: Percept = {} 
        
        # --- Memory & Plan ---
        self.clues: List[Tuple[Coord, int]] = [] 
        self.goal: Optional[Coord] = None
        self.current_path: List[Coord] = []
        
        # Junction Memory (Last 8 visited)
        # "CREATE A DATA STRUCTURE THAT SAVES LAST 12 JUNCTIONS"
        self.visited_junctions: Deque[Coord] = deque(maxlen=12)
        
        # --- Camping Logic ---
        self.is_loitering: bool = False
        self.loiter_timer: int = 0
        self.loiter_anchor: Optional[Coord] = None
        self.MAX_LOITER_TIME: int = 4 

    def tell(self, my_pos: Coord, pacman_pos: Optional[Coord], other_ghost_pos: List[Tuple[str, Coord]], percepts: Percept):
        self.my_pos = my_pos
        self.percepts = percepts 
        
        # FIRST TURN FIX — Pre-seed map knowledge BEFORE any decision logic runs
        if not self.initialized:
            self._mark_safe(my_pos)     # Mark current tile safe
            for n in get_neighbors(my_pos):  # Pre-seed unknown frontier
                if n not in self.walls:
                    self.unknown_tiles.add(n)
            self.initialized = True
        else:
            # Normal marking on subsequent turns
            self._mark_safe(my_pos)

        new_clue_pos = None
        for pos, item in percepts.items():
            if item == "WALL":
                self.walls.add(pos)
                self.safe_tiles.discard(pos)
                self.unknown_tiles.discard(pos) # Wall is no longer unknown
                self.junctions.discard(pos)
            else:
                self._mark_safe(pos) # Visible tiles are safe
                if item == "PELLET":
                    self.believed_pellets.add(pos)
                elif item == "EMPTY":
                    if pos in self.believed_pellets:
                        new_clue_pos = pos
                        self.believed_pellets.discard(pos)

        # 2. Update Clues
        alive_clues = []
        for c_pos, c_age in self.clues:
            if c_pos == self.my_pos: continue 
            if self.pacman_visible: continue
            if c_age < 25: alive_clues.append((c_pos, c_age + 1))
        self.clues = alive_clues

        # 3. Update Pacman Interaction
        if pacman_pos:
            self.pacman_visible = True
            self.pacman_last_pos = pacman_pos
            self.clues = [] 
            self.is_loitering = False
            self.goal = None # Reset goal to chase immediately
        else:
            self.pacman_visible = False
            if new_clue_pos:
                self.clues.insert(0, (new_clue_pos, 0))
                if len(self.clues) > 2: self.clues.pop()

    def ask(self) -> str:
        if self.my_pos is None: return 'WAIT'

        # --- CRITICAL FIX: THE PLANNING MESH ---
        # We combine Safe + Unknown. We treat "Unknown" as "Walkable until proven otherwise".
        # This allows BFS to find paths through the fog.
        planning_mesh = self.safe_tiles.union(self.unknown_tiles)
        # Ensure my current position is strictly in the mesh to avoid start-node errors
        planning_mesh.add(self.my_pos)

        # === DEBUG: PRINT MESH + GOAL ===
        #print("---- GHOST B DEBUG ----")
        #print("Pos:", self.my_pos)
        #print("Safe:", len(self.safe_tiles))
        #print("Junctions:", len(self.junctions))
        #print("Visited Q:", list(self.visited_junctions))
        #print("Goal:", self.goal)
        #print("-------------------------")

        # Defensive: if our current goal turned out to be a wall, drop it now.
        if self.goal is not None and self.goal in self.walls:
            #print(f"[GHOST B] Dropping goal {self.goal} because it is now a known wall.")
            self.goal = None
            self.current_path = []

        # 1. LOITERING
        if self.is_loitering:
            self.loiter_timer -= 1
            if self.loiter_timer <= 0 or self.pacman_visible:
                self.is_loitering = False
                self.goal = None 
                self.current_path = []
            else:
                return self._execute_loiter_step(planning_mesh)

        # 2. ARRIVAL & CAMPING
        if self.goal and self.my_pos == self.goal:
            #print(f"[GHOST B] Reached goal {self.goal}.")
            
            if self.my_pos in self.junctions:
                # --- UPDATE QUEUE ---
                # Record visit to this junction
                if self.my_pos not in self.visited_junctions:
                    self.visited_junctions.append(self.my_pos)
                elif self.visited_junctions[-1] != self.my_pos:
                    # If it's in the list but not the most recent, bump it to the end
                    self.visited_junctions.remove(self.my_pos)
                    self.visited_junctions.append(self.my_pos)

                # Start Loitering
                self.is_loitering = True
                self.loiter_timer = self.MAX_LOITER_TIME
                self.loiter_anchor = self.my_pos
                
                # Clear goal/path BUT return WAIT to hold position
                self.goal = None 
                self.current_path = []
                return 'WAIT'
            else:
                # Reached non-junction goal (e.g. clue) -> just clear and continue
                self.goal = None 
                self.current_path = []

        # 3. GOAL SELECTION
        if self.goal is None:
            self.goal = self._select_new_goal(planning_mesh)
            self.current_path = [] # New goal requires new path

        # 4. PATHFINDING
        if self.goal:
            # If we lack a path or have drifted off it
            needs_path = not self.current_path
            if self.current_path:
                # Robustness: If next step isn't a neighbor, the path is broken
                if self.current_path[0] not in get_neighbors(self.my_pos) and self.current_path[0] != self.my_pos:
                    needs_path = True
            
            if needs_path:
                # Pass the OPTIMISTIC planning mesh to BFS
                path = bfs_pathfinder(self.my_pos, self.goal, planning_mesh)
                if path:
                    self.current_path = path
                    # BFS often returns [start, next, ..., goal]. Remove start if present.
                    if self.current_path and self.current_path[0] == self.my_pos:
                        self.current_path.pop(0)
                else:
                    self.goal = None # Goal unreachable even optimistically

        # 5. EXECUTION
        if self.current_path:
            next_step = self.current_path[0]
            
            # Double check: Is the next step actually a wall we just discovered?
            if next_step in self.walls:
                self.current_path = [] # Path blocked, replan next tick
                return 'WAIT'
                
            # Optimization: Pop the step so we don't loop
            if next_step == self.my_pos:
                self.current_path.pop(0)
                if self.current_path:
                    next_step = self.current_path[0]
                else:
                    return 'WAIT'

            return get_move_from_path(self.my_pos, [self.my_pos, next_step])

        # 6. FALLBACK
        return self._get_random_optimistic_move()

    # --- Helpers ---

    def _execute_loiter_step(self, mesh: Set[Coord]) -> str:
        if self.my_pos == self.loiter_anchor:
            neighbors = [n for n in get_neighbors(self.loiter_anchor) if n in mesh]
            if neighbors:
                step_out = random.choice(neighbors)
                return get_move_from_path(self.my_pos, [self.my_pos, step_out])
            return 'WAIT'
        return get_move_from_path(self.my_pos, [self.my_pos, self.loiter_anchor])

    def _select_new_goal(self, mesh: Set[Coord]) -> Optional[Coord]:
        """
        Selects a new goal for the ghost, prioritizing:
        1. Chase visible Pacman
        2. Follow clues
        3. Patrol far junctions (avoiding visited ones)
        4. Explore unknown frontier
        5. Patrol any nearby junction
        """

        # 1. CHASE
        if self.pacman_visible:
            return self.pacman_last_pos

        # 2. CLUES
        if self.clues:
            return self._select_best_clue()

        # helper
        def is_valid(c: Coord) -> bool:
            return c not in self.walls and c in mesh and c != self.my_pos

        # debug helper
        def inspect(name, coords):
            coords_list = list(coords)
            #print(f"[GHOST B] Inspect {name}: total={len(coords_list)} sample={coords_list[:10]}")

        inspect("unknown_tiles", self.unknown_tiles)
        
        # Create exclusion set from visited queue
        excluded = {self.my_pos}
        excluded.update(self.visited_junctions)

        # 3. FAR JUNCTIONS
        # Filter out junctions that are in the 'excluded' (recently visited) set
        far_juncs = [
            j for j in self.junctions
            if j not in excluded and (abs(j[0]-self.my_pos[0]) + abs(j[1]-self.my_pos[1])) > 5 and is_valid(j)
        ]
        if far_juncs:
            #print("[GHOST B] Choosing far junctions:", far_juncs[:5])
            return find_nearest_coord(self.my_pos, set(far_juncs), mesh)

        # 4. UNKNOWN FRONTIER
        unknowns = [u for u in self.unknown_tiles if is_valid(u)]
        if unknowns:
            #print("[GHOST B] Choosing unknown frontier sample:", unknowns[:5])
            return find_nearest_coord(self.my_pos, set(unknowns), mesh)

        # 5. ANY JUNCTION (Fallback if we are stuck locally or have visited everywhere)
        nearby_juncs = [j for j in self.junctions if j != self.my_pos and is_valid(j)]
        if nearby_juncs:
            #print("[GHOST B] Choosing nearby junctions (fallback):", nearby_juncs[:5])
            return find_nearest_coord(self.my_pos, set(nearby_juncs), mesh)

        return None

    def _select_best_clue(self) -> Optional[Coord]:
        best, min_score = None, 9999
        for c_pos, c_age in self.clues:
            score = (abs(c_pos[0] - self.my_pos[0]) + abs(c_pos[1] - self.my_pos[1])) + (c_age * 2)
            if score < min_score: min_score, best = score, c_pos
        return best

    def _mark_safe(self, pos: Coord):
        if pos in self.safe_tiles: return
        self.safe_tiles.add(pos)
        self.walls.discard(pos)
        self.unknown_tiles.discard(pos) # IMPORTANT: Remove from unknown once visited
        
        # Add neighbors to unknown if they are fresh
        for n in get_neighbors(pos):
            if n not in self.safe_tiles and n not in self.walls:
                self.unknown_tiles.add(n)
        
        self._infer_junction(pos)
        for n in get_neighbors(pos): 
            if n in self.safe_tiles: self._infer_junction(n)

    def _infer_junction(self, pos: Coord):
        if pos in self.walls: return
        count = 0
        for n in get_neighbors(pos):
            if n not in self.walls: count += 1 # Optimistic inference
        if count >= 3: self.junctions.add(pos)

    def _get_random_optimistic_move(self) -> str:
        possible = []
        for move, (dx, dy) in MOVES.items():
            if move == 'WAIT': continue
            nx, ny = self.my_pos[0]+dx, self.my_pos[1]+dy
            # Move is valid if it is NOT a known wall
            if (nx, ny) not in self.walls and (nx, ny) in self.safe_tiles.union(self.unknown_tiles):
                possible.append(move)

        return random.choice(possible) if possible else 'WAIT'