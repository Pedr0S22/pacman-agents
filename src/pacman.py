from typing import Tuple
from environment import Environment, generate_maze
import os
import time

from ghosts.ghost import Ghost
from ghosts.ghost_a.ghost_a_kb import KnowledgeBaseA
from ghosts.ghost_b.ghost_b_kb import KnowledgeBaseB
from ghosts.ghost_c.ghost_c_kb import KnowledgeBaseC

Coord = Tuple[int, int]


def get_pressed_key() -> str:
    """Check if an arrow key or 'q' are pressed.
        Returns 'UP', 'DOWN', 'LEFT', 'RIGHT', 'QUIT', or None."""
    # Check OS type first
    if os.name == 'nt':
        # Windows solution
        try:
            import msvcrt
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                # Arrow key prefix
                if ch in [b'\x00', b'\xe0']:
                    ch2 = msvcrt.getch()
                    # Map to direction
                    if ch2 == b'H':
                        return 'UP'
                    elif ch2 == b'P':
                        return 'DOWN'
                    elif ch2 == b'M':
                        return 'RIGHT'
                    elif ch2 == b'K':
                        return 'LEFT'
                elif ch.decode('utf-8', errors='ignore').lower() == 'q':
                    return 'QUIT'
            return None
        except ImportError:
            return None


def run_game(
    env: Environment,
    sleep_s: float = 0.5
):
    """Run the Pac-Man game with keyboard controls."""
    action = "WAIT"

    while not env.victory and not env.game_over:

        key = get_pressed_key()
        if key is not None:
            action = key

        if action == 'QUIT':
            break

        env.step(action)

        print(env.render())
        print()
        time.sleep(sleep_s)


def run_pacman():
    """Game entry point: create a maze, instantiate the environment, run the game."""
    width, height = 25, 10
    walls, pellets, pacman_start, ghostA_start, ghostB_start, ghostC_start = generate_maze(w=width, h=height, pellet_density=0.6)

    kb_a = KnowledgeBaseA()
    kb_b = KnowledgeBaseB()
    kb_c = KnowledgeBaseC()

    ghost_a = Ghost(kb_a)
    ghost_b = Ghost(kb_b)
    ghost_c = Ghost(kb_c)

    env = Environment(
        width, height,
        walls=walls,
        pellets=pellets,
        pacman_start=pacman_start,
        ghostA_start=ghostA_start,
        ghostB_start=ghostB_start,
        ghostC_start=ghostC_start
    )

    run_game(env)


if __name__ == "__main__":
    run_pacman()
