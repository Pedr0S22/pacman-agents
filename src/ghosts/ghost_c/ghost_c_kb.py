from typing import Tuple, List, Optional, Set, Dict
from utils.types_utils import Coord, Percept, MOVES
from utils.path_utils import get_neighbors, bfs_pathfinder, get_move_from_path, find_nearest_coord
from utils.fol_components import Predicate, Constant, Variable, unify
from ghosts.KB import KnowledgeBase
from .predicates import *
import random

class KnowledgeBaseC(KnowledgeBase):
    """
    KB for Ghost C: The Coordinator.
    Logic: Model-Based Utility Agent using First-Order Logic (FOL).
    
    FOL Rules Applied:
    1. ∀x,y: Percept(x,y)=WALL → LearnedWall(x,y)
    2. ∀x,y: Percept(x,y)≠WALL → LearnedSafe(x,y)
    3. ∀x,y: GhostPos(C,x,y) → LearnedSafe(x,y)
    4. ∀g,x,y: GhostPos(g,x,y) ∧ Distance(C,g)<4 → Repulse(x,y)
    5. ∀x,y: PacmanPos(x,y) ∧ PacmanVector(dx,dy) → Goal(x+3dx, y+3dy)
    6. ∀x,y: UnreachableGoal(x,y) → ¬Goal(x,y)
    """
    def __init__(self):
        # FOL Knowledge Base: Set of ground predicates
        self.facts: Set[Predicate] = set()
        
        # FOL Variables for queries
        self.X = Variable("X")
        self.Y = Variable("Y")
        self.ID = Variable("ID")
        self.DX = Variable("DX")
        self.DY = Variable("DY")
        self.Count = Variable("Count")
        self.T = Variable("T")
        
        # Internal state (derived from FOL queries, not part of KB)
        self.my_pos: Coord = (24, 8)
        self.goal: Optional[Coord] = None
        self.current_path: List[Coord] = []
        
        # Tracking for vector calculation (operational, not FOL)
        self.last_pacman_pos: Optional[Coord] = None
        self.last_pacman_vector: Tuple[int, int] = (0, 0)

        self.current_time: int = 0

    def tell(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ):
        """
        Update KB with new percepts using FOL assertions.
        
        FOL Process:
        1. Retract dynamic beliefs (GhostPos, PacmanPos, LastPos)
        2. Learn map topology from percepts
        3. Assert new dynamic beliefs
        4. Compute and assert PacmanVector
        """
        self.current_time += 1
        self.my_pos = my_pos

        # --- FOL TEMPORAL UPDATES ---

        # 1. Manage History (Keep last 10 steps)
        # Rule: ∀x,y,t: VisitedAtTime(x,y,t) ∧ (CurrentTime - t > 10) → Retract
        self._retract_old_history(keep_last_n=10)

        # 2. Assert current position in history
        # Assert: VisitedAtTime(my_pos.x, my_pos.y, current_time)
        self._assert_fact(VisitedAtTime(
            Constant(my_pos[0]), 
            Constant(my_pos[1]), 
            Constant(self.current_time)
        ))

        # 3. Clean up old unreachable goals
        self._retract_old_unreachable_goals(age_threshold=7)
        
        # FOL Rule: Store last position to prevent backtracking
        # Retract: ∀x,y: LastPos(C,x,y) → Retract
        self._retract(LastPos(Constant('C'), self.X, self.Y))
        # Assert: LastPos(C, my_pos.x, my_pos.y)
        self._assert_fact(LastPos(Constant('C'), Constant(my_pos[0]), Constant(my_pos[1])))

        # FOL Rule 1 & 2: Map Learning
        # ∀x,y: Percept(x,y)=WALL → LearnedWall(x,y)
        # ∀x,y: Percept(x,y)≠WALL → LearnedSafe(x,y)
        self._learn_map_topology(my_pos, percepts)

        # Retract dynamic beliefs before re-asserting
        self._retract_dynamic_beliefs()

        # FOL Rule 3: Assert current positions
        # Assert: GhostPos(C, my_pos.x, my_pos.y)
        self._assert_fact(GhostPos(Constant('C'), Constant(my_pos[0]), Constant(my_pos[1])))
        
        # Assert: ∀g ∈ other_ghosts: GhostPos(g.id, g.x, g.y)
        for ghost_id, ghost_pos in other_ghost_pos:
            self._assert_fact(GhostPos(
                Constant(ghost_id), 
                Constant(ghost_pos[0]), 
                Constant(ghost_pos[1])
            ))
        
        # FOL: Assert PacmanPos if visible
        if pacman_pos:
            self._assert_fact(PacmanPos(Constant(pacman_pos[0]), Constant(pacman_pos[1])))
            
            # Compute PacmanVector (operational calculation for FOL assertion)
            if self.last_pacman_pos:
                vx = pacman_pos[0] - self.last_pacman_pos[0]
                vy = pacman_pos[1] - self.last_pacman_pos[1]
                if vx != 0 or vy != 0:
                    self.last_pacman_vector = (vx, vy)
            
            self.last_pacman_pos = pacman_pos
            
            # Assert: PacmanVector(dx, dy)
            self._assert_fact(PacmanVector(
                Constant(self.last_pacman_vector[0]), 
                Constant(self.last_pacman_vector[1])
            ))

    def ask(self) -> str:
        """
        Infer best action using FOL queries and utility-based reasoning.
        
        FOL Decision Hierarchy:
        1. IMMEDIATE DANGER: ∃g: GhostPos(g,x,y) ∧ g≠C ∧ Distance(C,g)≤4 → Repulse away
        2. CLOSE CHASE: PacmanPos(x,y) ∧ Distance(C,P)≤2 → Chase directly
        3. MEDIUM INTERCEPT: PacmanPos(x,y) ∧ 3≤Distance(C,P)≤4 → Intercept with vector
        4. EXPLORATION: Explore frontier or spread
        """
        
        print(f"[DEBUG] Pos={self.my_pos} Goal={self.goal}")
        print(f"        Path: {[f'{i}:{p}' for i,p in enumerate(self.current_path)]}")

        new_goal = None

        # === PRIORITY 0: CONTINUE ESCAPE ===
        # FOL Query: Are we currently locked in an EscapeState?
        # Rule: EscapeState(gx, gy, t) ∧ (CurrentTime - t < 20) ∧ Dist(Me, Goal) > 0
        escape_target = self._query_active_escape(duration=20)
        
        if escape_target:
            if escape_target == self.my_pos:
                # We reached the safe haven! Clear the state.
                print(f"[ESCAPE] Reached safety at {escape_target}. Resuming normal logic.")
                self._retract_escape_state()
            else:
                # Keep running to the escape target
                new_goal = escape_target
                print(f"[PRIORITY 0] ESCAPING OSCILLATION -> {new_goal}")

        # === PRIORITY 0.5: DETECT NEW OSCILLATION ===
        if new_goal is None and self._infer_oscillation():
            # We are stuck. Calculate a FAR target.
            far_goal = self._find_farthest_safe_tile()
            
            if far_goal:
                print(f"[LOGIC] OSCILLATION DETECTED. Initiating Long-Range Escape to {far_goal}")
                
                # Assert the new state into KB
                self._assert_fact(EscapeState(
                    Constant(far_goal[0]),
                    Constant(far_goal[1]),
                    Constant(self.current_time)
                ))
                
                new_goal = far_goal
            else:
                # Fallback if no map known yet
                return self._get_safe_fallback_move()

        # === PRIORITY 1: REPULSION FROM NEARBY GHOSTS (distance ≤ 4) ===
        # FOL Query: ∃g,gx,gy: GhostPos(g,gx,gy) ∧ g≠C ∧ Distance(C,(gx,gy))≤4
        # Can only see ghosts within 4 tiles
        nearby_ghosts = self._query_nearby_ghosts(repulsion_distance=5)  # 5 to include distance 4
        if nearby_ghosts:
            # FOL Inference: Flee away from visible ghosts
            new_goal = self._infer_repulsion_goal(nearby_ghosts)
            print(f"[PRIORITY 1] REPULSION from ghosts at {nearby_ghosts}")

        # === PRIORITY 2: CLOSE CHASE (distance ≤ 2) ===
        # FOL Query: PacmanPos(px,py) ∧ Distance(C,P)≤2
        # Pacman is very close - chase directly!
        if new_goal is None:
            pacman_info = self._query_pacman_state()
            if pacman_info:
                px, py, vx, vy = pacman_info
                distance_to_pacman = abs(self.my_pos[0] - px) + abs(self.my_pos[1] - py)
                
                # Only act on Pacman if we can see him (distance ≤ 4)
                if distance_to_pacman <= 4:
                    if distance_to_pacman <= 2:
                        # Chase directly - Pacman is very close!
                        chase_goal = (px, py)
                        if chase_goal and not self._is_unreachable_goal(chase_goal):
                            new_goal = chase_goal
                            print(f"[PRIORITY 2] CHASE Pacman at {(px, py)}, distance={distance_to_pacman}")

        # === PRIORITY 3: INTERCEPT (3 ≤ distance ≤ 4) ===
        # FOL Query: PacmanPos(px,py) ∧ 3≤Distance(C,P)≤4 ∧ PacmanVector(vx,vy)
        # Pacman is visible but not too close - intercept his path
        if new_goal is None:
            pacman_info = self._query_pacman_state()
            if pacman_info:
                px, py, vx, vy = pacman_info
                distance_to_pacman = abs(self.my_pos[0] - px) + abs(self.my_pos[1] - py)
                
                # Only if Pacman is visible and at medium distance
                if 3 <= distance_to_pacman <= 4:
                    # Predict where Pacman will be and intercept
                    # Since we can only see 4 tiles, predict 2 steps ahead
                    target_x = px + (vx * 2)
                    target_y = py + (vy * 2)
                    intercept_goal = self._find_nearest_safe_to_target((target_x, target_y))
                    
                    if intercept_goal and not self._is_unreachable_goal(intercept_goal):
                        new_goal = intercept_goal
                        print(f"[PRIORITY 3] INTERCEPT Pacman, distance={distance_to_pacman}, vector=({vx},{vy})")

        # === PRIORITY 4: VECTOR-ALIGNED EXPLORATION ===
        # Only use last known vector if we recently saw Pacman
        if new_goal is None:
            vector_info = self._query_vector()
            if vector_info and vector_info != (0, 0):
                aligned_goal = self._find_vector_aligned_frontier(vector_info)
                if aligned_goal and not self._is_unreachable_goal(aligned_goal):
                    new_goal = aligned_goal
                    print(f"[PRIORITY 4] VECTOR-ALIGNED EXPLORATION with vector {vector_info}")

        # === PRIORITY 5: FRONTIER EXPLORATION ===
        if new_goal is None:
            frontier_goal = self._find_nearest_frontier_goal()
            if frontier_goal and not self._is_unreachable_goal(frontier_goal):
                new_goal = frontier_goal
                print(f"[PRIORITY 5] FRONTIER EXPLORATION")

        # === PRIORITY 6: SPREAD (DEFAULT) ===
        if new_goal is None:
            spread_goal = self._find_spread_goal()
            if spread_goal and not self._is_unreachable_goal(spread_goal):
                new_goal = spread_goal
                print(f"[PRIORITY 6] SPREAD")

        # === PATHFINDING & EXECUTION ===
        if new_goal:
            need_replan = (new_goal != self.goal) or self._is_path_obstructed()
            
            if need_replan:
                self.goal = new_goal
                safe_coords = self._query_all_safe_coords()
                
                safe_coords.add(self.goal)
                # BFS pathfinding on safe coordinate set
                new_path = bfs_pathfinder(self.my_pos, self.goal, safe_coords)
                
                if not new_path:
                    self._assert_fact(UnreachableGoal(
                        Constant(self.goal[0]),
                        Constant(self.goal[1]),
                        Constant(self.current_time)
                    ))
                    
                    fallback = self._find_nearest_frontier_goal() or self._find_spread_goal()
                    if fallback:
                        self.goal = fallback
                        new_path = bfs_pathfinder(self.my_pos, self.goal, safe_coords) or []
                    else:
                        new_path = []
                        
                elif len(new_path) == 1 and new_path[0] != self.my_pos:
                    self._assert_fact(UnreachableGoal(
                        Constant(self.goal[0]),
                        Constant(self.goal[1]),
                        Constant(self.current_time)
                    ))
                
                self.current_path = new_path

        # === EXECUTE NEXT MOVE ===
        if self.current_path:
            # CRITICAL: Validate path includes current position
            if self.my_pos not in self.current_path:
                print(f"[ERROR] Path invalid! my_pos={self.my_pos} not in path={self.current_path}")
                self.current_path = []
                self.goal = None 
                return self._get_safe_fallback_move()
            
            idx = self.current_path.index(self.my_pos)
            
            if idx + 1 < len(self.current_path):
                next_pos = self.current_path[idx + 1]
                
                # [FIX] Allow move if the position is known safe OR if it is our specific goal
                # We must take the risk to step into the goal to learn what it is.
                is_safe = self._is_position_safe(next_pos)
                is_target_goal = (next_pos == self.goal)

                if is_safe or is_target_goal:
                    dist = abs(next_pos[0] - self.my_pos[0]) + abs(next_pos[1] - self.my_pos[1])
                    if dist == 1:
                        move = get_move_from_path(self.my_pos, [self.my_pos, next_pos])
                        return move
                    else:
                        print(f"[ERROR] Next pos not adjacent! dist={dist}")
                        self.current_path = []
                        self.goal = None
                        return self._get_safe_fallback_move()
                else:
                    # Next position is unsafe and NOT our goal - Abort
                    print(f"[BLOCKED] Next pos {next_pos} is unsafe and not goal.")
                    self.current_path = []
                    self.goal = None
                    return self._get_safe_fallback_move()

            else:
                # At goal
                self.current_path = []
                self.goal = None
        
        return self._get_safe_fallback_move()

    # ========================================================================
    # FOL MAP LEARNING
    # ========================================================================

    def _learn_map_topology(self, my_pos: Coord, percepts: Percept):
        """
        FOL Rules:
        - ∀x,y: GhostPos(C,x,y) → LearnedSafe(x,y)
        - ∀x,y: Percept(x,y)=WALL → LearnedWall(x,y)
        - ∀x,y: Percept(x,y)≠WALL → LearnedSafe(x,y)
        """
        # Rule: Current position is always safe
        cx, cy = Constant(my_pos[0]), Constant(my_pos[1])
        if not self._query_exists(LearnedSafe(cx, cy)):
            self._assert_fact(LearnedSafe(cx, cy))
        
        # Rule: Process all percepts
        for pos, item in percepts.items():
            px, py = Constant(pos[0]), Constant(pos[1])
            
            if item == "WALL":
                # Assert: LearnedWall(px, py)
                if not self._query_exists(LearnedWall(px, py)):
                    self._assert_fact(LearnedWall(px, py))
                    # Retract conflicting safe assertion
                    self._retract(LearnedSafe(px, py))
            else:
                # Assert: LearnedSafe(px, py)
                if not self._query_exists(LearnedSafe(px, py)):
                    self._assert_fact(LearnedSafe(px, py))

    # ========================================================================
    # FOL QUERY METHODS
    # ========================================================================

    def _query_nearby_ghosts(self, repulsion_distance: int) -> List[Coord]:
        """
        FOL Query: ∃g,gx,gy: GhostPos(g,gx,gy) ∧ g≠C ∧ ManhattanDist(C,(gx,gy)) < repulsion_distance
        Returns: List of (gx, gy) coordinates
        """
        nearby = []
        # Query: GhostPos(ID, X, Y)
        ghost_positions = self.get_unifications(GhostPos(self.ID, self.X, self.Y))
        
        for result in ghost_positions:
            ghost_id = result[self.ID].value
            gx = result[self.X].value
            gy = result[self.Y].value
            
            # Filter: g ≠ C
            if ghost_id != 'C':
                distance = abs(self.my_pos[0] - gx) + abs(self.my_pos[1] - gy)
                if distance < repulsion_distance:
                    nearby.append((gx, gy))
        
        return nearby

    def _query_pacman_state(self) -> Optional[Tuple[int, int, int, int]]:
        """
        FOL Query: PacmanPos(px,py) ∧ PacmanVector(vx,vy)
        Returns: (px, py, vx, vy) or None
        """
        # Query: PacmanPos(X, Y)
        pacman_positions = self.get_unifications(PacmanPos(self.X, self.Y))
        if not pacman_positions:
            return None
        
        px = pacman_positions[0][self.X].value
        py = pacman_positions[0][self.Y].value
        
        # Query: PacmanVector(DX, DY)
        vector_results = self.get_unifications(PacmanVector(self.DX, self.DY))
        if vector_results:
            vx = vector_results[0][self.DX].value
            vy = vector_results[0][self.DY].value
        else:
            vx, vy = 0, 0
        
        return (px, py, vx, vy)

    def _query_vector(self) -> Optional[Tuple[int, int]]:
        """
        FOL Query: PacmanVector(vx,vy)
        Returns: (vx, vy) or None
        """
        vector_results = self.get_unifications(PacmanVector(self.DX, self.DY))
        if vector_results:
            return (vector_results[0][self.DX].value, vector_results[0][self.DY].value)
        return None

    def _query_all_safe_coords(self) -> Set[Coord]:
        """
        FOL Query: {(x,y) | LearnedSafe(x,y)}
        Returns: Set of all safe coordinates
        """
        results = self.get_unifications(LearnedSafe(self.X, self.Y))
        return {(res[self.X].value, res[self.Y].value) for res in results}


    def _is_unreachable_goal(self, goal: Coord) -> bool:
        """
        FOL Query: ∃t: UnreachableGoal(goal.x, goal.y, t)
        """
        T = Variable("T")
        results = self.get_unifications(UnreachableGoal(
            Constant(goal[0]),
            Constant(goal[1]),
            T
        ))
        return len(results) > 0

    def _is_position_safe(self, pos: Coord) -> bool:
        """
        FOL Query: LearnedSafe(pos.x, pos.y)
        Returns: True if position is safe
        """
        return self._query_exists(LearnedSafe(Constant(pos[0]), Constant(pos[1])))

    def _is_path_obstructed(self) -> bool:
        """
        FOL Check: Path is obstructed if:
        1. No path exists: ¬∃path
        2. Path exists but we're NOT at goal and path is too short
        3. Any tile in path is unsafe: ∃(x,y)∈path: ¬LearnedSafe(x,y)
        """
        if not self.current_path:
            return True
        
        # If path length is 1 and we're at that position, we're AT the goal (not obstructed)
        if len(self.current_path) == 1:
            if self.current_path[0] == self.my_pos:
                return False  # We reached the goal!
            else:
                return True  # Path doesn't include our position (invalid)
        
        # FOL Check: ∃(x,y)∈path: ¬LearnedSafe(x,y)
        for tile in self.current_path:
            if not self._is_position_safe(tile):
                return True
        
        return False

    # ========================================================================
    # FOL INFERENCE METHODS (Goal Selection)
    # ========================================================================

    def _infer_repulsion_goal(self, threatening_ghosts: List[Coord]) -> Optional[Coord]:
        """
        FOL Inference: Find safe tile maximizing distance from visible threatening ghosts.
        
        Since we can only see 4 tiles in each direction, threatening ghosts are always
        within vision range (distance ≤ 4). We want to move AWAY from them.
        
        Strategy: Find the direction opposite to the average ghost position and move there.
        """
        safe_tiles = self._query_all_safe_coords()
        
        # Calculate centroid of all threatening ghosts
        avg_threat_x = sum(gx for gx, gy in threatening_ghosts) / len(threatening_ghosts)
        avg_threat_y = sum(gy for gx, gy in threatening_ghosts) / len(threatening_ghosts)
        
        # Vector pointing AWAY from threats
        escape_dx = self.my_pos[0] - avg_threat_x
        escape_dy = self.my_pos[1] - avg_threat_y
        
        # Normalize escape vector (get direction)
        escape_magnitude = max(abs(escape_dx), abs(escape_dy), 1)  # Avoid division by zero
        escape_dx = escape_dx / escape_magnitude
        escape_dy = escape_dy / escape_magnitude
        
        best_goal = None
        best_score = -float('inf')
        
        for tx, ty in safe_tiles:
            # Only consider tiles within reasonable distance
            dist_from_me = abs(tx - self.my_pos[0]) + abs(ty - self.my_pos[1])
            if dist_from_me > 6 or dist_from_me == 0:  # Not too far, not current position
                continue
            
            # Direction from current position to candidate tile
            dx = tx - self.my_pos[0]
            dy = ty - self.my_pos[1]
            
            # How well aligned is this tile with escape direction? (dot product)
            alignment = (dx * escape_dx) + (dy * escape_dy)
            
            # Minimum distance to any threat (the closer the threat, the worse)
            min_threat_dist = min(
                abs(tx - gx) + abs(ty - gy) 
                for gx, gy in threatening_ghosts
            )
            
            # Score combines:
            # - Alignment with escape direction (heavily weighted)
            # - Distance from nearest threat
            score = alignment * 3 + min_threat_dist
            
            if score > best_score:
                best_score = score
                best_goal = (tx, ty)
        
        return best_goal if best_goal else self.my_pos

    def _find_nearest_frontier_goal(self) -> Optional[Coord]:
        """
        FOL Query: Find nearest safe tile adjacent to frontier.
        
        Instead of returning the frontier tile itself (which is unknown),
        return the safe tile that's adjacent to it.
        """
        frontier = self._compute_frontier()
        frontier = {f for f in frontier if not self._is_unreachable_goal(f)}
        
        if not frontier:
            return None
        
        safe_coords = self._query_all_safe_coords()
        
        # Find the nearest frontier tile
        nearest_frontier = find_nearest_coord(self.my_pos, frontier, safe_coords)
        if not nearest_frontier:
            return None
        
        dist = abs(self.my_pos[0] - nearest_frontier[0]) + abs(self.my_pos[1] - nearest_frontier[1])
        if dist == 1:
            return nearest_frontier
        
        # ✅ FIX: Return a SAFE tile adjacent to the frontier, not the frontier itself
        # Find which safe tile is adjacent to this frontier
        for neighbor in get_neighbors(nearest_frontier):
            if neighbor in safe_coords:
                # This is a safe tile adjacent to the frontier
                # Path to THIS instead of the frontier
                return neighbor
        
        print("SHIT HAPPEN: _FIND_NEAREST_FRONTIER: NONE")
        return None  # No safe tile adjacent to frontier (shouldn't happen)

    def _find_vector_aligned_frontier(self, vector: Tuple[int, int]) -> Optional[Coord]:
        """
        FOL Query: Find frontier tile (fx,fy) where:
        - ∃sx,sy: LearnedSafe(sx,sy) ∧ Neighbor(sx,sy,fx,fy)
        - ¬LearnedWall(fx,fy) ∧ ¬LearnedSafe(fx,fy)
        - DotProduct((fx-Cx,fy-Cy), vector) > 0
        """
        frontier = self._compute_frontier()
        if not frontier:
            return None
        
        vx, vy = vector
        best_frontier = None
        min_distance = float('inf')
        
        for fx, fy in frontier:
            # Compute direction from my_pos to frontier
            dx = fx - self.my_pos[0]
            dy = fy - self.my_pos[1]
            
            # Dot product: alignment check
            dot = (dx * vx) + (dy * vy)
            
            if dot > 0:  # Aligned with vector
                dist = abs(dx) + abs(dy)
                if dist < min_distance:
                    min_distance = dist
                    best_frontier = (fx, fy)
        
            if not best_frontier:
                return None
                
            # [FIX 3] If adjacent, target the frontier directly
            dist = abs(self.my_pos[0] - best_frontier[0]) + abs(self.my_pos[1] - best_frontier[1])
            if dist == 1:
                return best_frontier

            # ✅ FIX: Return safe tile adjacent to frontier
            safe_coords = self._query_all_safe_coords()
            for neighbor in get_neighbors(best_frontier):
                if neighbor in safe_coords:
                    return neighbor
            
            return None

    def _find_spread_goal(self) -> Optional[Coord]:
        """
        FOL Query: Find (sx,sy) where LearnedSafe(sx,sy) ∧ dist(C,(sx,sy)) > 10
        """
        safe_tiles = self._query_all_safe_coords()
        
        for tile in safe_tiles:
            distance = abs(tile[0] - self.my_pos[0]) + abs(tile[1] - self.my_pos[1])
            if distance > 10:
                return tile
        
        return None

    def _compute_frontier(self) -> Set[Coord]:
        """
        FOL Inference: Compute frontier tiles
        Frontier(fx,fy) ≡ ∃sx,sy: LearnedSafe(sx,sy) ∧ Neighbor(sx,sy,fx,fy) 
                          ∧ ¬LearnedSafe(fx,fy) ∧ ¬LearnedWall(fx,fy)
        """
        safe_tiles = self._query_all_safe_coords()
        frontier = set()
        
        for sx, sy in safe_tiles:
            for neighbor in get_neighbors((sx, sy)):
                nx, ny = neighbor
                # Check: ¬LearnedSafe(nx,ny) ∧ ¬LearnedWall(nx,ny)
                is_safe = self._query_exists(LearnedSafe(Constant(nx), Constant(ny)))
                is_wall = self._query_exists(LearnedWall(Constant(nx), Constant(ny)))
                
                if not is_safe and not is_wall:
                    frontier.add(neighbor)
        
        return frontier

    # ========================================================================
    # FOL KB MANAGEMENT
    # ========================================================================

    def _assert_fact(self, fact: Predicate):
        """Assert a ground fact into the knowledge base."""
        if fact.is_ground():
            self.facts.add(fact)

    def _retract_old_unreachable_goals(self, age_threshold: int):
        """
        FOL Rule: Clean up old unreachable goals
        ∀x,y,t: UnreachableGoal(x,y,t) ∧ (current_time - t > threshold) → Retract(UnreachableGoal(x,y,t))
        """
        T = Variable("T")
        unreachable_facts = self.get_unifications(UnreachableGoal(self.X, self.Y, T))
        
        to_retract = []
        for result in unreachable_facts:
            timestamp = result[T].value
            age = self.current_time - timestamp
            
            if age > age_threshold:
                x_val = result[self.X].value
                y_val = result[self.Y].value
                to_retract.append(UnreachableGoal(
                    Constant(x_val),
                    Constant(y_val),
                    Constant(timestamp)
                ))
        
        for fact in to_retract:
            self.facts.discard(fact)

    def _retract_dynamic_beliefs(self):
        """
        Retract all dynamic beliefs before reasserting:
        - GhostPos(*, *, *)
        - PacmanPos(*, *)
        - PacmanVector(*, *)
        """
        self._retract(GhostPos(self.ID, self.X, self.Y))
        self._retract(PacmanPos(self.X, self.Y))
        self._retract(PacmanVector(self.DX, self.DY))

    def _retract(self, query_template: Predicate):
        """Retract all facts matching the query template."""
        to_remove = set()
        for fact in self.facts:
            if unify(query_template, fact) is not None:
                to_remove.add(fact)
        self.facts.difference_update(to_remove)


    def get_unifications(self, query: Predicate) -> List[Dict[Variable, Constant]]:
        """
        Find all facts that unify with the query.
        Returns list of substitutions.
        """
        results = []
        for fact in self.facts:
            if type(fact) == type(query):
                substitution = unify(query, fact)
                if substitution is not None:
                    results.append(substitution)
        return results

    def _query_exists(self, query: Predicate) -> bool:
        """Check if query unifies with any fact in KB."""
        return len(self.get_unifications(query)) > 0

    def _get_safe_fallback_move(self) -> str:
        """
        FOL Query: Find random safe move
        Query: ∃x,y: Neighbor(C,x,y) ∧ LearnedSafe(x,y)
        """
        safe_moves = []
        
        for move_name, (dx, dy) in MOVES.items():
            if move_name == 'WAIT':
                continue
            
            nx = self.my_pos[0] + dx
            ny = self.my_pos[1] + dy
            
            # FOL Check: LearnedSafe(nx, ny)
            if self._is_position_safe((nx, ny)):
                safe_moves.append(move_name)
        
        return random.choice(safe_moves) if safe_moves else 'WAIT'
    
    def _find_farthest_safe_tile(self) -> Optional[Coord]:
        """
        Find the LearnedSafe tile with the maximum Manhattan distance from my_pos.
        """
        safe_tiles = self._query_all_safe_coords()
        if not safe_tiles:
            return None
            
        best_tile = None
        max_dist = -1
        
        for tx, ty in safe_tiles:
            dist = abs(tx - self.my_pos[0]) + abs(ty - self.my_pos[1])
            # Ensure we don't pick a goal we are already at
            if dist > max_dist:
                max_dist = dist
                best_tile = (tx, ty)
                
        return best_tile

    def _query_active_escape(self, duration: int) -> Optional[Coord]:
        """
        FOL Query: EscapeState(X, Y, T)
        Returns (X,Y) if state exists and is not expired.
        Retracts state if expired.
        """
        T_var = Variable("T")
        X_var = Variable("X")
        Y_var = Variable("Y")
        
        results = self.get_unifications(EscapeState(X_var, Y_var, T_var))
        
        if results:
            # Get the most recent escape state
            res = results[0]
            start_time = res[T_var].value
            gx = res[X_var].value
            gy = res[Y_var].value
            
            # Check expiration
            if self.current_time - start_time > duration:
                # Expired
                self._retract(EscapeState(X_var, Y_var, T_var))
                return None
            
            return (gx, gy)
            
        return None

    def _retract_escape_state(self):
        """Retract all EscapeState facts."""
        self._retract(EscapeState(self.X, self.Y, self.T))

    def _retract_old_history(self, keep_last_n: int):
        """Retracts VisitedAtTime facts older than N steps."""
        T = Variable("T")
        history_facts = self.get_unifications(VisitedAtTime(self.X, self.Y, T))
        
        to_retract = []
        for result in history_facts:
            if self.current_time - result[T].value > keep_last_n:
                to_retract.append(VisitedAtTime(result[self.X], result[self.Y], result[T]))
        
        for fact in to_retract:
            self.facts.discard(fact)

    def _infer_oscillation(self) -> bool:
        """
        Check history for A-B-A-B-A pattern.
        Checks time t, t-2, t-4.
        """
        x, y = self.my_pos
        t = self.current_time
        
        # We need to have visited THIS exact tile 2 and 4 ticks ago
        was_here_t2 = self._query_exists(VisitedAtTime(Constant(x), Constant(y), Constant(t - 2)))
        was_here_t4 = self._query_exists(VisitedAtTime(Constant(x), Constant(y), Constant(t - 4)))
        
        return was_here_t2 and was_here_t4
    
    def _find_nearest_safe_to_target(self, target: Coord) -> Optional[Coord]:
        """
        Helper: Find the safe tile closest to a specific target coordinate.
        """
        safe_coords = self._query_all_safe_coords()
        if not safe_coords:
            return None
            
        # Use the imported utility function
        return find_nearest_coord(target, safe_coords, safe_coords)