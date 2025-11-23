from typing import Optional, Set, List, Tuple
from utils.types_utils import Coord, Percept, MOVES
from ghosts.KB import KnowledgeBase
import random

# State Definitions
STATE_PATROLLING = "PATROLLING"
STATE_CHASING = "CHASING"
STATE_PURSUING = "PURSUING"
STATE_INVESTIGATING = "INVESTIGATING"

class KnowledgeBaseA(KnowledgeBase):
    """
    KB for Ghost A.
    Logic: Model-Based Reflex Agent using Propositional Logic.
    
    - Maintains a internal model (grid) of propositions.
    - 'tell' updates the truth value of propositions.
    - 'ask' queries these truth values to derive actions.
    """

    def __init__(self):
        # --- Internal State ---
        
        # Proposition: Wall_x_y is True if (x,y) is in self.walls
        self.walls: Set[Coord] = set()
        
        # Proposition: Safe_x_y is True if (x,y) is known safe
        self.safe_tiles: Set[Coord] = set()
        
        # State Propositions (Only one is True at a time)
        self.current_state: str = STATE_PATROLLING
        
        # Beliefs (Memory Propositions)
        self.last_known_pacman: Optional[Coord] = None
        self.last_move: str = 'WAIT'
        self.investigation_target: Optional[Coord] = None
        
        # Percept Propositions (Updated every turn)
        self.my_pos: Coord = (0, 0)
        self.see_pacman: bool = False
        self.pacman_pos_percept: Optional[Coord] = None

    def tell(
        self,
        my_pos: Coord,
        pacman_pos: Optional[Coord],
        other_ghost_pos: List[Tuple[str, Coord]],
        percepts: Percept
    ):
        """
        Updates the Truth Value of propositions based on percepts.
        """
        
        # Proposition: MyPos_x_y is True
        self.my_pos = my_pos

        # Map Propositions
        # Proposition: For all (x,y) in Percepts: Percept(x,y)=WALL <=> Wall_x_y
        for pos, item in percepts.items():
            if item == "WALL":
                self.walls.add(pos)
                self.safe_tiles.discard(pos)
            else:
                # Proposition: not Wall_x_y => Safe_x_y
                self.safe_tiles.add(pos)

        # Pacman Propositions
        # Proposition: SeePacman <=> (pacman_pos is not None)
        self.pacman_pos_percept = pacman_pos
        self.see_pacman = (pacman_pos is not None)

        # --- State Transition Logic (PL Rules) ---
        self._update_state_logic()

    def _update_state_logic(self) -> None:
        """
        Applies State Transition Rules (P => Q).
        """
        # Rule 1: Detection
        # Proposition: SeePacman => State_Chasing
        if self.see_pacman:
            self.current_state = STATE_CHASING
            self.last_known_pacman = self.pacman_pos_percept
            return

        # Rule 2: Lost Sight (Persistence)
        # Proposition: State_Chasing ^ not SeePacman => State_Pursuing
        if self.current_state == STATE_CHASING and not self.see_pacman:
            self.current_state = STATE_PURSUING
            return
        
        # Rule 3: Arrival at Last Known Location
        # Proposition: State_Pursuing ^ (MyPos == LastKnownPacman) => State_Investigating
        if self.current_state == STATE_PURSUING and self.my_pos == self.last_known_pacman:
            self.current_state = STATE_INVESTIGATING
            # Select a valid neighbor to investigate that isn't a wall
            # Exists n in Neighbors(MyPos): Safe_n => InvestigationTarget = n
            options = [n for n in self._get_neighbors(self.my_pos) if n not in self.walls]
            if options:
                self.investigation_target = random.choice(options)
            else:
                self.current_state = STATE_PATROLLING
            return

        # Rule 4: Finished Investigating
        # Proposition: State_Investigating ^ (MyPos == InvestigationTarget) => State_Patrolling
        # Proposition: State_Investigating ^ Wall(InvestigationTarget) => State_Patrolling
        if self.current_state == STATE_INVESTIGATING:
            if self.my_pos == self.investigation_target:
                self.current_state = STATE_PATROLLING
            elif self.investigation_target in self.walls:
                self.current_state = STATE_PATROLLING
            return

    def ask(self) -> str:
        """
        Queries the internal model to decide the action.
        Returns action string.
        """
        action = 'WAIT'

        # Query 1: Chasing Logic
        # Proposition: State_Chasing => MoveTowards(LastKnownPacman)
        if self.current_state == STATE_CHASING:
            action = self._smart_move(self.last_known_pacman)

        # Query 2: Pursuing Logic
        # Proposition: State_Pursuing => MoveTowards(LastKnownPacman)
        elif self.current_state == STATE_PURSUING:
            action = self._smart_move(self.last_known_pacman)

        # Query 3: Investigating Logic
        # Proposition: State_Investigating => MoveTowards(InvestigationTarget)
        elif self.current_state == STATE_INVESTIGATING:
            action = self._smart_move(self.investigation_target)

        # Query 4: Patrolling Logic (Default)
        # Proposition: State_Patrolling => PatrolMove()
        else: # PATROLLING
            action = self._get_patrol_move()

        self.last_move = action
        return action

        
    # --- Internal Logic Helpers ---


    def _get_neighbors(self, pos: Coord) -> List[Coord]:
        """Helper to get adjacent coordinates."""
        x, y = pos
        return [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]

    def _smart_move(self, target: Coord) -> str:
        """
        Greedy movement towards target.
        Logic: Minimize Distance(MyPos, Target) s.t. not Wall(NextPos)
        """
        if not target: return 'WAIT'
        
        # Determine desired axes
        dx = target[0] - self.my_pos[0]
        dy = target[1] - self.my_pos[1]
        
        candidates = []
        # Prioritize axis with larger distance
        if abs(dx) >= abs(dy):
            candidates.append('RIGHT' if dx > 0 else 'LEFT')
            if dy != 0: candidates.append('DOWN' if dy > 0 else 'UP')
        else:
            candidates.append('DOWN' if dy > 0 else 'UP')
            if dx != 0: candidates.append('RIGHT' if dx > 0 else 'LEFT')
            
        # Add remaining moves as fallback
        for m in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
            if m not in candidates: candidates.append(m)

        # Check Safety (Proposition: not Wall_next)
        for move in candidates:
            mx, my = MOVES[move]
            next_pos = (self.my_pos[0] + mx, self.my_pos[1] + my)
            if next_pos not in self.walls:
                return move
                
        return 'WAIT'

    def _get_patrol_move(self) -> str:
        """
        Patrol Logic with Momentum.
        """
        # 1. Identify Valid Moves (Proposition: not Wall_next)
        valid_moves = []
        reverse_move = self._get_reverse(self.last_move)

        for move, (dx, dy) in MOVES.items():
            if move == 'WAIT': continue
            next_pos = (self.my_pos[0] + dx, self.my_pos[1] + dy)
            if next_pos not in self.walls:
                valid_moves.append(move)

        if not valid_moves:
            return 'WAIT'

        # 2. Apply Momentum Logic
        # Formal: Valid(LastMove) => Action(LastMove)
        if self.last_move in valid_moves:
            return self.last_move

        # 3. Handle Junctions/Corners (Jitter Fix)
        # Logic: If stuck, choose Random from Valid \ {Reverse}
        # (Unless dead end, then Reverse is allowed)
        non_reverse_moves = [m for m in valid_moves if m != reverse_move]
        random.shuffle(non_reverse_moves)
        
        if non_reverse_moves:
            return random.choice(non_reverse_moves)
        
        # Dead end: Only reverse is possible
        return valid_moves[0]

    def _get_reverse(self, move: str) -> str:
        opposites = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT', 'WAIT': 'WAIT'}
        return opposites.get(move, 'WAIT')