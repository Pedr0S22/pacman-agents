from typing import Tuple, Set, Dict, List, Optional
from utils.types_utils import Coord
import random
import time

class Environment:
    """Grid representing the game environment."""
    def __init__(
        self,
        w: int,
        h: int,
        walls: Set[Coord] = None,
        pellets: Set[Coord] = None,
        pacman_start: Coord = None,
        ghostA_start: Coord = None,
        ghostB_start: Coord = None,
        ghostC_start: Coord = None

    ):
        self.w, self.h = w, h
        self.walls: Set[Coord] = set(walls or set())
        self.pellets: Set[Coord] = set(pellets or set())
        self.pacman_pos: Coord = pacman_start

        self.ghostA_pos: Coord = ghostA_start
        self.ghostB_pos: Coord = ghostB_start
        self.ghostC_pos: Coord = ghostC_start
        self.ghost_spawns: Set[Coord] = {ghostA_start, ghostB_start, ghostC_start}

        self.iterations: int = 0
        self.victory: bool = False
        self.game_over: bool = False
        self.score: int = 0
        self.lives: int = 2

        # Storing start positions for respawn
        self.ghostA_start_pos = ghostA_start
        self.ghostB_start_pos = ghostB_start
        self.ghostC_start_pos = ghostC_start

    def in_bounds(self, c: Coord) -> bool:
        """Return True if coordinate c is within grid bounds."""
        x, y = c
        return 0 <= x < self.w and 0 <= y < self.h

    def pacman_blocked(self, c: Coord) -> bool:
        """
        Return True if coordinate c is blocked for Pac-Man.
        Pac-Man is blocked by walls, bounds, OR the ghost spawn.
        """
        return (
            (not self.in_bounds(c)) or
            (c in self.walls)
        )

    def ghost_blocked(self, c: Coord) -> bool:
        """
        Return True if coordinate c is blocked for a Ghost.
        Ghosts are blocked by walls and bounds, but NOT spawns.
        """
        return (
            (not self.in_bounds(c)) or
            (c in self.walls)
        )
    
    def get_ghost_percepts(
        self,
        ghost_id: str # 'A', 'B', or 'C'
    ) -> Tuple[Optional[Coord], List[Tuple[str, Coord]], Dict[Coord, str]]:
        """
        Calculates the 4-cell line-of-sight percepts for a ghost.
        Line-of-sight is blocked by walls.

        Returns a tuple of:
        1. pacman_pos: (x,y) if seen, else None
        2. other_ghosts: List[(id, (x,y))] of other seen ghosts
        3. percept_map: A dictionary {(x,y): "ITEM"} for all seen tiles.
        """
        
        percept_map: Dict[Coord, str] = {}
        pacman_pos_seen: Optional[Coord] = None
        other_ghosts_seen: List[Tuple[str, Coord]] = []
        
        ghost_pos = (0,0)
        if ghost_id == 'A': ghost_pos = self.ghostA_pos
        elif ghost_id == 'B': ghost_pos = self.ghostB_pos
        elif ghost_id == 'C': ghost_pos = self.ghostC_pos
        
        # Define the 4 cardinal directions
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)] # UP, DOWN, LEFT, RIGHT
        
        for dx, dy in directions:
            for i in range(1, 5): # See up to 4 cells
                x, y = ghost_pos[0] + dx * i, ghost_pos[1] + dy * i
                pos = (x, y)
                
                # Check for walls first, as they block sight
                if pos in self.walls:
                    percept_map[pos] = "WALL"
                    break # Stop seeing in this direction
                
                # Check for Pac-Man
                if pos == self.pacman_pos:
                    percept_map[pos] = "PACMAN"
                    pacman_pos_seen = pos
                
                # Check for other ghosts
                elif pos == self.ghostA_pos and ghost_id != 'A':
                    percept_map[pos] = "GHOST"
                    other_ghosts_seen.append(("A", pos))
                elif pos == self.ghostB_pos and ghost_id != 'B':
                    percept_map[pos] = "GHOST"
                    other_ghosts_seen.append(("B", pos))
                elif pos == self.ghostC_pos and ghost_id != 'C':
                    percept_map[pos] = "GHOST"
                    other_ghosts_seen.append(("C", pos))
                
                # Check for pellets
                elif pos in self.pellets:
                    percept_map[pos] = "PELLET"
                
                # If nothing else, it's an empty, traversable tile
                else:
                    # add empty tiles
                    percept_map[pos] = "EMPTY"

        return pacman_pos_seen, other_ghosts_seen, percept_map

    def sense(self) -> Dict:
        """Return a percept dictionary describing the current state."""
        return dict(
            pos=self.pacman_pos,
            pellet_here=(self.pacman_pos in self.pellets),
            iterations=self.iterations,
            victory=self.victory
        )
    
    def move_ghost(self, ghost_id: str, action: str) -> None:
        """Moves the specified ghost (A, B, or C) one step."""

        current_pos = None
        if ghost_id == 'A':
            current_pos = self.ghostA_pos
        elif ghost_id == 'B':
            current_pos = self.ghostB_pos
        elif ghost_id == 'C':
            current_pos = self.ghostC_pos
        else:
            return # Invalid ghost ID

        moves = {'RIGHT': (1, 0), 'LEFT': (-1, 0), 'DOWN': (0, 1), 'UP': (0, -1), 'WAIT': (0,0)}

        if action in moves:
            dx, dy = moves[action]
            nx, ny = current_pos[0] + dx, current_pos[1] + dy

            # Ghosts use their own blocking logic
            if not self.ghost_blocked((nx, ny)):
                if ghost_id == 'A':
                    self.ghostA_pos = (nx, ny)
                elif ghost_id == 'B':
                    self.ghostB_pos = (nx, ny)
                elif ghost_id == 'C':
                    self.ghostC_pos = (nx, ny)

        self.check_collision()

    def check_collision(self) -> bool:
        """Checks if Pac-Man and any Ghost are on the same tile."""
        if self.pacman_pos == self.ghostA_pos or \
            self.pacman_pos == self.ghostB_pos or \
            self.pacman_pos == self.ghostC_pos:
            
            self.lives -= 1

            if self.lives == -1:
                self.game_over = True
            return True # Collision happened
        return False
    
    def respawn_ghosts(self) -> None:
        """Moves ghosts to the 3 corners farthest from Pac-Man."""
        corners = [(1, 1), (self.w - 2, 1), (1, self.h - 2), (self.w - 2, self.h - 2)]
        px, py = self.pacman_pos

        scored_corners = []
        for cx, cy in corners:
            # Manhathan distance
            dist = abs(cx - px) + abs(cy - py)
            scored_corners.append(((cx, cy), dist))
        
        scored_corners.sort(key=lambda x: x[1], reverse=True)
        top_three_positions = [corner[0] for corner in scored_corners[:3]]
        random.shuffle(top_three_positions)
        
        self.ghostA_pos = top_three_positions[0]
        self.ghostB_pos = top_three_positions[1]
        self.ghostC_pos = top_three_positions[2]

    def step(self, action: str) -> None:
        """Advance the environment one step given an action string.
            Supported actions: 'UP', 'DOWN', 'LEFT', 'RIGHT' to move."""
        if self.victory or self.game_over:
            return

        self.iterations += 1

        # Move Pac-Man according to the action
        moves = {'RIGHT': (1, 0), 'LEFT': (-1, 0), 'DOWN': (0, 1), 'UP': (0, -1)}
        if action in moves:
            dx, dy = moves[action]
            nx, ny = self.pacman_pos[0] + dx, self.pacman_pos[1] + dy
            if not self.pacman_blocked((nx, ny)):
                self.pacman_pos = (nx, ny)

        # Collect pellet if needed and add score
        if self.pacman_pos in self.pellets:
            self.pellets.remove(self.pacman_pos)
            self.score +=10

        # Check Collision (Ghost kill Pac-Man)
        self.check_collision()

        # Check if no pellets are left or no lives left
        if len(self.pellets) == 0:
            self.victory = True
        
        if self.lives == -1:
            self.game_over = True

    def render(self) -> str:
        """Return a multi-line string visualization of the grid.

        Legend:
            'P' - Pac-Man
            'A' - Ghost A
            'B' - Ghost B
            'C' - Ghost C
            '#' - Wall
            '.' - Pellet
            ' ' - Empty space
        """
        buf: List[str] = []
        status_line = f"Iterations={self.iterations} | Pellets left={len(self.pellets)}\nLeft Lives={self.lives if self.lives > 0 else 0} | Score={self.score}\n"
        buf.append(status_line)

        for y in range(self.h):
            row = []
            for x in range(self.w):
                c = (x, y)
                if c == self.ghostA_pos:
                    ch = 'A'
                elif c == self.ghostB_pos:
                    ch = 'B'
                elif c == self.ghostC_pos:
                    ch = 'C'
                elif c == self.pacman_pos:
                    ch = 'P'
                elif c in self.walls:
                    ch = '#'
                elif c in self.pellets:
                    ch = '.'
                else:
                    ch = ' '
                row.append(ch)
            buf.append(''.join(row))

        if self.victory:
            buf.append("VICTORY!")

        if self.game_over:
            buf.append("GAME OVER!")

        return '\n'.join(buf)
    
