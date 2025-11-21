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

def handle_death_pause(env: Environment, sleep_s: float):
    """Handles the visual pause and respawn when Pac-Man dies."""
    # Clear and Render (Show the collision)
    if os.name == 'nt': os.system('cls')
    print(env.render())
    
    # Print Message
    print(f"\nPac-Man Became a Ghost Snack! 👻\nLives Left: {env.lives}")
    print("Get Ready!\n")
    time.sleep(sleep_s * 6) # Pause longer for impact
    
    # Respawn Ghosts
    if not env.game_over:
        env.respawn_ghosts()

def run_game(
    env: Environment,
    ghost_a: Ghost,
    ghost_b: Ghost,
    ghost_c: Ghost,
    sleep_s: float = 0.5
):
    """Run the Pac-Man game with keyboard controls."""
    pacman_action = "WAIT"

    # Initial Render
    if os.name == 'nt': os.system('cls')
    print(env.render())
    print()
    time.sleep(sleep_s)

    while not env.victory and not env.game_over:

        key = get_pressed_key()
        if key is not None: pacman_action = key
        if pacman_action == 'QUIT': break

        current_lives = env.lives
        
        # Pac-Man Step
        env.step(pacman_action)

        if env.lives < current_lives:
            if env.game_over: break
            handle_death_pause(env, sleep_s)
            continue

        # Ghost's Step
        if not env.game_over:
            # --- Ghost A ---
            pac_A, others_A, percepts_A = env.get_ghost_percepts('A')
            move_A = ghost_a.get_next_move(env.ghostA_pos, pac_A, others_A, percepts_A)
            env.move_ghost('A', move_A)
            
            if env.lives < current_lives:
                if env.game_over: break
                handle_death_pause(env, sleep_s)
                continue

            # --- Ghost B ---
            pac_B, others_B, percepts_B = env.get_ghost_percepts('B')
            move_B = ghost_b.get_next_move(env.ghostB_pos, pac_B, others_B, percepts_B)
            env.move_ghost('B', move_B)

            if env.lives < current_lives:
                if env.game_over: break
                handle_death_pause(env, sleep_s)
                continue

            # --- Ghost C ---
            pac_C, others_C, percepts_C = env.get_ghost_percepts('C')
            move_C = ghost_c.get_next_move(env.ghostC_pos, pac_C, others_C, percepts_C)
            env.move_ghost('C', move_C)

            if env.lives < current_lives:
                if env.game_over: break
                handle_death_pause(env, sleep_s)
                continue

        # Normal Frame Render
        if os.name == 'nt': os.system('cls')
        print(env.render())
        print()
        time.sleep(sleep_s)

    # Final Game Over Screen
    if os.name == 'nt': os.system('cls')
    print(env.render())
    print()

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

    # --- Run the Game ---
    run_game(env, ghost_a, ghost_b, ghost_c)

if __name__ == "__main__":
    run_pacman()