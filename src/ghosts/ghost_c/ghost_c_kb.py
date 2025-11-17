from typing import Tuple, Dict, Set, List, Optional
from utils.types_utils import Coord, Percept, MOVES
from utils.path_utils import bfs_pathfinder, get_move_from_path, find_nearest_coord, get_neighbors
from utils.fol_components import Predicate, Constant, Variable, unify
from predicates import *
import random
import math

class KnowledgeBaseC:
    """
    KB for Ghost C ("The Overlord").
    This is a formal FOL KB that follows the TELL/ASK model.
    TELL: Updates the fact database.
    ASK: Runs inference, pathfinding, and returns a final action.
    """
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        
        # A set of ground predicate "facts"
        self.facts: Set[Predicate] = set()

        # --- Stored Percepts ---
        self.my_pos: Coord = (0, 0) # My current position
        self.pacman_pos_percept: Optional[Coord] = None
        self.other_ghosts_percept: List[Tuple[str, Coord]] = []
        self.percepts: Percept = {}

        # --- Pathfinding State  ---
        self.goal: Optional[Coord] = None
        self.current_path: List[Coord] = []
        
        # --- Reusable Variables for Queries ---
        self.X = Variable("X")
        self.Y = Variable("Y")
        self.PX = Variable("PX")
        self.PY = Variable("PY")
        self.VX = Variable("VX")
        self.VY = Variable("VY")
        self.G = Variable("G")
        self.GX = Variable("GX")
        self.GY = Variable("GY")
        self.R = Variable("R")
        self.N = Variable("N")

        # --- Static Knowledge ---
        self.region_map: Dict[Coord, str] = {}
        mid_x, mid_y = w // 2, h // 2
        for x in range(w):
            for y in range(h):
                c = (x, y)
                if x < mid_x and y < mid_y: r_id = "R1"
                elif x >= mid_x and y < mid_y: r_id = "R2"
                elif x < mid_x and y >= mid_y: r_id = "R3"
                else: r_id = "R4"
                self.region_map[c] = r_id
                self.assert_fact(InRegion(Constant(x), Constant(y), Constant(r_id)))
        
        for r_id in ["R1", "R2", "R3", "R4"]:
            self.assert_fact(RegionPelletCount(Constant(r_id), Constant(0)))

    # --- CORE KB METHODS ---

    def tell(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ):
        """
        Stores all new facts and updates the KB's internal state
        and learned map.
        """
        # --- 1. Store Current Percepts ---
        self.my_pos = my_pos
        self.pacman_pos_percept = pacman_pos
        self.other_ghosts_percept = other_ghost_pos
        self.percepts = percepts

        # --- 2. Retract Old Dynamic Beliefs ---
        old_pacman_pos = None
        bindings = self.query(PacmanPos(self.PX, self.PY))
        if bindings:
            old_pacman_pos = (bindings[0][self.PX].value, bindings[0][self.PY].value)
        
        self.retract(PacmanPos(Variable("X"), Variable("Y")))
        self.retract(PacmanVector(Variable("DX"), Variable("DY")))
        self.retract(GhostPos(Variable("G"), Variable("X"), Variable("Y")))
        
        # --- 3. Learn Map & Assert Facts from Percepts ---
        current_pac_clue = None
        
        # Assert self as safe
        self.assert_fact(LearnedSafe(Constant(my_pos[0]), Constant(my_pos[1])))

        for pos, item in percepts.items():
            cx, cy = Constant(pos[0]), Constant(pos[1])
            
            if item == "WALL":
                self.assert_fact(LearnedWall(cx, cy))
                self.facts.discard(LearnedSafe(cx, cy))
            else:
                # If not a wall, it's safe
                if LearnedSafe(cx, cy) not in self.facts:
                    self.assert_fact(LearnedSafe(cx, cy))
                    # Check/update topology for this new safe tile
                    self._check_topology(pos)
                    # Also check neighbors
                    for n_pos in get_neighbors(pos):
                        self._check_topology(n_pos)

                if item == "PELLET":
                    if SawPelletAt(cx, cy) not in self.facts:
                        self.assert_fact(SawPelletAt(cx, cy))
                        r_id = self.region_map.get(pos)
                        if r_id: self._increment_region_count(r_id)
                
                elif item == "EMPTY":
                    if SawPelletAt(cx, cy) in self.facts:
                        current_pac_clue = pos
                        self.facts.discard(SawPelletAt(cx, cy))
                        r_id = self.region_map.get(pos)
                        if r_id: self._decrement_region_count(r_id)
                
                elif item == "PACMAN":
                    self.pacman_pos_percept = pos # Ensure this is set
        
        # --- 4. Assert Agent Beliefs (Priority: Percept > Clue) ---
        if self.pacman_pos_percept:
            p_pos = self.pacman_pos_percept
            self.assert_fact(PacmanPos(Constant(p_pos[0]), Constant(p_pos[1])))
            if old_pacman_pos:
                dx = p_pos[0] - old_pacman_pos[0]
                dy = p_pos[1] - old_pacman_pos[1]
                if dx != 0 or dy != 0:
                    self.assert_fact(PacmanVector(Constant(dx), Constant(dy)))
        elif current_pac_clue:
            self.assert_fact(PacmanPos(Constant(current_pac_clue[0]), Constant(current_pac_clue[1])))

        for g_id, g_pos in self.other_ghosts_percept:
            self.assert_fact(GhostPos(Constant(g_id), Constant(g_pos[0]), Constant(g_pos[1])))

    def ask(self) -> str:
        """
        Runs inference on the current KB, determines a goal,
        finds a path, and returns a single, safe action.
        """
        
        # --- 1. Run FOL Inference Rules (Determine Goal) ---
        new_goal = None
        safe_tiles = self.get_safe_tiles() # Get current map
        
        pacman_bindings = self.query(PacmanPos(self.PX, self.PY))
        
        if pacman_bindings:
            p_pos = (pacman_bindings[0][self.PX].value, pacman_bindings[0][self.PY].value)
            
            # Rule 1: Flank (Coordinator)
            ghost_bindings = self.query(GhostPos(self.G, self.GX, self.GY))
            for binding in ghost_bindings:
                g_pos = (binding[self.GX].value, binding[self.GY].value)
                dist = abs(p_pos[0] - g_pos[0]) + abs(p_pos[1] - g_pos[1])
                if dist < 4:
                    new_goal = self._find_flank_pos(p_pos, safe_tiles)
                    break
            
            # Rule 2: Intercept (Shepherd)
            if new_goal is None:
                vector_bindings = self.query(PacmanVector(self.VX, self.VY))
                if vector_bindings:
                    p_vec = (vector_bindings[0][self.VX].value, vector_bindings[0][self.VY].value)
                    if p_vec != (0, 0):
                        new_goal = self._find_intercept_junction(p_pos, p_vec)

            # Rule 3: Direct Chase (Fallback)
            if new_goal is None:
                new_goal = p_pos
        
        else:
            # Rule 4: Disjointed Hunt (Analyst)
            region_bindings = self.query(RegionPelletCount(self.R, self.N))
            
            richest_r = None
            max_n = -1
            for binding in region_bindings:
                n = binding[self.N].value
                if n > max_n:
                    max_n = n
                    richest_r = binding[self.R].value
            
            if richest_r and max_n > 0:
                ghost_bindings = self.query(GhostPos(self.G, self.GX, self.GY))
                other_g_pos = [(b[self.GX].value, b[self.GY].value) for b in ghost_bindings]
                new_goal = self._find_furthest_point_in_region(richest_r, other_g_pos, safe_tiles)

        # Rule 5: Default Explore (if all else fails)
        if new_goal is None:
            new_goal = self._find_explore_goal(safe_tiles)

        # --- 2. Update Goal and Path (Pathfinding Logic) ---
        if new_goal is None:
            return self._get_random_safe_move() # No goal, just move randomly

        if new_goal and (new_goal != self.goal or not self.current_path):
            self.goal = new_goal
            path = bfs_pathfinder(self.my_pos, self.goal, safe_tiles)
            self.current_path = path if path else []
        
        if self.my_pos == self.goal:
            self.current_path = []
            
        # --- 3. Get Move from Path ---
        if self.current_path:
            current_step_index = -1
            try:
                current_step_index = self.current_path.index(self.my_pos)
            except ValueError:
                self.current_path = []
                path = bfs_pathfinder(self.my_pos, self.goal, safe_tiles)
                self.current_path = path if path else []
                current_step_index = 0
            
            if current_step_index != -1 and current_step_index + 1 < len(self.current_path):
                next_pos = self.current_path[current_step_index + 1]
                return get_move_from_path(self.my_pos, [self.my_pos, next_pos])

        # Recalculate if path is empty but goal exists
        if self.goal and not self.current_path:
            path = bfs_pathfinder(self.my_pos, self.goal, safe_tiles)
            self.current_path = path if path else []
            if self.current_path and len(self.current_path) > 1:
                return get_move_from_path(self.my_pos, self.current_path)

        return self._get_random_safe_move()

    # --- KB Query & Fact Management ---

    def query(self, query_predicate: Predicate) -> List[Dict[Variable, Constant]]:
        bindings_list = []
        for fact in self.facts:
            substitution = unify(query_predicate, fact)
            if substitution is not None:
                bindings_list.append(substitution)
        return bindings_list

    def retract(self, query_predicate: Predicate):
        facts_to_remove = set()
        for fact in self.facts:
            if unify(query_predicate, fact) is not None:
                facts_to_remove.add(fact)
            elif query_predicate.is_ground() and unify(fact, query_predicate) is not None:
                facts_to_remove.add(fact)
        self.facts.difference_update(facts_to_remove)

    def assert_fact(self, fact: Predicate):
        if fact.is_ground():
            self.facts.add(fact)

    # --- Internal KB Maintenance Helpers ---
    
    def _update_region_count(self, region_id: str, delta: int):
        r_const = Constant(region_id)
        n_var = Variable("N")
        bindings = self.query(RegionPelletCount(r_const, n_var))
        
        if bindings:
            old_count = bindings[0][n_var].value
            old_fact = RegionPelletCount(r_const, Constant(old_count))
            new_count = old_count + delta
            new_fact = RegionPelletCount(r_const, Constant(new_count))
            self.facts.discard(old_fact)
            self.facts.add(new_fact)
        else:
            new_fact = RegionPelletCount(r_const, Constant(max(0, delta)))
            self.facts.add(new_fact)

    def _check_topology(self, pos: Coord):
        if self.query(LearnedSafe(Constant(pos[0]), Constant(pos[1]))):
            safe_neighbors = 0
            for n_pos in get_neighbors(pos):
                if self.query(LearnedSafe(Constant(n_pos[0]), Constant(n_pos[1]))):
                    safe_neighbors += 1
            
            c_pos = (Constant(pos[0]), Constant(pos[1]))
            if safe_neighbors >= 3:
                self.assert_fact(IsJunction(c_pos[0], c_pos[1]))
                self.facts.discard(IsTunnel(c_pos[0], c_pos[1]))
            elif safe_neighbors == 2:
                self.assert_fact(IsTunnel(c_pos[0], c_pos[1]))
                self.facts.discard(IsJunction(c_pos[0], c_pos[1]))
            else:
                self.facts.discard(IsJunction(c_pos[0], c_pos[1]))
                self.facts.discard(IsTunnel(c_pos[0], c_pos[1]))
    
    def get_safe_tiles(self) -> Set[Coord]:
        safe_tiles = set()
        bindings_list = self.query(LearnedSafe(self.X, self.Y))
        for bindings in bindings_list:
            safe_tiles.add((bindings[self.X].value, bindings[self.Y].value))
        return safe_tiles

    # --- Internal Rule Helpers (moved from agent) ---
    
    def _find_flank_pos(self, pac_pos: Coord, safe_tiles: Set[Coord]) -> Optional[Coord]:
        junctions = set()
        j_bindings = self.query(IsJunction(self.X, self.Y))
        for b in j_bindings: junctions.add((b[self.X].value, b[self.Y].value))
        
        if not junctions: return None
        
        nearby_junctions = []
        for j in junctions:
            dist = abs(j[0] - pac_pos[0]) + abs(j[1] - pac_pos[1])
            if dist < 5 and dist > 0: nearby_junctions.append((j, dist))
        
        if not nearby_junctions: return None
        
        nearby_junctions.sort(key=lambda x: x[1])
        return nearby_junctions[0][0]

    def _find_intercept_junction(self, pac_pos: Coord, pac_vec: Coord) -> Optional[Coord]:
        px, py = pac_pos
        vx, vy = pac_vec
        
        for i in range(1, 5):
            next_p = (px + vx*i, py + vy*i)
            if self.query(IsJunction(Constant(next_p[0]), Constant(next_p[1]))):
                return next_p
            if self.query(LearnedWall(Constant(next_p[0]), Constant(next_p[1]))):
                return None
        return None

    def _find_furthest_point_in_region(self, region_id: str, other_ghost_pos: List[Coord], safe_tiles: Set[Coord]) -> Optional[Coord]:
        region_tiles = set()
        r_bindings = self.query(InRegion(self.X, self.Y, Constant(region_id)))
        for b in r_bindings:
            p = (b[self.X].value, b[self.Y].value)
            if p in safe_tiles: region_tiles.add(p)
        
        if not region_tiles: return None
        
        if not other_ghost_pos:
            pellet_bindings = self.query(SawPelletAt(self.X, self.Y))
            for b in pellet_bindings:
                p = (b[self.X].value, b[self.Y].value)
                if p in region_tiles: return p
            return list(region_tiles)[0]

        avg_ghost_x = sum(p[0] for p in other_ghost_pos) / len(other_ghost_pos)
        avg_ghost_y = sum(p[1] for p in other_ghost_pos) / len(other_ghost_pos)
        
        farthest_p, max_dist_sq = None, -1
        for p in region_tiles:
            dist_sq = (p[0] - avg_ghost_x)**2 + (p[1] - avg_ghost_y)**2
            if dist_sq > max_dist_sq:
                max_dist_sq, farthest_p = dist_sq, p
        return farthest_p

    def _find_explore_goal(self, safe_tiles: Set[Coord]) -> Optional[Coord]:
        unknown_tiles = set()
        for sx, sy in safe_tiles:
            for n_pos in get_neighbors((sx,sy)):
                if n_pos not in safe_tiles and not self.query(LearnedWall(Constant(n_pos[0]), Constant(n_pos[1]))):
                    unknown_tiles.add(n_pos)
        
        if unknown_tiles:
            return find_nearest_coord(self.my_pos, unknown_tiles, safe_tiles)
        
        junctions = set()
        j_bindings = self.query(IsJunction(self.X, self.Y))
        for b in j_bindings: junctions.add((b[self.X].value, b[self.Y].value))
        if junctions:
            return find_nearest_coord(self.my_pos, junctions, safe_tiles)
        
        return None
        
    def _get_random_safe_move(self) -> str:
        """Failsafe for when pathfinding fails or no goal exists."""
        possible_moves = []
        for move, (dx, dy) in MOVES.items():
            if move == 'WAIT': continue
            check_pos = (self.my_pos[0] + dx, self.my_pos[1] + dy)
            if self.query(LearnedSafe(Constant(check_pos[0]), Constant(check_pos[1]))):
                possible_moves.append(move)
        
        if possible_moves:
            return random.choice(possible_moves)
        return 'WAIT'