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

class InRegion(Predicate):
    """Fact: InRegion(x, y, RegionID)"""
    def __init__(self, x: Term, y: Term, region: Term):
        super().__init__(x, y, region)
        self.x = x
        self.y = y
        self.region = region

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

class RegionPelletCount(Predicate):
    """Belief: RegionPelletCount(RegionID, N)"""
    def __init__(self, region: Term, count: Term):
        super().__init__(region, count)
        self.region = region
        self.count = count