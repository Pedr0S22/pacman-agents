from typing import Set, Optional
from utils.types_utils import Coord, Percept

class KnowledgeBaseB:
    """
    KB for Ghost B ("The Ambusher").
    This is a "smart" PL KB. It learns the map from scratch.
    """
    def __init__(self):
        # --- The Learned Map ---
        # Starts empty and is built from percepts.
        self.walls: Set[Coord] = set()
        self.safe_tiles: Set[Coord] = set()
        self.seen_pellets: Set[Coord] = set()
        self.junctions: Set[Coord] = set()
        self.unknown_tiles: Set[Coord] = set() # For exploration
        
        # --- Beliefs ---
        self.pacman_clue: Optional[Coord] = None
        self.clue_age: int = 0
        self.max_clue_age: int = 20 # Give up on a clue after 20 steps
        
        # Add starting tile as safe
        self.safe_tiles.add((0,0)) # Will be updated on first move
        self.unknown_tiles.add((0,0))

    def _add_safe_tile(self, pos: Coord, percepts: Percept):
        """Adds a tile as safe and updates unknown/junction status."""
        if pos in self.safe_tiles:
            return # Already processed
            
        self.safe_tiles.add(pos)
        self.unknown_tiles.discard(pos)
        self.walls.discard(pos) # In case it was inferred wrong
        
        # Add neighbors to 'unknown'
        for nx, ny in [(pos[0]+1, pos[1]), (pos[0]-1, pos[1]), (pos[0], pos[1]+1), (pos[0], pos[1]-1)]:
            neighbor = (nx, ny)
            if neighbor not in self.safe_tiles and neighbor not in self.walls:
                self.unknown_tiles.add(neighbor)

        # Check for junction
        self._check_for_junction(pos, percepts)
        # Re-check neighbors too, as this tile might complete them
        for nx, ny in [(pos[0]+1, pos[1]), (pos[0]-1, pos[1]), (pos[0], pos[1]+1), (pos[0], pos[1]-1)]:
            self._check_for_junction((nx, ny), percepts)

    def _check_for_junction(self, pos: Coord, percepts: Percept):
        """
        Infers if a tile is a junction.
        A junction is a safe tile with 3+ safe, non-wall neighbors.
        We use percepts for immediate info, and self.safe_tiles for learned info.
        """
        if pos not in self.safe_tiles:
            return # Not a safe tile

        safe_neighbors = 0
        for nx, ny in [(pos[0]+1, pos[1]), (pos[0]-1, pos[1]), (pos[0], pos[1]+1), (pos[0], pos[1]-1)]:
            neighbor = (nx, ny)
            # Check percepts first (most accurate)
            if neighbor in percepts and percepts[neighbor] != "WALL":
                safe_neighbors += 1
            # Check learned map
            elif neighbor in self.safe_tiles:
                safe_neighbors += 1
        
        if safe_neighbors >= 3:
            self.junctions.add(pos)

    def update_from_percepts(self, percepts: Percept):
        """
        The "learning" part of the KB.
        Updates the map based on new line-of-sight info.
        """
        new_clue = None
        
        for pos, item in percepts.items():
            if item == "WALL":
                self.walls.add(pos)
                self.safe_tiles.discard(pos)
                self.unknown_tiles.discard(pos)
            
            elif item == "PELLET":
                self._add_safe_tile(pos, percepts)
                self.seen_pellets.add(pos) # Add to "memory"
            
            elif item == "EMPTY":
                self._add_safe_tile(pos, percepts)
                # --- The "Aha!" Moment ---
                if pos in self.seen_pellets:
                    # Found a clue! Pac-Man was here.
                    new_clue = pos
            
            elif item == "PACMAN":
                self._add_safe_tile(pos, percepts)
                # Clear clues if we have direct sight
                self.pacman_clue = None
                self.clue_age = 0
            
            else: # Other ghosts, etc.
                self._add_safe_tile(pos, percepts)
        
        if new_clue:
            # We found a new clue
            self.pacman_clue = new_clue
            self.clue_age = 0

    def get_clue(self) -> Optional[Coord]:
        """Returns the current clue, if it's not too old."""
        if not self.pacman_clue:
            return None
        
        self.clue_age += 1
        if self.clue_age > self.max_clue_age:
            self.pacman_clue = None # Clue is stale
            self.clue_age = 0
            return None
            
        return self.pacman_clue

    def get_explore_goal(self) -> Optional[Coord]:
        """Gets the nearest unknown tile to explore."""
        # This is a simple implementation. A real one would use BFS
        # from current pos, but this is faster.
        if self.unknown_tiles:
            return list(self.unknown_tiles)[0]
        return None

    def get_patrol_goal(self) -> Optional[Coord]:
        """Gets the nearest junction to camp at."""
        if self.junctions:
            # In a real impl, we'd find the *nearest*
            return list(self.junctions)[0]
        return None