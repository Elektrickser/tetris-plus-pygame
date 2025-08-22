
import pygame
import random
import os

import tkinter as tk
from tkinter import simpledialog

# --- CONFIG ---

# Initialwerte, werden im Dialog überschrieben
SCREEN_WIDTH, SCREEN_HEIGHT = 300, 600
GRID_SIZE = 30
FPS = 60

# Tastatureingabe Debounce in ms (ignoriert schnelle Doppel-Registrierungen)
DEBOUNCE_MS = 150

# Start-Defaults für COLUMNS und ROWS (werden in main überschrieben)
COLUMNS = SCREEN_WIDTH // GRID_SIZE
ROWS = SCREEN_HEIGHT // GRID_SIZE

# Sidebar-Breite (wird in main angepasst)
SIDEBAR_WIDTH = 150

# Ghost mode global switch (toggle im Hauptmenü)
GHOST_ENABLED = False
# Ghost style: 'filled' or 'outline'
GHOST_STYLE = 'filled'  # options: 'filled', 'outline'

# Menu fixed size
MENU_WIDTH = 600
MENU_HEIGHT = 600

# Grid presets: (cols, rows)
GRID_PRESETS = [
    (10, 20),  # standard
    (10, 40),
    (20, 40),
    (40, 40)
]

def get_window_size():
    root = tk.Tk()
    root.withdraw()
    # Neue Mindestwerte (vom Nutzer gewünscht)
    min_width_px = 350
    min_height_px = 600
    width = simpledialog.askinteger("Fenstergröße", f"Breite des Fensters (min {min_width_px}, max 800):", minvalue=min_width_px, maxvalue=800)
    height = simpledialog.askinteger("Fenstergröße", f"Höhe des Fensters (min {min_height_px}, max 1200):", minvalue=min_height_px, maxvalue=1200)
    root.destroy()

    # Fallback auf Defaults
    if not width:
        width = SCREEN_WIDTH
    if not height:
        height = SCREEN_HEIGHT
    # Sicherstellen, dass Mindestgrößen eingehalten werden
    if width < min_width_px:
        width = min_width_px
    if height < min_height_px:
        height = min_height_px

    # Auf nächstkleineren Vielfaches von GRID_SIZE runden, aber nicht unter Minimum fallen
    width = width - (width % GRID_SIZE)
    if width < min_width_px:
        # wenn Rundung nach unten kleiner als Minimum wäre, runde auf
        width += GRID_SIZE

    height = height - (height % GRID_SIZE)
    if height < min_height_px:
        height += GRID_SIZE

    return width, height

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

def get_ghost_y(shape, grid, start_x, start_y):
    # returns the y position where the shape would land (top-left y)
    y = start_y
    while True:
        if not valid_space(shape, grid, (start_x, y + 1)):
            break
        y += 1
        if y > ROWS:
            break
    return y

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

