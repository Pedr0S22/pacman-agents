from typing import Tuple, Set, Dict, Iterable, Optional, List
from abc import ABC, abstractmethod
import argparse
import random
import time

Coord = Tuple[int, int]


class Environment:
    """Grid world representing the vacuum environment.

    Attributes:
        w, h: grid width and height
        obstacles: set of blocked coordinates
        _init_dirt: initial dirt locations (kept for resets)
        dock: docking coordinate where robot can recharge
        max_battery: maximum battery capacity
        rng: random number generator (for reproducibility)
        pos: current robot position
        dirt: current dirt locations
        battery: current battery level
        time: elapsed time steps
        cleaned: number of cleaned cells so far
        action_blocked: whether last move was blocked by obstacle/bounds
    """
    def __init__(
        self, w: int = 8, h: int = 6,
        obstacles: Set[Coord] | None = None,
        dirt: Set[Coord] | None = None,
        dock: Coord = (0, 0),
        seed: Optional[int] = None,
        max_battery: int = 200,
    ):
        self.w, self.h = w, h
        self.obstacles: Set[Coord] = set(obstacles or set())
        self._init_dirt: Set[Coord] = set(dirt or set())
        self.dock: Coord = dock
        self.max_battery = max_battery
        self.rng = random.Random(seed)

        self.pos: Coord = self.dock
        self.dirt: Set[Coord] = set(self._init_dirt)
        self.battery: int = max_battery
        self.time: int = 0
        self.cleaned: int = 0
        self.action_blocked: bool = False

    def reset(self, start: Optional[Coord] = None, 
              battery: Optional[int] = None):
        """Reset the environment to its initial state.

        Args:
            start: optional starting coordinate for the robot (defaults to dock)
            battery: optional starting battery (defaults to max_battery)
        """
        self.pos = start if start is not None else self.dock
        self.dirt = set(self._init_dirt)
        self.battery = self.max_battery if battery is None else battery
        self.time = 0
        self.cleaned = 0
        self.action_blocked = False

    def in_bounds(self, c: Coord) -> bool:
        """Return True if coordinate `c` is within grid bounds."""
        x, y = c
        return 0 <= x < self.w and 0 <= y < self.h

    def blocked(self, c: Coord) -> bool:
        """Return True if coordinate `c` is blocked by bounds or an obstacle."""
        return (not self.in_bounds(c)) or (c in self.obstacles)

    def neighbors(self, c: Coord) -> Iterable[Tuple[Coord, str]]:
        """Yield neighboring free coordinates and their action labels.

        Returns iterable of (coord, action) for N/E/S/W moves that are not blocked.
        """
        allowed = []
        for dx, dy, a in ((1, 0, 'E'), (-1, 0, 'W'), (0, 1, 'S'), (0, -1, 'N')):
            nc = (c[0] + dx, c[1] + dy)
            if not self.blocked(nc):
                allowed.append((nc, a))
        return allowed
        
    def sense(self) -> Dict:
        """Return a percept dictionary describing the current environment state.

        Keys: pos, dirt_here, at_dock, battery, time, action_blocked
        """
        return dict(
            pos=self.pos,
            dirt_here=(self.pos in self.dirt),
            at_dock=(self.pos == self.dock),
            battery=self.battery,
            time=self.time,
            action_blocked=self.action_blocked
        )

    def step(self, action: str):
        """Advance the environment one step given an `action` string.

        Supported actions:
            - 'N','S','E','W' to move
            - 'VACUUM' to clean current cell
            - 'WAIT' to recharge at dock

        Effects: updates `time`, `battery`, `pos`, `dirt`, `cleaned`, and
        sets `action_blocked` if a movement is blocked.
        """
        if self.battery <= 0:
            return
        self.time += 1
        self.battery -= 1
        self.action_blocked = False

        # Recharge if at dock and action is WAIT
        if action == "WAIT" and self.pos == self.dock:
            self.battery = min(self.battery + 5, self.max_battery)

        if action == "VACUUM":
            if self.pos in self.dirt:
                self.dirt.remove(self.pos)
                self.cleaned += 1
            return

        moves = {'E': (1, 0), 'W': (-1, 0), 'S': (0, 1), 'N': (0, -1)}
        if action in moves:
            dx, dy = moves[action]
            nx, ny = self.pos[0] + dx, self.pos[1] + dy
            if self.blocked((nx, ny)):
                self.action_blocked = True
            else:
                self.pos = (nx, ny)

    def render(self) -> str:
        """Return a multi-line string visualising the grid.

        Legend: 'R' robot, 'D' dock, '#' obstacle, '*' dirt, '.' empty
        """
        buf: List[str] = []
        buf.append(f"t={self.time} | battery={self.battery}/{self.max_battery} | "
                   + f"cleaned={self.cleaned} | remaining={len(self.dirt)}")
        
        for y in range(self.h):
            row = []
            for x in range(self.w):
                c = (x, y)
                if c == self.pos and c == self.dock:
                    ch = 'R'  # Robot on dock
                elif c == self.pos:
                    ch = 'R'
                elif c in self.obstacles:
                    ch = '#'
                elif c == self.dock:
                    ch = 'D'
                elif c in self.dirt:
                    ch = '*'
                else:
                    ch = '.'
                row.append(ch)
            buf.append(''.join(row))

        return '\n'.join(buf)


