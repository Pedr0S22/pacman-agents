from typing import Tuple, Set, List, Optional
from utils.types_utils import Coord, Percept
from utils.path_utils import bfs_pathfinder, get_move_from_path, find_nearest_coord
from utils.fol_components import Constant, Variable
from ghost_c_kb import KnowledgeBaseC
from predicates import *
import random

class GhostC:
    """
    Ghost C: The "Overlord" (FOL Agent)
    - Logic: First-Order Logic (formal KB and queries)
    - KB: Learns map, topology, and models other agents.
    - Behavior: Uses prioritized rules (Flank, Intercept, Hunt)
        by querying its FOL knowledge base.
    """
    def __init__(self, w: int, h: int):
        self.kb = KnowledgeBaseC(w, h)
        self.goal: Optional[Coord] = None
        self.current_path: List[Coord] = []
        
        # --- Define reusable variables for queries ---
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


    def get_next_move(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ) -> str:
        
        # --- 0. Add self to known safe tiles ---
        self.kb.assert_fact(LearnedSafe(Constant(my_pos[0]), Constant(my_pos[1])))
            
        # --- 1. Update KB from Percepts ---
        self.kb.update_from_percepts(
            my_pos,
            pacman_pos,
            other_ghost_pos,
            percepts
        )
        
        # --- 2. Run FOL Inference Rules (Determine Goal) ---
        new_goal = None
        safe_tiles = self.kb.get_safe_tiles() # Get current map
        
        # --- Query for Pacman's Position ---
        pacman_bindings = self.kb.query(PacmanPos(self.PX, self.PY))
        
        if pacman_bindings:
            # Pac-Man's location is known
            p_pos = (pacman_bindings[0][self.PX].value, pacman_bindings[0][self.PY].value)
            
            # Rule 1: Flank (Coordinator)
            # Query: ∃g, G (GhostPos(G, g) ∧ G ≠ Self ∧ Distance(p, g) < 4)
            ghost_bindings = self.kb.query(GhostPos(self.G, self.GX, self.GY))
            for binding in ghost_bindings:
                g_pos = (binding[self.GX].value, binding[self.GY].value)
                dist = abs(p_pos[0] - g_pos[0]) + abs(p_pos[1] - g_pos[1])
                if dist < 4:
                    new_goal = self._find_flank_pos(my_pos, p_pos, safe_tiles)
                    break
            
            # Rule 2: Intercept (Shepherd)
            if new_goal is None:
                vector_bindings = self.kb.query(PacmanVector(self.VX, self.VY))
                if vector_bindings:
                    p_vec = (vector_bindings[0][self.VX].value, vector_bindings[0][self.VY].value)
                    if p_vec != (0, 0):
                        new_goal = self._find_intercept_junction(p_pos, p_vec)

            # Rule 3: Direct Chase (Fallback)
            if new_goal is None:
                new_goal = p_pos
        
        else:
            # Pac-Man's location is *unknown*
            # Rule 4: Disjointed Hunt (Analyst)
            # Query: Find R such that ∀R' (RegionPelletCount(R, N) ≥ RegionPelletCount(R', N'))
            region_bindings = self.kb.query(RegionPelletCount(self.R, self.N))
            
            richest_r = None
            max_n = -1
            for binding in region_bindings:
                n = binding[self.N].value
                if n > max_n:
                    max_n = n
                    richest_r = binding[self.R].value
            
            if richest_r and max_n > 0:
                # Query: ∃g, G (GhostPos(G, g))
                ghost_bindings = self.kb.query(GhostPos(self.G, self.GX, self.GY))
                other_g_pos = [(b[self.GX].value, b[self.GY].value) for b in ghost_bindings]
                
                new_goal = self._find_furthest_point_in_region(richest_r, other_g_pos, safe_tiles)

        # Rule 5: Default Explore (if all else fails)
        if new_goal is None:
            # Find nearest unknown, by checking neighbors of safe tiles
            unknown_tiles = set()
            for sx, sy in safe_tiles:
                for nx, ny in [(sx+1, sy), (sx-1, sy), (sx, sy+1), (sx, sy-1)]:
                    n_pos = (nx,ny)
                    # An unknown tile is one that is not safe and not a known wall
                    if n_pos not in safe_tiles and not self.kb.query(LearnedWall(Constant(nx), Constant(ny))):
                        unknown_tiles.add(n_pos)
            
            if unknown_tiles:
                new_goal = find_nearest_coord(my_pos, unknown_tiles, safe_tiles)
            
            # If still no goal, find nearest junction
            if new_goal is None:
                junctions = set()
                j_bindings = self.kb.query(IsJunction(self.X, self.Y))
                for b in j_bindings:
                    junctions.add((b[self.X].value, b[self.Y].value))
                if junctions:
                    new_goal = find_nearest_coord(my_pos, junctions, safe_tiles)


        # --- 3. Update Goal and Path ---
        if new_goal and (new_goal != self.goal or not self.current_path):
            self.goal = new_goal
            path = bfs_pathfinder(
                start_pos=my_pos,
                goal_pos=self.goal,
                safe_tiles=safe_tiles
            )
            self.current_path = path if path else []
        
        if my_pos == self.goal:
            self.current_path = []
            
        # --- 4. Get Move from Path ---
        if self.current_path:
            # Handle path consumption
            current_step_index = -1
            try:
                current_step_index = self.current_path.index(my_pos)
            except ValueError:
                # We are off-path, recalculate
                self.current_fpath = []
                if self.goal:
                    path = bfs_pathfinder(my_pos, self.goal, safe_tiles)
                    self.current_path = path if path else []
                
            if current_step_index != -1 and current_step_index + 1 < len(self.current_path):
                next_pos = self.current_path[current_step_index + 1]
                return get_move_from_path(my_pos, [my_pos, next_pos])

        # Recalculate if path is empty but goal exists
        if self.goal and not self.current_path:
            path = bfs_pathfinder(my_pos, self.goal, safe_tiles)
            self.current_path = path if path else []
            if self.current_path and len(self.current_path) > 1:
                return get_move_from_path(my_pos, self.current_path)

        return 'WAIT'
        
    # --- Helper functions for FOL rules ---
    
    def _find_flank_pos(self, my_pos: Coord, pac_pos: Coord, safe_tiles: Set[Coord]) -> Optional[Coord]:
        junctions = set()
        j_bindings = self.kb.query(IsJunction(self.X, self.Y))
        for b in j_bindings:
            junctions.add((b[self.X].value, b[self.Y].value))
        
        if not junctions: return None
        
        nearby_junctions = []
        for j in junctions:
            dist = abs(j[0] - pac_pos[0]) + abs(j[1] - pac_pos[1])
            if dist < 5 and dist > 0: # Find close, but not on-top
                nearby_junctions.append((j, dist))
        
        if not nearby_junctions: return None
        
        nearby_junctions.sort(key=lambda x: x[1])
        # Simple heuristic: pick the closest junction to Pac-Man
        return nearby_junctions[0][0]

    def _find_intercept_junction(self, pac_pos: Coord, pac_vec: Coord) -> Optional[Coord]:
        px, py = pac_pos
        vx, vy = pac_vec
        
        for i in range(1, 5): # Check 4 steps ahead
            next_p = (px + vx*i, py + vy*i)
            if self.kb.query(IsJunction(Constant(next_p[0]), Constant(next_p[1]))):
                return next_p # Found junction on path
            if self.kb.query(LearnedWall(Constant(next_p[0]), Constant(next_p[1]))):
                return None # Hit a wall, path Prediction failed
        return None

    def _find_furthest_point_in_region(self, region_id: str, other_ghost_pos: List[Coord], safe_tiles: Set[Coord]) -> Optional[Coord]:
        region_tiles = set()
        r_bindings = self.kb.query(InRegion(self.X, self.Y, Constant(region_id)))
        for b in r_bindings:
            p = (b[self.X].value, b[self.Y].value)
            if p in safe_tiles:
                region_tiles.add(p)
        
        if not region_tiles:
            return None
        
        # If no other ghosts, just pick a pellet from the region
        if not other_ghost_pos:
            pellet_bindings = self.kb.query(SawPelletAt(self.X, self.Y))
            for b in pellet_bindings:
                p = (b[self.X].value, b[self.Y].value)
                if p in region_tiles:
                    return p
            # No pellets? Just pick a random tile
            return list(region_tiles)[0]

        avg_ghost_x = sum(p[0] for p in other_ghost_pos) / len(other_ghost_pos)
        avg_ghost_y = sum(p[1] for p in other_ghost_pos) / len(other_ghost_pos)
        
        farthest_p = None
        max_dist_sq = -1

        for p in region_tiles:
            dist_sq = (p[0] - avg_ghost_x)**2 + (p[1] - avg_ghost_y)**2
            if dist_sq > max_dist_sq:
                max_dist_sq = dist_sq
                farthest_p = p
        
        return farthest_p