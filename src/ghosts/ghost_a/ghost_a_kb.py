from typing import Optional, List, Tuple
from utils.types_utils import Coord, Percept, MOVES
from ghosts.KB import KnowledgeBase
import random

# --- State Definitions ---
STATE_PATROLLING = "PATROLLING"
STATE_CHASING = "CHASING"
STATE_PURSUING = "PURSUING"
STATE_INVESTIGATING = "INVESTIGATING"

class KnowledgeBaseA(KnowledgeBase):
    """
    Implements the 4-state logic for Ghost A using a formal TELL/ASK.
    
    TELL:
        -Updates the KB's internal state and memory.
    ASK:
        - Runs the state machine, determines a goal, calculates a
        - safe move, and returns a single action string.
    """
    def __init__(self):
        # --- Internal State ---
        self.state: str = STATE_PATROLLING

        # --- Memory ---
        self.last_known_pacman_pos: Optional[Coord] = None
        self.last_known_direction: str = 'WAIT'
        self.investigation_direction: str = 'WAIT'
        self.patrol_direction: str = 'WAIT'
        
        # --- Percepts (Stored by TELL) ---
        self.my_pos: Coord = (0, 0)
        self.percepts: Percept = {}

    def _set_state(self, state: str):
        if self.state != state:
            # print(f"Ghost A: {self.state} -> {state}")
            self.state = state

    def tell(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ):
        """
        Stores all new facts from the environment and updates the
        KB's internal state.
        """
        # (Ghost A ignores other_ghost_pos, but it must accept the arg)
        
        # Store current facts
        self.my_pos = my_pos
        self.percepts = percepts
        
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
            # 1. Check if current patrol direction is valid
            if self.patrol_direction != 'WAIT':
                dx, dy = MOVES[self.patrol_direction]
                next_pos = (self.my_pos[0] + dx, self.my_pos[1] + dy)
                if self.percepts.get(next_pos) != "WALL":
                    return self.patrol_direction # Keep going!
            
            # 2. If invalid or waiting, pick a new valid direction
            possible_moves = []
            for move, (dx, dy) in MOVES.items():
                if move == 'WAIT': continue
                check_pos = (self.my_pos[0] + dx, self.my_pos[1] + dy)
                if self.percepts.get(check_pos) != "WALL":
                    possible_moves.append(move)
            
            if possible_moves:
                # Pick new direction and save it
                self.patrol_direction = random.choice(possible_moves)
                return self.patrol_direction
            return 'WAIT'

        if goal is None: return 'WAIT'

        # --- Smart Chase (Wall Following Heuristic) ---
        
        # Calculate ideal vector
        dx = goal[0] - self.my_pos[0]
        dy = goal[1] - self.my_pos[1]
        
        # Prioritize Main Axis, then Perpendicular Axis
        primary_moves = []
        if abs(dx) >= abs(dy):
            primary_moves.append('RIGHT' if dx > 0 else 'LEFT')
            if dy != 0: primary_moves.append('DOWN' if dy > 0 else 'UP')
        else:
            primary_moves.append('DOWN' if dy > 0 else 'UP')
            if dx != 0: primary_moves.append('RIGHT' if dx > 0 else 'LEFT')

        # Try primary moves first
        for move in primary_moves:
            mx, my = MOVES[move]
            check = (self.my_pos[0] + mx, self.my_pos[1] + my)
            if self.percepts.get(check) != "WALL":
                return move
        
        # If blocked, try Perpendicular moves (Wall Following logic)
        # i.e., if I want to go RIGHT but can't, try UP or DOWN
        all_moves = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        for move in all_moves:
            if move in primary_moves: continue # Already checked
            mx, my = MOVES[move]
            check = (self.my_pos[0] + mx, self.my_pos[1] + my)
            if self.percepts.get(check) != "WALL":
                return move # Take the escape route
        
        return 'WAIT'