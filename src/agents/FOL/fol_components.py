from typing import Optional, Dict

class Term:
    """Base class for FOL terms (constants or variables)."""
    pass


class Constant(Term):
    """A constant term in FOL (e.g., a specific coordinate value)."""
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Constant) and self.value == other.value

    def __hash__(self):
        return hash(('Constant', self.value))


class Variable(Term):
    """A variable term in FOL (e.g., X, Y)."""
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name

    def __hash__(self):
        return hash(('Variable', self.name))


class Predicate:
    """Base class for FOL predicates."""
    def __init__(self, *args: Term):
        self.args = args

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.args == other.args)

    def __hash__(self):
        return hash((type(self).__name__, self.args))

    def is_ground(self) -> bool:
        """Check if the predicate contains only constants (no variables)."""
        return all(isinstance(arg, Constant) for arg in self.args)


class LocationBasedPredicate(Predicate):
    """Base class for predicates that refer to a location (x, y)."""
    def __init__(self, x: Term, y: Term):
        super().__init__(x, y)
        self.x = x
        self.y = y


def unify(query: Predicate, fact: Predicate) -> Optional[Dict[Variable, Constant]]:
    """Unify a query predicate with a ground fact.

    Args:
        query: A predicate that may contain variables
        fact: A ground predicate (contains only constants)

    Returns:
        Substitution dict mapping variables to constants if unification succeeds,
        None otherwise.
    """
    if type(query) != type(fact):
        return None

    if len(query.args) != len(fact.args):
        return None

    substitution = {}

    for q_arg, f_arg in zip(query.args, fact.args):
        if isinstance(q_arg, Constant):
            # Constant in query must match constant in fact
            if not isinstance(f_arg, Constant) or q_arg.value != f_arg.value:
                return None
        elif isinstance(q_arg, Variable):
            # Variable in query binds to constant in fact
            if not isinstance(f_arg, Constant):
                return None
            # Check consistency with existing bindings
            if q_arg in substitution:
                if substitution[q_arg].value != f_arg.value:
                    return None
            else:
                substitution[q_arg] = f_arg

    return substitution
