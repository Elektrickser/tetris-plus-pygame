import pygame
import random
import os

# --- CONFIG ---
SCREEN_WIDTH, SCREEN_HEIGHT = 300, 600
GRID_SIZE = 30
COLUMNS = SCREEN_WIDTH // GRID_SIZE
ROWS = SCREEN_HEIGHT // GRID_SIZE
FPS = 60

SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1, 0], [0, 1, 1]],  # S
    [[0, 1, 1], [1, 1, 0]],  # Z
    [[1, 1, 1], [1, 0, 0]],  # L
    [[1, 1, 1], [0, 0, 1]],  # J
    [[1, 1], [1, 1]]  # O
]
COLORS = [
    (0, 255, 255),  # I - Cyan
    (128, 0, 128),  # T - Purple
    (0, 255, 0),    # S - Green
    (255, 0, 0),    # Z - Red
    (255, 165, 0),  # L - Orange
    (0, 0, 255),    # J - Blue
    (255, 255, 0)   # O - Yellow
]

LEADERBOARD_FILE = "leaderboard.txt"

class Tetromino:
    def __init__(self, shape, color):
        self.shape = shape
        self.color = color
        self.x = COLUMNS // 2 - len(shape[0]) // 2
        self.y = 0

    def rotate(self):
        self.shape = [list(row) for row in zip(*self.shape[::-1])]

def create_grid(locked_positions={}):
    grid = [[(0, 0, 0) for _ in range(COLUMNS)] for _ in range(ROWS)]
    for y in range(ROWS):
        for x in range(COLUMNS):
            if (x, y) in locked_positions:
                grid[y][x] = locked_positions[(x, y)]
    return grid

def valid_space(shape, grid, offset):
    off_x, off_y = offset
    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                new_x = x + off_x
                new_y = y + off_y
                if new_x < 0 or new_x >= COLUMNS or new_y >= ROWS:
                    return False
                if new_y >= 0 and grid[new_y][new_x] != (0, 0, 0):
                    return False
    return True

def clear_rows(grid, locked):
    full_rows = [y for y in range(ROWS) if (0, 0, 0) not in grid[y]]
    if full_rows:
        # Flash effect before clearing
        for y in full_rows:
            for x in range(COLUMNS):
                grid[y][x] = (255, 255, 255)
        pygame.display.update()
        pygame.time.delay(150)

    for y in full_rows:
        for x in range(COLUMNS):
            locked.pop((x, y), None)
    for x, y in sorted(list(locked.keys()), key=lambda k: k[1], reverse=True):
        shift = sum(1 for row in full_rows if y < row)
        if shift:
            locked[(x, y + shift)] = locked.pop((x, y))
    return len(full_rows)

def draw_grid_lines(surface):
    for y in range(ROWS):
        pygame.draw.line(surface, (50, 50, 50), (0, y * GRID_SIZE), (SCREEN_WIDTH, y * GRID_SIZE))
    for x in range(COLUMNS):
        pygame.draw.line(surface, (50, 50, 50), (x * GRID_SIZE, 0), (x * GRID_SIZE, SCREEN_HEIGHT))

def draw_window(surface, grid, score, level, next_piece):
    surface.fill((0, 0, 0))
    for y in range(ROWS):
        for x in range(COLUMNS):
            pygame.draw.rect(surface, grid[y][x], (x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE), 0)
    draw_grid_lines(surface)

    font = pygame.font.SysFont("comicsans", 24)
    label = font.render(f"Next:", True, (255, 255, 255))
    surface.blit(label, (SCREEN_WIDTH + 10, 30))
    for y, row in enumerate(next_piece.shape):
        for x, cell in enumerate(row):
            if cell:
                pygame.draw.rect(surface, next_piece.color,
                                 (SCREEN_WIDTH + 10 + x * GRID_SIZE,
                                  60 + y * GRID_SIZE, GRID_SIZE, GRID_SIZE), 0)

    score_label = font.render(f"Score: {score}", True, (255, 255, 255))
    level_label = font.render(f"Level: {level}", True, (255, 255, 255))
    surface.blit(score_label, (SCREEN_WIDTH + 10, 200))
    surface.blit(level_label, (SCREEN_WIDTH + 10, 230))

