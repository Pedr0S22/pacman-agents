from typing import Tuple, Dict, Set, List, Optional
from utils.types_utils import Coord, Percept
from utils.fol_components import Predicate, Constant, Variable, unify
from predicates import *

class KnowledgeBaseC:
    """
    KB for Ghost C ("The Overlord").
    This is a formal FOL KB. It stores all beliefs as a
    set of ground predicates (Facts).
    """
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        
        # The Knowledge Base is a set of ground predicates
        self.facts: Set[Predicate] = set()

        # Pre-calculate region mappings (static knowledge)
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
                # Assert the static InRegion facts
                self.facts.add(InRegion(Constant(x), Constant(y), Constant(r_id)))
        
        # Initialize pellet counts for regions
        for r_id in ["R1", "R2", "R3", "R4"]:
            self.facts.add(RegionPelletCount(Constant(r_id), Constant(0)))

    def query(self, query_predicate: Predicate) -> List[Dict[Variable, Constant]]:
        """
        Runs a query against the KB.
        Returns a list of all successful substitutions.
        e.g., query(PacmanPos(Variable("X"), Variable("Y")))
        """
        bindings_list = []
        for fact in self.facts:
            substitution = unify(query_predicate, fact)
            if substitution is not None:
                bindings_list.append(substitution)
        return bindings_list

    def retract(self, query_predicate: Predicate):
        """
        Finds and removes all facts that match a query.
        e.g., retract(PacmanPos(Variable("X"), Variable("Y")))
        """
        facts_to_remove = set()
        for fact in self.facts:
            # Need to check both ways for unification, e.g.,
            # query(PacmanPos(X,Y)) should remove PacmanPos(1,1)
            # query(PacmanPos(1,1)) should remove PacmanPos(1,1)
            if unify(query_predicate, fact) is not None:
                facts_to_remove.add(fact)
            elif query_predicate.is_ground() and unify(fact, query_predicate) is not None:
                 facts_to_remove.add(fact)

        self.facts.difference_update(facts_to_remove)

    def assert_fact(self, fact: Predicate):
        """Adds a single ground fact to the KB."""
        if fact.is_ground():
            # Avoid duplicate facts
            self.facts.add(fact)

    def update_from_percepts(
        self,
        my_pos: Coord,
        pacman_pos_percept: Optional[Coord],
        other_ghosts_percept: List[Tuple[str, Coord]],
        percepts: Percept
    ):
        """The 'learning' and 'belief update' function."""
        
        # --- 1. Retract old dynamic beliefs ---
        # Get old PacmanPos to infer vector
        old_pacman_pos = None 
        bindings = self.query(PacmanPos(Variable("X"), Variable("Y")))
        if bindings:
            old_pacman_pos = (bindings[0][Variable("X")].value, bindings[0][Variable("Y")].value)
        
        self.retract(PacmanPos(Variable("X"), Variable("Y")))
        self.retract(PacmanVector(Variable("DX"), Variable("DY")))
        self.retract(GhostPos(Variable("G"), Variable("X"), Variable("Y")))
        
        # --- 2. Learn Map & Assert Facts from Percepts ---
        current_pac_clue = None

        for pos, item in percepts.items():
            cx, cy = Constant(pos[0]), Constant(pos[1])
            
            if item == "WALL":
                self.assert_fact(LearnedWall(cx, cy))
                self.facts.discard(LearnedSafe(cx, cy)) # Retract safe if it was a wall
            else:
                # If not a wall, it's safe
                if LearnedSafe(cx, cy) not in self.facts:
                    self.assert_fact(LearnedSafe(cx, cy))
                    # Check/update topology for this new safe tile
                    self._check_topology(pos)
                    # Also check neighbors, as this might complete them
                    for n_pos in [(pos[0]+1, pos[1]), (pos[0]-1, pos[1]), (pos[0], pos[1]+1), (pos[0], pos[1]-1)]:
                         self._check_topology(n_pos)


                if item == "PELLET":
                    # Assert SawPelletAt *only if we haven't*
                    if SawPelletAt(cx, cy) not in self.facts:
                        self.assert_fact(SawPelletAt(cx, cy))
                        # Update region count
                        r_id = self.region_map.get(pos)
                        if r_id:
                            self._increment_region_count(r_id)
                
                elif item == "EMPTY":
                    # Check for "clue"
                    if SawPelletAt(cx, cy) in self.facts:
                        # Pac-Man was here!
                        current_pac_clue = pos
                        # Remove pellet fact and update count
                        self.facts.discard(SawPelletAt(cx, cy))
                        r_id = self.region_map.get(pos)
                        if r_id:
                            self._decrement_region_count(r_id)
                
                elif item == "PACMAN":
                    # Direct sight overrides clues
                    pacman_pos_percept = pos
        
        # --- 3. Assert Agent Beliefs (Priority: Percept > Clue) ---
        if pacman_pos_percept:
            self.assert_fact(PacmanPos(Constant(pacman_pos_percept[0]), Constant(pacman_pos_percept[1])))
            if old_pacman_pos:
                # Infer vector
                dx = pacman_pos_percept[0] - old_pacman_pos[0]
                dy = pacman_pos_percept[1] - old_pacman_pos[1]
                # Only assert a non-zero vector
                if dx != 0 or dy != 0:
                    self.assert_fact(PacmanVector(Constant(dx), Constant(dy)))
        elif current_pac_clue:
            # No direct sight, but we found a clue
            self.assert_fact(PacmanPos(Constant(current_pac_clue[0]), Constant(current_pac_clue[1])))

        for g_id, g_pos in other_ghosts_percept:
            self.assert_fact(GhostPos(Constant(g_id), Constant(g_pos[0]), Constant(g_pos[1])))

    # --- Internal KB Maintenance ---
    
    def _increment_region_count(self, region_id: str):
        self._update_region_count(region_id, 1)

    def _decrement_region_count(self, region_id: str):
        self._update_region_count(region_id, -1)

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
            # Should have been initialized, but as a fallback
            new_fact = RegionPelletCount(r_const, Constant(max(0, delta)))
            self.facts.add(new_fact)

    def _check_topology(self, pos: Coord):
        """Infers and asserts Junction/Tunnel facts."""
        if LearnedSafe(Constant(pos[0]), Constant(pos[1])) not in self.facts:
            return # Only check known safe tiles

        safe_neighbors = 0
        for nx, ny in [(pos[0]+1, pos[1]), (pos[0]-1, pos[1]), (pos[0], pos[1]+1), (pos[0], pos[1]-1)]:
            if LearnedSafe(Constant(nx), Constant(ny)) in self.facts:
                safe_neighbors += 1
        
        c_pos = (Constant(pos[0]), Constant(pos[1]))
        if safe_neighbors >= 3:
            self.assert_fact(IsJunction(c_pos[0], c_pos[1]))
            self.facts.discard(IsTunnel(c_pos[0], c_pos[1]))
        elif safe_neighbors == 2:
            # Basic tunnel logic (could be improved to check for opposites)
            self.assert_fact(IsTunnel(c_pos[0], c_pos[1]))
            self.facts.discard(IsJunction(c_pos[0], c_pos[1]))
        else:
            # It's a dead end or open space
            self.facts.discard(IsJunction(c_pos[0], c_pos[1]))
            self.facts.discard(IsTunnel(c_pos[0], c_pos[1]))
    
    # --- Helper for pathfinding (must query KB) ---
    def get_safe_tiles(self) -> Set[Coord]:
        """Returns all learned safe tiles for the pathfinder."""
        safe_tiles = set()
        bindings_list = self.query(LearnedSafe(Variable("X"), Variable("Y")))
        for bindings in bindings_list:
            x = bindings[Variable("X")].value
            y = bindings[Variable("Y")].value
            safe_tiles.add((x, y))
        return safe_tiles