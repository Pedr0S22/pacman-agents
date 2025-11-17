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
    Implements the 4-state logic for Ghost A.
    1. CHASE: Sees Pac-Man.
    2. PURSUE: Lost sight, moving to Pac-Man's last-known position.
    3. INVESTIGATE: Arrived at last-known position, now picking a new
        "escape route" to follow.
    4. PATROL: All else fails.
    """
    def __init__(self, patrol_points: Optional[list[Coord]] = None):
        # The agent's current state
        self.state: str = STATE_PATROLLING
        
        # --- Memory ---
        self.last_known_pacman_pos: Optional[Coord] = None
        self.last_known_direction: str = 'WAIT' # Pac-Man's vector
        self.investigation_direction: str = 'WAIT' # The *new* path to check
        
        # --- Patrol ---
        self.patrol_points: list[Coord] = patrol_points or [(1, 1), (1, 8), (23, 8), (23, 1)]
        self.patrol_index: int = 0

    def _set_state(self, state: str):
        if self.state != state:
            # print(f"Ghost A: {self.state} -> {state}") # Uncomment for debugging
            self.state = state
            
    def get_patrol_goal(self, my_pos: Coord) -> Coord:
        """Get the current patrol target."""
        goal = self.patrol_points[self.patrol_index]
        if my_pos == goal:
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
            goal = self.patrol_points[self.patrol_index]
        return goal

    def update_and_get_goal(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        percepts: Percept
    ) -> Coord:
        """
        This is the main "brain" of the agent.
        It updates its state and returns the correct goal.
        """
        
        # === RULE 1: CHASE (Highest Priority) ===
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
            return pacman_pos # Goal is Pac-Man himself

        # === (No Pac-Man in sight from here) ===
        
        # === RULE 2: PURSUE (Was chasing, now lost sight) ===
        if self.state == STATE_CHASING:
            self._set_state(STATE_PURSUING)
            # Goal is the last spot we saw him
            if self.last_known_pacman_pos:
                return self.last_known_pacman_pos

        # === RULE 3: INVESTIGATE (Arrived at last known spot) ===
        if self.state == STATE_PURSUING and my_pos == self.last_known_pacman_pos:
            # Your new logic: "decides one possible direction"
            possible_moves = []
            # Find opposite of Pac-Man's last vector (where we came from)
            opposite_dir = 'WAIT'
            if self.last_known_direction == 'UP': opposite_dir = 'DOWN'
            elif self.last_known_direction == 'DOWN': opposite_dir = 'UP'
            elif self.last_known_direction == 'LEFT': opposite_dir = 'RIGHT'
            elif self.last_known_direction == 'RIGHT': opposite_dir = 'LEFT'
            
            for move, (dx, dy) in MOVES.items():
                if move == 'WAIT' or move == opposite_dir:
                    continue
                
                check_pos = (my_pos[0] + dx, my_pos[1] + dy)
                if check_pos not in percepts or percepts.get(check_pos) != "WALL":
                    possible_moves.append(move)
            
            if possible_moves:
                self.investigation_direction = random.choice(possible_moves)
                self._set_state(STATE_INVESTIGATING)
            else:
                # No escape routes, give up and patrol
                self._set_state(STATE_PATROLLING)
                return self.get_patrol_goal(my_pos)

        # === RULE 4: INVESTIGATING (Following new direction) ===
        if self.state == STATE_INVESTIGATING:
            # Check for an obstacle
            dx, dy = MOVES[self.investigation_direction]
            next_pos = (my_pos[0] + dx, my_pos[1] + dy)
            
            if next_pos in percepts and percepts.get(next_pos) == "WALL":
                # Hit a wall, give up and patrol
                self._set_state(STATE_PATROLLING)
                return self.get_patrol_goal(my_pos)
            else:
                # Keep following this investigation path
                return next_pos

        # === RULE 5: PATROLLING (Default) ===
        self._set_state(STATE_PATROLLING)
        return self.get_patrol_goal(my_pos)