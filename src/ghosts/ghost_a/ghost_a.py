from typing import Tuple, List, Optional
from utils.types_utils import Coord, Percept, MOVES
from ghost_a_kb import KnowledgeBaseA
import random

class GhostA:
    """
    Ghost A: The "Pursuer" (PL Agent)
    - This class is now a "dumb" shell.
    - All logic is inside KnowledgeBaseA.
    - This agent just asks the KB for a goal, then figures out
        how to move there.
    """
    def __init__(self, patrol_points: Optional[list[Coord]] = None):
        self.kb = KnowledgeBaseA(patrol_points)
        self.goal: Optional[Coord] = None
        self.last_move: str = 'WAIT'

    def get_next_move(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ) -> str:
        
        # --- 1. Get Goal from KB ---
        # The KB's state machine runs and tells us where to go.
        self.goal = self.kb.update_and_get_goal(
            my_pos,
            pacman_pos,
            percepts
        )
        
        if self.goal is None:
            return 'WAIT'
            
        # --- 2. Determine Move from Goal ---
        # Ghost A is dumb, no pathfinder. It just moves
        # greedily towards the goal.
        
        move = 'WAIT'
        dx = self.goal[0] - my_pos[0]
        dy = self.goal[1] - my_pos[1]
        
        # Prioritize non-stuck moves
        move_options = []
        if dx > 0: move_options.append('RIGHT')
        if dx < 0: move_options.append('LEFT')
        if dy > 0: move_options.append('DOWN')
        if dy < 0: move_options.append('UP')
        
        if not move_options:
            # We are at the goal
            self.last_move = 'WAIT'
            return 'WAIT'

        # Prefer non-diagonal moves
        if abs(dx) > abs(dy):
            move = 'RIGHT' if dx > 0 else 'LEFT'
        else:
            move = 'DOWN' if dy > 0 else 'UP'

        # --- 3. Avoid Walls (Simple Collision Avoidance) ---
        next_x = my_pos[0] + MOVES[move][0]
        next_y = my_pos[1] + MOVES[move][1]
        
        if (next_x, next_y) in percepts and percepts.get((next_x, next_y)) == "WALL":
            # Can't go this way, try other options
            move_options.remove(move)
            
            # Check remaining options
            for alt_move in move_options:
                alt_x = my_pos[0] + MOVES[alt_move][0]
                alt_y = my_pos[1] + MOVES[alt_move][1]
                if (alt_x, alt_y) not in percepts or percepts.get((alt_x, alt_y)) != "WALL":
                    move = alt_move # Found a valid alternative
                    break
            else:
                # All primary options are blocked, try anything
                # (including going backwards)
                all_moves = ['UP', 'DOWN', 'LEFT', 'RIGHT']
                random.shuffle(all_moves)
                for final_move in all_moves:
                    fin_x = my_pos[0] + MOVES[final_move][0]
                    fin_y = my_pos[1] + MOVES[final_move][1]
                    if (fin_x, fin_y) not in percepts or percepts.get((fin_x, fin_y)) != "WALL":
                        move = final_move
                        break
                else:
                    move = 'WAIT' # Completely trapped

        self.last_move = move
        return move