from utils.fol_components import Term, Predicate, LocationBasedPredicate

# Map Topology Predicates

class LearnedWall(LocationBasedPredicate):
    """Fact: LearnedWall(x, y)"""
    pass

class LearnedSafe(LocationBasedPredicate):
    """Fact: LearnedSafe(x, y)"""
    pass

class SawPelletAt(LocationBasedPredicate):
    """Fact: SawPelletAt(x, y) - The initial state"""
    pass

class IsJunction(LocationBasedPredicate):
    """Fact: IsJunction(x, y) - Inferred from map"""
    pass

class IsTunnel(LocationBasedPredicate):
    """Fact: IsTunnel(x, y) - Inferred from map"""
    pass


class PelletCountNear(Predicate):
    """Belief: PelletCountNear(Jx, Jy, N)
    "I believe the junction at (Jx, Jy) is a gateway to N pellets."
    """
    def __init__(self, jx: Term, jy: Term, count: Term):
        super().__init__(jx, jy, count)
        self.jx = jx
        self.jy = jy
        self.count = count


# --- Dynamic Belief Predicates ---

class PacmanPos(LocationBasedPredicate):
    """Belief: PacmanPos(x, y)"""
    pass

class PacmanVector(Predicate):
    """Belief: PacmanVector(dx, dy)"""
    def __init__(self, dx: Term, dy: Term):
        super().__init__(dx, dy)
        self.dx = dx
        self.dy = dy

class GhostPos(Predicate):
    """Belief: GhostPos(AgentID, x, y)"""
    def __init__(self, agent_id: Term, x: Term, y: Term):
        super().__init__(agent_id, x, y)
        self.agent_id = agent_id
        self.x = x
        self.y = y