def generate_maze(
    w: int,
    h: int,
    pellet_density: float = 0.5
) -> Tuple[Set[Coord], Set[Coord], Coord, Coord, Coord, Coord]:
    """
    Generate a fixed 25x10 maze and randomly place pellets in free spaces.

    ASCII representation of the fixed maze:
    '#' = Wall
    ' ' = Empty space
    """
    # --- Define the Fixed Maze Layout ---

    maze_ascii = [
        "#########################", # y=0
        "#           #           #", # y=1
        "# #########   ######### #", # y=2
        "# #       # # #       # #", # y=3
        "# # #####   #   ##### # #", # y=4
        "# #       #####       # #", # y=5
        "#   ## ##       ## ##   #", # y=6
        "#   #      ###      #   #", # y=7
        "#     #############     #", # y=8
        "#########################"  # y=9
    ]

    # --- Process the Maze ---

    walls: Set[Coord] = set()
    free_cells: List[Coord] = []

    for y, row in enumerate(maze_ascii):
        for x, char in enumerate(row):
            c = (x, y)
            if char == '#':
                walls.add(c)
            else:
                free_cells.append(c)

    # --- Pac-Man and Ghosts positioning ---

    corners = [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]
    for c in corners:
        walls.discard(c) # Remove wall if it exists
        if c not in free_cells:
            free_cells.append(c)

    pacman_start = (1, 1)
    ghostA_start = (w - 2, 1)
    ghostB_start = (w - 2, h - 2)
    ghostC_start = (1, h - 2)
    
    # Ensure Pac-Man's or Ghost's start is not a wall (as a safety check)
    if pacman_start in walls:
        walls.discard(pacman_start)

    if ghostA_start in walls:
        walls.discard(ghostA_start)

    if ghostB_start in walls:
        walls.discard(ghostB_start)

    if ghostC_start in walls:
        walls.discard(ghostC_start)

    # --- Generate Pellets ---

    reserved_spots = {pacman_start, ghostA_start, ghostB_start, ghostC_start}
    possible_pellet_cells = [c for c in free_cells if c not in reserved_spots]
    
    # Place pellets randomly in the available free cells
    rng = random.Random()
    k_pellets = max(1, int(pellet_density * len(possible_pellet_cells)))
    
    # Use possible_pellet_cells instead of free_cells
    pellets = set(rng.sample(possible_pellet_cells, k_pellets)) if k_pellets > 0 else set()

    return walls, pellets, pacman_start, ghostA_start, ghostB_start, ghostC_start