class Agent(ABC):
    """Generic base class for agents.

    Attributes:
        rng: random number generator (for reproducibility)
    """
    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()

    @abstractmethod
    def act(self, percept: Dict, env: Environment) -> str:
        """Decide an action given the current `percept` and `env`.

        Must return an action string understood by `Environment.step`.
        """
        pass
        

def generate_world(
    w: int, h: int,
    obstacle_density: float = 0.1,
    dirt_density: float = 0.1,
    seed: Optional[int] = None,
    dock: Coord = (0, 0),
) -> Tuple[Set[Coord], Set[Coord]]:
    """Generate obstacle and dirt sets for a random world.

    Ensures the `dock` is not completely surrounded by obstacles.
    Returns: (obstacles_set, dirt_set)
    """
    rng = random.Random(seed)
    all_cells = [(x, y) for y in range(h) for x in range(w)]
    if dock in all_cells:
        all_cells.remove(dock)

    # generate obstacles
    k_obs = int(obstacle_density * len(all_cells))
    obstacles = set(rng.sample(all_cells, k_obs)) if k_obs > 0 else set()
    
    # ensure dock is not isolated: clear its neighbors if blocked
    def neighbors_4(c: Coord) -> Iterable[Tuple[Coord, str]]:
        neighbors = []
        for dx, dy, a in ((1, 0, 'E'), (-1, 0, 'W'), (0, 1, 'S'), (0, -1, 'N')):
            neighbors.append(((c[0] + dx, c[1] + dy), a))
        return neighbors
        
    for (nx, ny), _ in neighbors_4(dock):
        if (nx, ny) in obstacles:
            obstacles.remove((nx, ny))

    # generate dirt
    free_cells = [c for c in all_cells if c not in obstacles]
    k_dirt = max(1, int(dirt_density * len(free_cells)))
    dirt = set(rng.sample(free_cells, k_dirt)) if k_dirt > 0 else set()

    return obstacles, dirt


def run_simulation(
    env: Environment,
    agent: Agent,
    steps: int = 200,
    sleep_s: float = 0.0,
) -> Dict[str, int]:
    """Run the agent in `env` for up to `steps` steps and return metrics.

    Prints a rendering each step. Returns a dict with steps, cleaned,
    remaining, battery, and bumps (blocked moves count).
    """
    bumps = 0
    for _ in range(steps):
        percept = env.sense()
        action = agent.act(percept, env)
        env.step(action)
        if env.action_blocked:
            bumps += 1

        print(env.render())
        print()
        if sleep_s > 0:
            time.sleep(sleep_s)

        if not env.dirt or env.battery <= 0:
            break

    return dict(
        steps=env.time,
        cleaned=env.cleaned,
        remaining=len(env.dirt),
        battery=env.battery,
        bumps=bumps
    )


def run_vacuum(agent_type: type[Agent]):
    """CLI entry point: create a world, instantiate an agent, run simulation.

    `agent_type` should be a class deriving from `Agent`.
    """
    parser = argparse.ArgumentParser(description="Vacuum Cleaner Agent Simulator")
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=6)
    parser.add_argument("--obstacle-density", type=float, default=0.1, help="Fraction of cells that are obstacles (0..1).")
    parser.add_argument("--dirt-density", type=float, default=0.1, help="Fraction of free cells that contain dirt initially (0..1).")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--battery", type=int, default=100)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between rendered steps.")

    args = parser.parse_args()

    w, h = args.width, args.height
    dock = (0, 0)
    obstacles, dirt = generate_world(
        w, h,
        obstacle_density=args.obstacle_density,
        dirt_density=args.dirt_density,
        seed=args.seed,
        dock=dock
    )

    env = Environment(w, h, obstacles, dirt, dock=dock, 
                      seed=args.seed, max_battery=max(args.battery, 1))
    env.reset(battery=args.battery)
    agent = agent_type(env, random.Random(args.seed))

    print(env.render() + "\n")

    result = run_simulation(
        env, agent,
        steps=args.steps,
        sleep_s=args.sleep
    )

    print(f"Performance Measures")
    print(f"Grid: {w}x{h} | Obstacles: {len(obstacles)} | Initial Dirt: {len(dirt)} | Seed: {args.seed}")
    print(f"Steps: {result['steps']} | Cleaned: {result['cleaned']} | Remaining: {result['remaining']}")
    print(f"Battery Left: {result['battery']} / {env.max_battery} | Bumps: {result['bumps']}")
