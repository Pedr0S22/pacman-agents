from typing import Tuple, Dict, Set, List, Optional

# Coordinate type for all grid positions
Coord = Tuple[int, int]

# Percept Types
# A percept is a dictionary mapping a coordinate to what the ghost sees there.
Percept = Dict[Coord, str]

# Move/Direction Definitions
MOVES = {
    'UP': (0, -1),
    'DOWN': (0, 1),
    'LEFT': (-1, 0),
    'RIGHT': (1, 0),
    'WAIT': (0, 0)
}
DIRECTIONS = list(MOVES.keys())