def draw_window(surface, grid, score, level, next_piece, hold_shape_index=None, current_piece=None):
    surface.fill((0, 0, 0))
    for y in range(ROWS):
        for x in range(COLUMNS):
            pygame.draw.rect(surface, grid[y][x], (x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE), 0)
    draw_grid_lines(surface)

    font = pygame.font.SysFont("comicsans", 24)
    # Sidebar-Offset verwenden
    sidebar_x = SCREEN_WIDTH
    # Draw ghost for current piece if enabled
    if GHOST_ENABLED and current_piece is not None:
        ghost_y = get_ghost_y(current_piece.shape, grid, current_piece.x, current_piece.y)
        # semi-transparent ghost surface (more visible alpha)
        ghost_surf = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        gx_color = (*current_piece.color[:3], 200)
        ghost_surf.fill(gx_color)
        for gy, row in enumerate(current_piece.shape):
            for gx, cell in enumerate(row):
                if cell:
                    draw_x = (current_piece.x + gx) * GRID_SIZE
                    draw_y = (ghost_y + gy) * GRID_SIZE
                    if GHOST_STYLE == 'filled':
                        surface.blit(ghost_surf, (draw_x, draw_y))
                        pygame.draw.rect(surface, current_piece.color, (draw_x, draw_y, GRID_SIZE, GRID_SIZE), 1)
                    else:
                        # outline-only
                        pygame.draw.rect(surface, current_piece.color, (draw_x, draw_y, GRID_SIZE, GRID_SIZE), 1)
    # Hold box
    hold_label = font.render("Hold:", True, (255, 255, 255))
    surface.blit(hold_label, (sidebar_x + 10, 10))
    if hold_shape_index is not None:
        hold_shape = SHAPES[hold_shape_index]
        hold_color = COLORS[hold_shape_index]
        for y, row in enumerate(hold_shape):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(surface, hold_color,
                                     (sidebar_x + 10 + x * GRID_SIZE,
                                      40 + y * GRID_SIZE, GRID_SIZE, GRID_SIZE), 0)

    # Next box
    label = font.render(f"Next:", True, (255, 255, 255))
    surface.blit(label, (sidebar_x + 10, 140))
    for y, row in enumerate(next_piece.shape):
        for x, cell in enumerate(row):
            if cell:
                pygame.draw.rect(surface, next_piece.color,
                                 (sidebar_x + 10 + x * GRID_SIZE,
                                  170 + y * GRID_SIZE, GRID_SIZE, GRID_SIZE), 0)

    score_label = font.render(f"Score: {score}", True, (255, 255, 255))
    level_label = font.render(f"Level: {level}", True, (255, 255, 255))
    surface.blit(score_label, (sidebar_x + 10, 300))
    surface.blit(level_label, (sidebar_x + 10, 330))
    # Draw active piece on top
    if current_piece is not None:
        for y, row in enumerate(current_piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    draw_x = (current_piece.x + x) * GRID_SIZE
                    draw_y = (current_piece.y + y) * GRID_SIZE
                    pygame.draw.rect(surface, current_piece.color, (draw_x, draw_y, GRID_SIZE, GRID_SIZE), 0)

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

def draw_pause(surface):
    # Draw a semi-transparent overlay and PAUSED label; do not call display.update() here
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surface.blit(overlay, (0, 0))
    font = pygame.font.SysFont("comicsans", 48)
    label = font.render("PAUSED", True, (255, 255, 0))
    surface.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, SCREEN_HEIGHT // 2 - 24))

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
    entries = []
    with open(LEADERBOARD_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(' ', 2)
            # expected: score size name  (e.g. "1234 10x20 Alice")
            if len(parts) == 3:
                score_str, size_str, name = parts
                try:
                    score = int(score_str)
                except ValueError:
                    score = 0
                if 'x' in size_str:
                    try:
                        cols_str, rows_str = size_str.split('x')
                        cols = int(cols_str)
                        rows = int(rows_str)
                    except Exception:
                        cols = None
                        rows = None
                else:
                    cols = None
                    rows = None
                entries.append((name, score, cols, rows))
            else:
                # fallback to old format: score name
                parts2 = line.split(' ', 1)
                if len(parts2) == 2:
                    score_str, name = parts2
                    try:
                        score = int(score_str)
                    except ValueError:
                        score = 0
                    entries.append((name, score, None, None))
    return entries

def save_leaderboard(entries):
    with open(LEADERBOARD_FILE, "w") as f:
        for name, score, cols, rows in entries:
            if cols and rows:
                f.write(f"{score} {cols}x{rows} {name}\n")
            else:
                f.write(f"{score} {name}\n")

def update_leaderboard(name, score, cols=None, rows=None):
    leaderboard = load_leaderboard()
    leaderboard.append((name, score, cols, rows))
    leaderboard.sort(key=lambda x: x[1], reverse=True)
    leaderboard = leaderboard[:5]
    save_leaderboard(leaderboard)

def draw_menu(surface, highscore, selected_preset=0):
    surface.fill((30, 30, 30))
    font_big = pygame.font.SysFont("comicsans", 48)
    font_small = pygame.font.SysFont("comicsans", 24)
    font_mini = pygame.font.SysFont("comicsans", 18)

    # Gesamtbreite (Spielfeld + Sidebar)
    total_width = SCREEN_WIDTH + SIDEBAR_WIDTH

    title = font_big.render("TETRIS ENHANCED", True, (0, 255, 255))
    title_x = max(0, min(total_width // 2 - title.get_width() // 2, total_width - title.get_width()))
    surface.blit(title, (title_x, 20))

    # Spaltenaufteilung: linke Spalte für Optionen, rechte Spalte für Leaderboard
    left_x = int(total_width * 0.06)
    left_width = int(total_width * 0.44)
    right_x = int(total_width * 0.56)

    mouse_x, mouse_y = pygame.mouse.get_pos()

    # Start-Button (linke Spalte)
    button_rect = pygame.Rect(left_x + left_width // 2 - 75, 150, 150, 50)
    btn_color = (0, 200, 0)
    if button_rect.collidepoint((mouse_x, mouse_y)):
        btn_color = (0, 230, 0)
    pygame.draw.rect(surface, btn_color, button_rect, border_radius=6)
    button_text = font_small.render("START", True, (255, 255, 255))
    surface.blit(button_text, (button_rect.x + 35, button_rect.y + 10))

    # Generic option button size
    opt_w = left_width - 40
    opt_h = 36
    opt_x = left_x + 20

    # Ghost option (button with small icon)
    ghost_btn_rect = pygame.Rect(opt_x, 220, opt_w, opt_h)
    ghost_bg = (50, 50, 50)
    if ghost_btn_rect.collidepoint((mouse_x, mouse_y)):
        ghost_bg = (80, 80, 80)
    pygame.draw.rect(surface, ghost_bg, ghost_btn_rect, border_radius=4)
    # icon
    icon_rect = pygame.Rect(ghost_btn_rect.x + 6, ghost_btn_rect.y + 6, opt_h - 12, opt_h - 12)
    if GHOST_STYLE == 'filled' and GHOST_ENABLED:
        pygame.draw.rect(surface, (200, 200, 200), icon_rect)
    else:
        pygame.draw.rect(surface, (200, 200, 200), icon_rect, 2)
    ghost_label = font_small.render(f"Ghost: {'ON' if GHOST_ENABLED else 'OFF'}", True, (255, 255, 255))
    surface.blit(ghost_label, (icon_rect.right + 8, ghost_btn_rect.y + 6))

    # Ghost style toggle (smaller button)
    style_btn_rect = pygame.Rect(opt_x, 260, opt_w, opt_h)
    style_bg = (50, 50, 50)
    if style_btn_rect.collidepoint((mouse_x, mouse_y)):
        style_bg = (80, 80, 80)
    pygame.draw.rect(surface, style_bg, style_btn_rect, border_radius=4)
    # style icon
    s_icon = pygame.Rect(style_btn_rect.x + 6, style_btn_rect.y + 6, opt_h - 12, opt_h - 12)
    if GHOST_STYLE == 'filled':
        pygame.draw.rect(surface, (180, 180, 255), s_icon)
    else:
        pygame.draw.rect(surface, (180, 180, 255), s_icon, 2)
    style_label = font_small.render(f"Ghost style: {GHOST_STYLE}", True, (255, 255, 255))
    surface.blit(style_label, (s_icon.right + 8, style_btn_rect.y + 6))

    # Debounce option
    debounce_btn_rect = pygame.Rect(opt_x, 300, opt_w, opt_h)
    debounce_bg = (50, 50, 50)
    if debounce_btn_rect.collidepoint((mouse_x, mouse_y)):
        debounce_bg = (80, 80, 80)
    pygame.draw.rect(surface, debounce_bg, debounce_btn_rect, border_radius=4)
    # debounce icon: small +/- box
    d_icon = pygame.Rect(debounce_btn_rect.x + 6, debounce_btn_rect.y + 6, opt_h - 12, opt_h - 12)
    pygame.draw.rect(surface, (200, 200, 100), d_icon, border_radius=2)
    debounce_label = font_small.render(f"Debounce: {DEBOUNCE_MS}ms", True, (255, 255, 255))
    surface.blit(debounce_label, (d_icon.right + 8, debounce_btn_rect.y + 6))

    # Leaderboard (rechts)
    surface.blit(font_small.render("Leaderboard:", True, (255, 255, 0)), (right_x, 140))
    y_pos = 170
    leaderboard = load_leaderboard()
    for i, entry in enumerate(leaderboard):
        # entry is (name, score, cols, rows)
        if len(entry) >= 4:
            name, score, cols, rows = entry
        else:
            name, score = entry[0], entry[1]
            cols = rows = None
        size_text = f" {cols}x{rows}" if cols and rows else ""
        surface.blit(font_mini.render(f"{i+1}. {name} - {score}{size_text}", True, (255, 255, 255)), (right_x + 10, y_pos))
        y_pos += 25

    # Preset buttons (labels 1-4) in left column below options (larger)
    preset_rects = []
    px = left_x + 20
    py = 340
    preset_w = opt_w
    preset_h = opt_h + 8
    for i, (c, r) in enumerate(GRID_PRESETS):
        rect = pygame.Rect(px, py + i * (preset_h + 8), preset_w, preset_h)
        bg = (60, 60, 60)
        if i == selected_preset:
            bg = (100, 100, 120)
        if rect.collidepoint((mouse_x, mouse_y)):
            bg = (90, 90, 90)
        pygame.draw.rect(surface, bg, rect, border_radius=6)
        text = font_small.render(f"{i+1}: {c}x{r}", True, (255, 255, 255))
        surface.blit(text, (rect.x + 12, rect.y + 6))
        preset_rects.append(rect)

    # Shortcut hint line
    hint = font_mini.render("Shortcuts: S/Enter Start  G Ghost  T Style  D Debounce  1-4 Presets", True, (180, 180, 180))
    surface.blit(hint, (left_x + 10, MENU_HEIGHT - 30))
    pygame.display.update()
    return button_rect, ghost_btn_rect, style_btn_rect, debounce_btn_rect, preset_rects

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
    paused = False
    # Debounce-Tabelle: speichert zuletzt registrierte Zeit pro Key
    last_key_time = {}
    # Hold-Funktionalität
    hold_shape_index = None
    hold_used = False  # kann nur einmal pro erzeugtem Stein benutzt werden

    while run:
        grid = create_grid(locked_positions)
        # Verwende dt vom Clock; wenn pausiert, Zeit nicht erhöhen
        dt = clock.tick(FPS)
        if not paused:
            fall_time += dt
            move_time += dt / 1000

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
                # Aktualisiere das Grid sofort, damit volle Reihen erkannt werden
                grid = create_grid(locked_positions)
                score += 10
                lines_cleared = clear_rows(grid, locked_positions)
                score += lines_cleared * 100
                level = start_level + score // 500
                fall_speed = max(0.1, 0.5 - (level * 0.05))
                # Nach dem Entfernen neu erstellen
                grid = create_grid(locked_positions)

                shape_index = next_shape_index
                current_piece = Tetromino(SHAPES[shape_index], COLORS[shape_index])
                next_shape_index = random.randint(0, len(SHAPES) - 1)
                next_piece = Tetromino(SHAPES[next_shape_index], COLORS[next_shape_index])
                # Neuer Stein aus Next: Hold wieder erlauben
                hold_used = False
                if not valid_space(current_piece.shape, grid, (current_piece.x, current_piece.y)):
                    draw_game_over(win, score)
                    name = get_player_name(win)
                    update_leaderboard(name, score, COLUMNS, ROWS)
                    run = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                # Debounce: ignore repeated quick presses of the same key
                now = pygame.time.get_ticks()
                last = last_key_time.get(event.key, 0)
                if now - last < DEBOUNCE_MS:
                    continue
                last_key_time[event.key] = now

                if event.key == pygame.K_p:
                    paused = not paused
                    if paused:
                        # Reset input-holds so Bewegung stoppt vollständig
                        left_hold = False
                        right_hold = False
                        soft_drop = False
                        draw_pause(win)
                    continue
                if event.key == pygame.K_b:
                    # Hold/Swap
                    if hold_shape_index is None:
                        # Leerer Hold: verschiebe aktuellen Stein in Hold und spawne Next
                        hold_shape_index = shape_index
                        shape_index = next_shape_index
                        current_piece = Tetromino(SHAPES[shape_index], COLORS[shape_index])
                        next_shape_index = random.randint(0, len(SHAPES) - 1)
                        next_piece = Tetromino(SHAPES[next_shape_index], COLORS[next_shape_index])
                        hold_used = True
                    else:
                        # Tausch nur erlaubt, wenn noch nicht benutzt für diese Runde
                        if not hold_used:
                            # swap
                            temp = hold_shape_index
                            hold_shape_index = shape_index
                            shape_index = temp
                            current_piece = Tetromino(SHAPES[shape_index], COLORS[shape_index])
                            # mark as used
                            hold_used = True
                    continue
                if paused:
                    continue
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
                    # Update grid before clearing rows to detect volle Reihen sofort
                    grid = create_grid(locked_positions)
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
                    # Neuer Stein aus Next: Hold wieder erlauben
                    hold_used = False
                    if not valid_space(current_piece.shape, grid, (current_piece.x, current_piece.y)):
                        draw_game_over(win, score)
                        name = get_player_name(win)
                        update_leaderboard(name, score, COLUMNS, ROWS)
                        run = False
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    left_hold = False
                elif event.key == pygame.K_RIGHT:
                    right_hold = False
                elif event.key == pygame.K_DOWN:
                    soft_drop = False

    # active piece is drawn by draw_window (so ghost calculation uses grid without it)

        draw_window(win, grid, score, level, next_piece, hold_shape_index, current_piece)
        if paused:
            draw_pause(win)
        pygame.display.update()

    return highscore

def main():
    global SCREEN_WIDTH, SCREEN_HEIGHT, COLUMNS, ROWS, SIDEBAR_WIDTH, GHOST_ENABLED, GHOST_STYLE, DEBOUNCE_MS
    pygame.init()
    highscore = 0

    # Menu runs in fixed-size window
    menu_win = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT))
    pygame.display.set_caption("Tetris Enhanced - Menu")

    selected_preset = 0
    running = True
    while running:
        button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
        menu = True
        while menu:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    menu = False
                elif event.type == pygame.KEYDOWN:
                    # Shortcuts: S/ENTER start, G ghost toggle, T style toggle, D debounce, 1-4 presets
                    if event.key in (pygame.K_s, pygame.K_RETURN):
                        menu = False
                        break
                    if event.key == pygame.K_g:
                        GHOST_ENABLED = not GHOST_ENABLED
                        button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
                    if event.key == pygame.K_t:
                        GHOST_STYLE = 'outline' if GHOST_STYLE == 'filled' else 'filled'
                        button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
                    if event.key == pygame.K_d:
                        options = [50, 100, 150, 250]
                        try:
                            idx = options.index(DEBOUNCE_MS)
                            DEBOUNCE_MS = options[(idx + 1) % len(options)]
                        except ValueError:
                            DEBOUNCE_MS = 150
                        button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
                    if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                        selected_preset = int(event.unicode) - 1
                        button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = event.pos
                    # map mouse pos to menu coordinates (menu_win)
                    if button_rect.collidepoint(pos):
                        menu = False
                        break
                    if ghost_rect.collidepoint(pos):
                        GHOST_ENABLED = not GHOST_ENABLED
                        button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
                    if style_rect.collidepoint(pos):
                        GHOST_STYLE = 'outline' if GHOST_STYLE == 'filled' else 'filled'
                        button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
                    if debounce_rect.collidepoint(pos):
                        options = [50, 100, 150, 250]
                        try:
                            idx = options.index(DEBOUNCE_MS)
                            DEBOUNCE_MS = options[(idx + 1) % len(options)]
                        except ValueError:
                            DEBOUNCE_MS = 150
                        button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
                    # presets
                    for idx, rect in enumerate(preset_rects):
                        if rect.collidepoint(pos):
                            selected_preset = idx
                            button_rect, ghost_rect, style_rect, debounce_rect, preset_rects = draw_menu(menu_win, highscore, selected_preset)
            pygame.time.delay(10)

        if not running:
            break

        # Start game with selected preset
        cols, rows = GRID_PRESETS[selected_preset]
        SCREEN_WIDTH = cols * GRID_SIZE
        SCREEN_HEIGHT = rows * GRID_SIZE
        COLUMNS = cols
        ROWS = rows
        SIDEBAR_WIDTH = max(120, min(300, SCREEN_WIDTH // 5))

        # Initialize game window sized for play area + sidebar
        win = pygame.display.set_mode((SCREEN_WIDTH + SIDEBAR_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tetris Enhanced")
        start_level = select_level(win)
        game_loop(win, highscore, start_level)

    pygame.quit()

if __name__ == "__main__":
    main()
