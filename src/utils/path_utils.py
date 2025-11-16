from typing import Set, List, Optional
from collections import deque
from types_utils import Coord, MOVES

def get_neighbors(pos: Coord) -> List[Coord]:
    """Gets the 4 adjacent neighbors of a coordinate."""
    x, y = pos
    return [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]

def bfs_pathfinder(
    start_pos: Coord,
    goal_pos: Coord,
    # The set of tiles the agent knows are safe to traverse.
    # This is crucial for agents B and C who must learn the map.
    safe_tiles: Set[Coord]
) -> Optional[List[Coord]]:
    """
    Finds the shortest path from start to goal using Breadth-First Search (BFS).
    Only searches tiles within the provided 'safe_tiles' set.
    """
    if start_pos == goal_pos:
        return [start_pos]

    queue = deque([(start_pos, [start_pos])])  # (position, path_list)
    visited = {start_pos}

    while queue:
        current_pos, path = queue.popleft()

        for neighbor in get_neighbors(current_pos):
            if neighbor == goal_pos:
                return path + [neighbor]  # Path found

            if neighbor in safe_tiles and neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    
    return None # No path found

def get_move_from_path(
    current_pos: Coord,
    path: List[Coord]
) -> str:
    """
    Determines the move ('UP', 'DOWN', etc.) from the current position
    to the next step in the path.
    """
    if not path or len(path) < 2:
        return 'WAIT'

    cx, cy = current_pos
    nx, ny = path[1]  # The next step
    
    dx, dy = nx - cx, ny - cy

    for move, (mdx, mdy) in MOVES.items():
        if (dx, dy) == (mdx, mdy):
            return move
            
    return 'WAIT'

def find_nearest_coord(
    start_pos: Coord,
    target_coords: Set[Coord],
    safe_tiles: Set[Coord]
) -> Optional[Coord]:
    """
    Finds the coordinate in 'target_coords' that is closest to 'start_pos'
    by path distance, using only 'safe_tiles'.
    """
    if start_pos in target_coords:
        return start_pos
    
    if not target_coords or not safe_tiles:
        return None

    queue = deque([start_pos])
    visited = {start_pos}

    while queue:
        current_pos = queue.popleft()
        
        for neighbor in get_neighbors(current_pos):
            if neighbor in target_coords:
                return neighbor  # Found the closest target
            
            if neighbor in safe_tiles and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return None # No reachable target