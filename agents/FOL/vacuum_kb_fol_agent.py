from vacuum_utils import Environment, Agent, run_vacuum
from fol_components import Constant, Variable, Predicate, LocationBasedPredicate, unify
from typing import Dict, Optional, Set, List
import random

class Position(LocationBasedPredicate):
    """Position(x, y) - the agent is at position (x, y)."""
    pass


class DirtAt(LocationBasedPredicate):
    """DirtAt(x, y) - there is dirt at position (x, y)."""
    pass


class Blocked(LocationBasedPredicate):
    """Blocked(x, y) - position (x, y) is blocked by obstacle or boundary."""
    pass


class KnowledgeBaseWithFOL:
    """Knowledge base using first-order logic with predicates and terms."""
    _DIRS = ['N', 'S', 'E', 'W']
    _MOVES = {'E': (1, 0), 'W': (-1, 0), 'S': (0, 1), 'N': (0, -1)}

    def __init__(self, env: Environment,
                rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.w, self.h = env.w, env.h

        # Store ground predicates (predicates with only constants)
        self.facts: Set[Predicate] = set()

    def tell(self, predicate: Predicate) -> None:
        """Add a ground predicate into the knowledge base."""
        if not predicate.is_ground():
            raise ValueError("Can only tell ground predicates (no variables)")

        # Special handling for Position: only one position can be true at a time
        if isinstance(predicate, Position):
            self.facts = {f for f in self.facts if not isinstance(f, Position)}

        self.facts.add(predicate)

    def get_unifications(self, query: Predicate) -> List[Dict[str, Constant]]:
        """Query the KB and return all unifications that satisfy the query.

        Args:
            query: A predicate that may contain variables

        Returns:
            List of substitutions (variable bindings) that satisfy the query
        """
        results = []

        for fact in self.facts:
            if type(fact) == type(query):
                substitution = unify(query, fact)
                if substitution is not None:
                    results.append(substitution)

        return results

    def ask(self) -> str:
        """Return an action based on the knowledge base.

        Priority: vacuum if dirt at current position, else move to
        non-blocked direction (randomized), else wait.
        """
        pos_query = Position(Variable('X'), Variable('Y'))
        pos_results = self.get_unifications(pos_query)

        if not pos_results:
            return "WAIT"

        x_val = pos_results[0][Variable('X')].value
        y_val = pos_results[0][Variable('Y')].value

        dirt_query = DirtAt(Constant(x_val), Constant(y_val))
        if self.get_unifications(dirt_query):
            self.facts.discard(dirt_query)
            return "VACUUM"

        self.rng.shuffle(self._DIRS)
        for d in self._DIRS:
            dx, dy = self._MOVES[d]
            nx, ny = x_val + dx, y_val + dy

            if 0 <= nx < self.w and 0 <= ny < self.h:
                blocked_query = Blocked(Constant(nx), Constant(ny))
                if not self.get_unifications(blocked_query):
                    return d

        return "WAIT"


class KnowledgeBaseAgent(Agent):
    """Agent that maintains a knowledge base and acts on it."""
    _MOVES = {'E': (1, 0), 'W': (-1, 0), 'S': (0, 1), 'N': (0, -1)}

    def __init__(self, env: Environment,
                rng: Optional[random.Random] = None):
        super(KnowledgeBaseAgent, self).__init__(rng)
        self.kb = KnowledgeBaseWithFOL(env, rng)

    def _store_facts(self, p: Dict, env: Environment):
        """Extract percept/environment facts and store them in the KB."""
        x, y = p["pos"][0], p["pos"][1]

        self.kb.tell(Position(Constant(x), Constant(y)))

        if p["dirt_here"]:
            self.kb.tell(DirtAt(Constant(x), Constant(y)))

        for _, (dx, dy) in self._MOVES.items():
            if env.blocked((x + dx, y + dy)):
                self.kb.tell(Blocked(Constant(x + dx), Constant(y + dy)))

    def act(self, percept: Dict, env: Environment) -> str:
        """Store percept facts then query KB for next action.
            Returns action strings understood by `Environment.step`."""
        self._store_facts(percept, env)
        return self.kb.ask()


if __name__ == "__main__":
    run_vacuum(KnowledgeBaseAgent)
