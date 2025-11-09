from typing import Tuple, Set, Dict, List
import random

Coord = Tuple[int, int]

class Environment:
    """Grid representing the game environment."""
    def __init__(
        self,
        w: int,
        h: int,
        walls: Set[Coord] = None,
        pellets: Set[Coord] = None,
        pacman_start: Coord = (1, 1),
        ghostA_start: Coord = (23,8),
        ghostB_start: Coord = (23,7),
        ghostC_start: Coord = (22,8)

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
            (c in self.walls) or
            (c in self.ghost_spawns)
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

    def sense(self) -> Dict:
        """Return a percept dictionary describing the current state."""
        return dict(
            pos=self.pacman_pos,
            pellet_here=(self.pacman_pos in self.pellets),
            iterations=self.iterations,
            victory=self.victory
        )
    
    def move_ghost(self, ghost_id: str, action: str):
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

    def step(self, action: str):
        """Advance the environment one step given an action string.
            Supported actions: 'UP', 'DOWN', 'LEFT', 'RIGHT' to move."""
        if self.victory or self.game_over:
            return

        self.iterations += 1

        # Move according to the action
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

        if self.pacman_pos == self.ghostA_pos or self.pacman_pos == self.ghostB_pos or self.pacman_pos == self.ghostC_pos:
            self.lives -=1

            # Ghosts return to spawn area
            self.ghostA_pos = self.ghostA_start_pos
            self.ghostB_pos = self.ghostB_start_pos
            self.ghostC_pos = self.ghostC_start_pos

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
            'x' - Ghost Spawn
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
                if c == self.pacman_pos:
                    ch = 'P'
                elif c == self.ghostA_pos:
                    ch = 'A'
                elif c == self.ghostB_pos:
                    ch = 'B'
                elif c == self.ghostC_pos:
                    ch = 'C'
                elif c in self.walls:
                    ch = '#'
                elif c in self.ghost_spawns:
                    ch = 'x'
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
) -> Tuple[Set[Coord], Set[Coord], Coord]:
    """
    Generate a fixed 25x10 maze and randomly place pellets in free spaces.

    ASCII representation of the fixed maze:
    '#' = Wall
    ' ' = Empty space
    """
    # --- Define the Fixed Maze Layout ---

    # Pac-Man's starting position
    pacman_start = (1, 1)
    ghostA_start = (23,8)
    ghostB_start = (23,7)
    ghostC_start = (22,8)

    start_positions = {pacman_start, ghostA_start, ghostB_start, ghostC_start}

    maze_ascii = [
        "#########################", # y=0
        "#           #           #", # y=1
        "# ######### # ######### #", # y=2
        "# #       # # #       # #", # y=3
        "# # #####   #   ##### # #", # y=4
        "# #       #   #       # #", # y=5
        "#   ## ####   #### ##   #", # y=6
        "#   #       #       #   #", # y=7
        "#     #############     #", # y=8
        "#########################"  # y=9
    ]

    # --- Process the Maze ---

    walls: Set[Coord] = set()
    free_cells: List[Coord] = [] # Use a list for random.sample

    # Parse the ASCII maze string array
    for y, row in enumerate(maze_ascii):
        for x, char in enumerate(row):
            c = (x, y)
            if char == '#':
                walls.add(c)
            elif c not in start_positions:
                free_cells.append(c)
    
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
    
    # Place pellets randomly in the available free cells
    rng = random.Random()
    k_pellets = max(1, int(pellet_density * len(free_cells)))
    pellets = set(rng.sample(free_cells, k_pellets)) if k_pellets > 0 else set()

    return walls, pellets, pacman_start, ghostA_start, ghostB_start, ghostC_start