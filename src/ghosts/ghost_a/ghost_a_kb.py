from typing import Optional
from utils.types_utils import Coord, Percept, MOVES
import random

# --- State Definitions ---
STATE_PATROLLING = "PATROLLING"
STATE_CHASING = "CHASING"
STATE_PURSUING = "PURSUING"
STATE_INVESTIGATING = "INVESTIGATING"

class KnowledgeBaseA:
    """
    Implements the 4-state logic for Ghost A using a formal TELL/ASK.
    
    TELL:
        -Updates the KB's internal state and memory.
    ASK:
        - Runs the state machine, determines a goal, calculates a
        - safe move, and returns a single action string.
    """
    def __init__(self, patrol_points: Optional[list[Coord]] = None):
        # --- Internal State ---
        self.state: str = STATE_PATROLLING
        
        # --- Memory ---
        self.last_known_pacman_pos: Optional[Coord] = None
        self.last_known_direction: str = 'WAIT'
        self.investigation_direction: str = 'WAIT'
        
        # --- Percepts (Stored by TELL) ---
        self.my_pos: Coord = (0, 0)
        self.percepts: Percept = {}

    def _set_state(self, state: str):
        if self.state != state:
            # print(f"Ghost A: {self.state} -> {state}")
            self.state = state

    def tell(self, my_pos: Coord, pacman_pos: Optional[Coord], percepts: Percept):
        """
        Stores all new facts from the environment and updates the
        KB's internal state.
        """
        # Store current facts
        self.my_pos = my_pos
        self.percepts = percepts

        # === Run State Transition Logic ===
        
        # Rule 1: Can see Pac-Man
        if pacman_pos:
            self._set_state(STATE_CHASING)
            # Update last known direction
            if self.last_known_pacman_pos:
                dx = pacman_pos[0] - self.last_known_pacman_pos[0]
                dy = pacman_pos[1] - self.last_known_pacman_pos[1]
                if abs(dx) > abs(dy):
                    self.last_known_direction = 'RIGHT' if dx > 0 else 'LEFT'
                elif dy != 0:
                    self.last_known_direction = 'DOWN' if dy > 0 else 'UP'
            
            self.last_known_pacman_pos = pacman_pos
            return # State is set, ASK will handle the rest

        # Rule 2: Was chasing, now lost sight
        if self.state == STATE_CHASING:
            self._set_state(STATE_PURSUING)
            return

        # Rule 3: Arrived at last known spot
        if self.state == STATE_PURSUING and self.my_pos == self.last_known_pacman_pos:
            # Find possible "escape routes" for Pac-Man
            possible_moves = []
            opposite_dir = 'WAIT'
            if self.last_known_direction == 'UP': opposite_dir = 'DOWN'
            elif self.last_known_direction == 'DOWN': opposite_dir = 'UP'
            elif self.last_known_direction == 'LEFT': opposite_dir = 'RIGHT'
            elif self.last_known_direction == 'RIGHT': opposite_dir = 'LEFT'
            
            for move, (dx, dy) in MOVES.items():
                if move == 'WAIT' or move == opposite_dir:
                    continue
                check_pos = (self.my_pos[0] + dx, self.my_pos[1] + dy)
                if self.percepts.get(check_pos) != "WALL":
                    possible_moves.append(move)
            
            if possible_moves:
                self.investigation_direction = random.choice(possible_moves)
                self._set_state(STATE_INVESTIGATING)
            else:
                self._set_state(STATE_PATROLLING)
            return

        # Rule 4: Was investigating, hit a wall
        if self.state == STATE_INVESTIGATING:
            dx, dy = MOVES[self.investigation_direction]
            next_pos = (self.my_pos[0] + dx, self.my_pos[1] + dy)
            if self.percepts.get(next_pos) == "WALL":
                self._set_state(STATE_PATROLLING)
            return
            
        # Rule 5: Default to patrolling
        if self.state not in [STATE_CHASING, STATE_PURSUING, STATE_INVESTIGATING]:
            self._set_state(STATE_PATROLLING)

    def ask(self) -> str:
        """
        Runs inference on the current state and returns a
        single, safe action.
        """
        # 1. Get Goal based on current state
        goal = None
        if self.state == STATE_CHASING:
            goal = self.last_known_pacman_pos
        elif self.state == STATE_PURSUING:
            goal = self.last_known_pacman_pos
        elif self.state == STATE_INVESTIGATING:
            dx, dy = MOVES[self.investigation_direction]
            goal = (self.my_pos[0] + dx, self.my_pos[1] + dy)
        elif self.state == STATE_PATROLLING:

            possible_moves = []
            for move, (dx, dy) in MOVES.items():
                if move == 'WAIT': continue
                check_pos = (self.my_pos[0] + dx, self.my_pos[1] + dy)
                if self.percepts.get(check_pos) != "WALL":
                    possible_moves.append(move)
            
            if possible_moves:
                return random.choice(possible_moves)
            else:
                return 'WAIT' # Trapped
        
        if goal is None:
            # This should only be hit if state is PATROLLING
            return 'WAIT'

        # 2. Find greedy move towards goal
        move = 'WAIT'
        dx = goal[0] - self.my_pos[0]
        dy = goal[1] - self.my_pos[1]
        
        move_options = []
        if dx > 0: move_options.append('RIGHT')
        if dx < 0: move_options.append('LEFT')
        if dy > 0: move_options.append('DOWN')
        if dy < 0: move_options.append('UP')
        
        if not move_options and self.my_pos != goal:
            # Goal is not reachable by cardinal moves
            return 'WAIT'
        if not move_options:
            return 'WAIT' # We are at the goal

        # Prefer non-diagonal moves
        if abs(dx) > abs(dy):
            move = 'RIGHT' if dx > 0 else 'LEFT'
        else:
            move = 'DOWN' if dy > 0 else 'UP'
        
        # 3. Check for wall collision
        next_x = self.my_pos[0] + MOVES[move][0]
        next_y = self.my_pos[1] + MOVES[move][1]
        
        if self.percepts.get((next_x, next_y)) == "WALL":
            # Can't go this way, try other options
            if move in move_options:
                move_options.remove(move)
            
            for alt_move in move_options:
                alt_x = self.my_pos[0] + MOVES[alt_move][0]
                alt_y = self.my_pos[1] + MOVES[alt_move][1]
                if self.percepts.get((alt_x, alt_y)) != "WALL":
                    move = alt_move # Found a valid alternative
                    return move # Return safe move
            
            # All primary options are blocked, try anything
            all_moves = ['UP', 'DOWN', 'LEFT', 'RIGHT']
            random.shuffle(all_moves)
            for final_move in all_moves:
                fin_x = self.my_pos[0] + MOVES[final_move][0]
                fin_y = self.my_pos[1] + MOVES[final_move][1]
                if self.percepts.get((fin_x, fin_y)) != "WALL":
                    return final_move # Return *any* safe move
            
            return 'WAIT' # Completely trapped

        return move # Return chosen, safe move