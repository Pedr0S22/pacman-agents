from utils.fol_components import Term, Predicate, Constant, LocationBasedPredicate

# Map Topology Predicates

class LearnedWall(LocationBasedPredicate):
    """Fact: LearnedWall(x, y)"""
    pass

class LearnedSafe(LocationBasedPredicate):
    """Fact: LearnedSafe(x, y)"""
    pass

class PacmanPos(LocationBasedPredicate):
    """Belief: PacmanPos(x, y)"""
    pass


# Dynamic Belief Predicates

class VisitedAtTime(Predicate):
    """Fact: VisitedAtTime(x, y, t) - History tracking"""
    def __init__(self, x: Term, y: Term, t: Term):
        super().__init__(x, y, t)
        self.x = x
        self.y = y
        self.t = t

class EscapeState(Predicate):
    """
    Fact: EscapeState(TargetX, TargetY, StartTime)
    Persists the commitment to run to a specific target to break a loop.
    """
    def __init__(self, tx: Term, ty: Term, start_time: Term):
        super().__init__(tx, ty, start_time)
        self.tx = tx
        self.ty = ty
        self.start_time = start_time


class LastPos(Predicate):
    """Stores the last position of a ghost to avoid bouncing."""
    def __init__(self, ghost_id: Constant, x: Constant, y: Constant):
        super().__init__("LastPos", ghost_id, x, y)


class UnreachableGoal(Predicate):
    """Fact: UnreachableGoal(x,y,timestamp)
    Goals become reachable again after time passes."""
    def __init__(self, x: Term, y: Term, timestamp: Term):
        super().__init__(x, y, timestamp)
        self.x = x
        self.y = y
        self.timestamp = timestamp


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