def draw_game_over(surface, score):
    surface.fill((0, 0, 0))
    font_big = pygame.font.SysFont("comicsans", 48)
    font_small = pygame.font.SysFont("comicsans", 30)
    label = font_big.render("GAME OVER", True, (255, 0, 0))
    score_label = font_small.render(f"Score: {score}", True, (255, 255, 255))
    surface.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
    surface.blit(score_label, (SCREEN_WIDTH // 2 - score_label.get_width() // 2, SCREEN_HEIGHT // 2))
    pygame.display.update()
    pygame.time.delay(1500)

def get_player_name(surface):
    font = pygame.font.SysFont("comicsans", 28)
    name = ""
    entering = True
    while entering:
        surface.fill((0, 0, 0))
        prompt = font.render("Enter your name:", True, (255, 255, 255))
        surface.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, SCREEN_HEIGHT // 2 - 40))
        name_text = font.render(name, True, (255, 255, 0))
        surface.blit(name_text, (SCREEN_WIDTH // 2 - name_text.get_width() // 2, SCREEN_HEIGHT // 2))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                entering = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    entering = False
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                else:
                    if len(name) < 10:
                        name += event.unicode
    return name.strip() if name.strip() else "Player"

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    with open(LEADERBOARD_FILE, "r") as f:
        lines = [line.strip().split(" ", 1) for line in f if line.strip()]
    return [(n, int(s)) for s, n in (line for line in [(l[0], l[1]) if len(l) > 1 else ("0", "Unknown") for l in lines])]

def save_leaderboard(entries):
    with open(LEADERBOARD_FILE, "w") as f:
        for name, score in entries:
            f.write(f"{score} {name}\n")

def update_leaderboard(name, score):
    leaderboard = load_leaderboard()
    leaderboard.append((name, score))
    leaderboard.sort(key=lambda x: x[1], reverse=True)
    leaderboard = leaderboard[:5]
    save_leaderboard(leaderboard)

def draw_menu(surface, highscore):
    surface.fill((30, 30, 30))
    font_big = pygame.font.SysFont("comicsans", 48)
    font_small = pygame.font.SysFont("comicsans", 24)
    font_mini = pygame.font.SysFont("comicsans", 18)

    title = font_big.render("TETRIS ENHANCED", True, (0, 255, 255))
    surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

    button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 75, 150, 150, 50)
    pygame.draw.rect(surface, (0, 200, 0), button_rect)
    button_text = font_small.render("START", True, (255, 255, 255))
    surface.blit(button_text, (button_rect.x + 35, button_rect.y + 10))

    # Leaderboard
    leaderboard = load_leaderboard()
    y_pos = 250
    surface.blit(font_small.render("Leaderboard:", True, (255, 255, 0)), (20, y_pos))
    for i, (name, score) in enumerate(leaderboard):
        y_pos += 25
        surface.blit(font_mini.render(f"{i+1}. {name} - {score}", True, (255, 255, 255)), (30, y_pos))

    pygame.display.update()
    return button_rect

def select_level(surface):
    levels = [0, 4, 8, 12, 16, 20]
    selected = 0
    font = pygame.font.SysFont("comicsans", 28)
    selecting = True
    while selecting:
        surface.fill((0, 0, 0))
        label = font.render("Select starting level", True, (255, 255, 255))
        surface.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, 100))
        for i, lvl in enumerate(levels):
            color = (255, 255, 0) if i == selected else (200, 200, 200)
            text = font.render(str(lvl), True, color)
            surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 200 + i * 40))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                selecting = False
                return levels[selected]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(levels)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(levels)
                elif event.key == pygame.K_RETURN:
                    return levels[selected]

def game_loop(win, highscore, start_level):
    clock = pygame.time.Clock()
    locked_positions = {}
    shape_index = random.randint(0, len(SHAPES) - 1)
    current_piece = Tetromino(SHAPES[shape_index], COLORS[shape_index])
    next_shape_index = random.randint(0, len(SHAPES) - 1)
    next_piece = Tetromino(SHAPES[next_shape_index], COLORS[next_shape_index])
    fall_time = 0
    score = 0
    level = start_level
    fall_speed = max(0.1, 0.5 - (level * 0.05))
    soft_drop = False
    soft_drop_speed = 0.05
    left_hold = False
    right_hold = False
    move_delay = 0.08
    move_time = 0
    run = True

    while run:
        grid = create_grid(locked_positions)
        fall_time += clock.get_rawtime()
        clock.tick(FPS)
        move_time += clock.get_time() / 1000

        if left_hold and move_time >= move_delay:
            if valid_space(current_piece.shape, grid, (current_piece.x - 1, current_piece.y)):
                current_piece.x -= 1
            move_time = 0
        if right_hold and move_time >= move_delay:
            if valid_space(current_piece.shape, grid, (current_piece.x + 1, current_piece.y)):
                current_piece.x += 1
            move_time = 0

        current_fall_speed = soft_drop_speed if soft_drop else fall_speed
        if fall_time / 1000 >= current_fall_speed:
            fall_time = 0
            current_piece.y += 1
            if not valid_space(current_piece.shape, grid, (current_piece.x, current_piece.y)):
                current_piece.y -= 1
                for y, row in enumerate(current_piece.shape):
                    for x, cell in enumerate(row):
                        if cell:
                            locked_positions[(current_piece.x + x, current_piece.y + y)] = current_piece.color
                score += 10
                lines_cleared = clear_rows(grid, locked_positions)
                score += lines_cleared * 100
                level = start_level + score // 500
                fall_speed = max(0.1, 0.5 - (level * 0.05))
                grid = create_grid(locked_positions)

                shape_index = next_shape_index
                current_piece = Tetromino(SHAPES[shape_index], COLORS[shape_index])
                next_shape_index = random.randint(0, len(SHAPES) - 1)
                next_piece = Tetromino(SHAPES[next_shape_index], COLORS[next_shape_index])
                if not valid_space(current_piece.shape, grid, (current_piece.x, current_piece.y)):
                    draw_game_over(win, score)
                    name = get_player_name(win)
                    update_leaderboard(name, score)
                    run = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    left_hold = True
                    if valid_space(current_piece.shape, grid, (current_piece.x - 1, current_piece.y)):
                        current_piece.x -= 1
                    move_time = 0
                elif event.key == pygame.K_RIGHT:
                    right_hold = True
                    if valid_space(current_piece.shape, grid, (current_piece.x + 1, current_piece.y)):
                        current_piece.x += 1
                    move_time = 0
                elif event.key == pygame.K_DOWN:
                    soft_drop = True
                elif event.key == pygame.K_UP:
                    rotated = [list(row) for row in zip(*current_piece.shape[::-1])]
                    if valid_space(rotated, grid, (current_piece.x, current_piece.y)):
                        current_piece.rotate()
                    elif valid_space(rotated, grid, (current_piece.x - 1, current_piece.y)):
                        current_piece.x -= 1
                        current_piece.rotate()
                    elif valid_space(rotated, grid, (current_piece.x + 1, current_piece.y)):
                        current_piece.x += 1
                        current_piece.rotate()
                elif event.key == pygame.K_SPACE:
                    while valid_space(current_piece.shape, grid, (current_piece.x, current_piece.y + 1)):
                        current_piece.y += 1
                    for y, row in enumerate(current_piece.shape):
                        for x, cell in enumerate(row):
                            if cell:
                                locked_positions[(current_piece.x + x, current_piece.y + y)] = current_piece.color
                    score += 10
                    lines_cleared = clear_rows(grid, locked_positions)
                    score += lines_cleared * 100
                    level = start_level + score // 500
                    fall_speed = max(0.1, 0.5 - (level * 0.05))
                    grid = create_grid(locked_positions)
                    shape_index = next_shape_index
                    current_piece = Tetromino(SHAPES[shape_index], COLORS[shape_index])
                    next_shape_index = random.randint(0, len(SHAPES) - 1)
                    next_piece = Tetromino(SHAPES[next_shape_index], COLORS[next_shape_index])
                    if not valid_space(current_piece.shape, grid, (current_piece.x, current_piece.y)):
                        draw_game_over(win, score)
                        name = get_player_name(win)
                        update_leaderboard(name, score)
                        run = False
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    left_hold = False
                elif event.key == pygame.K_RIGHT:
                    right_hold = False
                elif event.key == pygame.K_DOWN:
                    soft_drop = False

        for y, row in enumerate(current_piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    grid_y = current_piece.y + y
                    grid_x = current_piece.x + x
                    if 0 <= grid_y < ROWS and 0 <= grid_x < COLUMNS:
                        grid[grid_y][grid_x] = current_piece.color

        draw_window(win, grid, score, level, next_piece)
        pygame.display.update()

    return highscore

def main():
    pygame.init()
    win = pygame.display.set_mode((SCREEN_WIDTH + 150, SCREEN_HEIGHT))
    pygame.display.set_caption("Tetris Enhanced")
    highscore = 0

    running = True
    while running:
        button_rect = draw_menu(win, highscore)
        menu = True
        while menu:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    menu = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if button_rect.collidepoint(event.pos):
                        menu = False
            pygame.time.delay(10)

        if running:
            start_level = select_level(win)
            game_loop(win, highscore, start_level)

    pygame.quit()

if __name__ == "__main__":
    main()
