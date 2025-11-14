import pygame
import random
import math

pygame.init()

# =====================
# SETTINGS
# =====================
WIDTH, HEIGHT = 1200, 800
CELL_SIZE = 40  # Size of each maze cell

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2-Player Maze Race")
clock = pygame.time.Clock()

# Colors
COLOR_BG = (40, 40, 60)
COLOR_WALL_LINE = (255, 255, 255)
COLOR_START = (0, 255, 0)
COLOR_END = (255, 215, 0)
COLOR_P1 = (100, 200, 255)
COLOR_P2 = (255, 100, 200)

# Game state
game_state = "menu"  # "menu", "settings", "playing", "won"
darkness_mode = "light"  # "light" or "dark"
timer_start = 0
elapsed_time = 0
winner = None

# Light settings for dark mode
PLAYER_LIGHT_RADIUS = 120

# Maze settings - Calculate rows and cols to fill the window
MAZE_COLS = WIDTH // CELL_SIZE
MAZE_ROWS = HEIGHT // CELL_SIZE

# ==========================
# PLAYER CLASS
# ==========================
class RacePlayer:
    def __init__(self, x, y, color, controls, name):
        self.x = x
        self.y = y
        self.color = color
        self.controls = controls  # Dictionary with keys: up, down, left, right
        self.name = name
        self.speed = 4
        self.radius = 12
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius * 2, self.radius * 2)
        self.finished = False
        self.finish_time = 0
    
    def handle_input(self, keys):
        if self.finished:
            return 0, 0
        
        dx = 0
        dy = 0
        
        if keys[self.controls['left']]:
            dx -= self.speed
        if keys[self.controls['right']]:
            dx += self.speed
        if keys[self.controls['up']]:
            dy -= self.speed
        if keys[self.controls['down']]:
            dy += self.speed
        
        # Normalize diagonal movement
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707
        
        return dx, dy
    
    def move(self, dx, dy, walls):
        if self.finished:
            return
        
        # Try horizontal movement
        new_x = self.x + dx
        test_rect = pygame.Rect(new_x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)
        
        collision = self.check_wall_collision(test_rect, walls)
        
        if not collision:
            self.x = new_x
        
        # Try vertical movement
        new_y = self.y + dy
        test_rect = pygame.Rect(self.x - self.radius, new_y - self.radius, self.radius * 2, self.radius * 2)
        
        collision = self.check_wall_collision(test_rect, walls)
        
        if not collision:
            self.y = new_y
        
        # Update rect
        self.rect = pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)
    
    def check_wall_collision(self, rect, walls):
        """Check if rect collides with any wall lines"""
        for wall in walls:
            # Wall is a line (x1, y1, x2, y2)
            if self.rect_line_collision(rect, wall):
                return True
        return False
    
    def rect_line_collision(self, rect, line):
        """Check if a rectangle collides with a line"""
        x1, y1, x2, y2 = line
        
        # Check if line intersects with any of the 4 edges of the rectangle
        # Top edge
        if self.line_intersect(x1, y1, x2, y2, rect.left, rect.top, rect.right, rect.top):
            return True
        # Bottom edge
        if self.line_intersect(x1, y1, x2, y2, rect.left, rect.bottom, rect.right, rect.bottom):
            return True
        # Left edge
        if self.line_intersect(x1, y1, x2, y2, rect.left, rect.top, rect.left, rect.bottom):
            return True
        # Right edge
        if self.line_intersect(x1, y1, x2, y2, rect.right, rect.top, rect.right, rect.bottom):
            return True
        
        return False
    
    def line_intersect(self, x1, y1, x2, y2, x3, y3, x4, y4):
        """Check if two line segments intersect"""
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return False
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        return 0 <= t <= 1 and 0 <= u <= 1
    
    def draw(self, surface):
        # Draw player as circle
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.radius + 2)
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        
        # Draw inner shine
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x - 4), int(self.y - 4)), 4)
        
        # Draw crown if finished first
        if self.finished and winner == self.name:
            font = pygame.font.Font(None, 36)
            crown = font.render("👑", True, (255, 215, 0))
            surface.blit(crown, (int(self.x - 15), int(self.y - 35)))

# ==========================
# MAZE GENERATION
# ==========================
def generate_maze(cols, rows):
    """Generate a maze using recursive backtracking - returns wall lines"""
    # Create grid of cells
    visited = [[False for _ in range(cols)] for _ in range(rows)]
    
    # Each cell has 4 walls: top, right, bottom, left
    walls_grid = [[{'top': True, 'right': True, 'bottom': True, 'left': True} 
                   for _ in range(cols)] for _ in range(rows)]
    
    def carve_passage(row, col):
        visited[row][col] = True
        
        # Directions: up, right, down, left
        directions = [(-1, 0, 'top', 'bottom'), 
                     (0, 1, 'right', 'left'), 
                     (1, 0, 'bottom', 'top'), 
                     (0, -1, 'left', 'right')]
        
        random.shuffle(directions)
        
        for dr, dc, wall1, wall2 in directions:
            new_row, new_col = row + dr, col + dc
            
            if 0 <= new_row < rows and 0 <= new_col < cols and not visited[new_row][new_col]:
                # Remove walls between cells
                walls_grid[row][col][wall1] = False
                walls_grid[new_row][new_col][wall2] = False
                carve_passage(new_row, new_col)
    
    # Start from top-left
    carve_passage(0, 0)
    
    # Remove walls from start areas and finish area
    # Player 1 start area (top-left 2x2)
    for row in range(2):
        for col in range(2):
            if row == 0:  # Remove top walls
                walls_grid[row][col]['top'] = False
            if col == 0:  # Remove left walls
                walls_grid[row][col]['left'] = False
            if row == 1:  # Remove bottom walls for top row
                walls_grid[row][col]['top'] = False
    
    # Player 2 start area (top-right 2x2)
    for row in range(2):
        for col in range(cols-2, cols):
            if row == 0:  # Remove top walls
                walls_grid[row][col]['top'] = False
            if col == cols-1:  # Remove right walls
                walls_grid[row][col]['right'] = False
            if row == 1:  # Remove bottom walls for top row
                walls_grid[row][col]['top'] = False
    
    # Finish area (bottom-middle 2x2)
    finish_col = cols // 2 - 1
    for row in range(rows-2, rows):
        for col in range(finish_col, finish_col+2):
            if row == rows-1:  # Remove bottom walls for finish area
                walls_grid[row][col]['bottom'] = False
            if row == rows-2:  # Remove top walls for bottom row
                walls_grid[row][col]['bottom'] = False
    
    # Convert walls to line segments
    wall_lines = []
    
    # Add outer boundary walls (prevent players from going outside)
    wall_lines.append((0, 0, cols * CELL_SIZE, 0))  # Top wall
    wall_lines.append((cols * CELL_SIZE, 0, cols * CELL_SIZE, rows * CELL_SIZE))  # Right wall
    wall_lines.append((0, rows * CELL_SIZE, cols * CELL_SIZE, rows * CELL_SIZE))  # Bottom wall
    wall_lines.append((0, 0, 0, rows * CELL_SIZE))  # Left wall
    
    for row in range(rows):
        for col in range(cols):
            x = col * CELL_SIZE
            y = row * CELL_SIZE
            
            # Top wall
            if walls_grid[row][col]['top']:
                wall_lines.append((x, y, x + CELL_SIZE, y))
            
            # Right wall
            if walls_grid[row][col]['right']:
                wall_lines.append((x + CELL_SIZE, y, x + CELL_SIZE, y + CELL_SIZE))
            
            # Bottom wall
            if walls_grid[row][col]['bottom']:
                wall_lines.append((x, y + CELL_SIZE, x + CELL_SIZE, y + CELL_SIZE))
            
            # Left wall
            if walls_grid[row][col]['left']:
                wall_lines.append((x, y, x, y + CELL_SIZE))
    
    return wall_lines

# ==========================
# DRAWING FUNCTIONS
# ==========================
def draw_maze_walls(walls):
    """Draw walls as lines"""
    for wall in walls:
        x1, y1, x2, y2 = wall
        pygame.draw.line(screen, COLOR_WALL_LINE, (x1, y1), (x2, y2), 3)

def draw_start_finish():
    """Draw start zones and finish zone"""
    # Player 1 Start zone (top-left)
    p1_start_rect = pygame.Rect(0, 0, CELL_SIZE * 2, CELL_SIZE * 2)
    pygame.draw.rect(screen, COLOR_P1, p1_start_rect)
    pygame.draw.rect(screen, (255, 255, 255), p1_start_rect, 3)
    
    font = pygame.font.Font(None, 30)
    p1_text = font.render("P1 START", True, (255, 255, 255))
    screen.blit(p1_text, (p1_start_rect.centerx - p1_text.get_width() // 2, 
                         p1_start_rect.centery - p1_text.get_height() // 2))
    
    # Player 2 Start zone (top-right)
    p2_start_x = (MAZE_COLS - 2) * CELL_SIZE
    p2_start_rect = pygame.Rect(p2_start_x, 0, CELL_SIZE * 2, CELL_SIZE * 2)
    pygame.draw.rect(screen, COLOR_P2, p2_start_rect)
    pygame.draw.rect(screen, (255, 255, 255), p2_start_rect, 3)
    
    p2_text = font.render("P2 START", True, (255, 255, 255))
    screen.blit(p2_text, (p2_start_rect.centerx - p2_text.get_width() // 2, 
                         p2_start_rect.centery - p2_text.get_height() // 2))
    
    # Finish zone (bottom-middle)
    finish_x = (MAZE_COLS // 2 - 1) * CELL_SIZE
    finish_y = (MAZE_ROWS - 2) * CELL_SIZE
    finish_rect = pygame.Rect(finish_x, finish_y, CELL_SIZE * 2, CELL_SIZE * 2)
    pygame.draw.rect(screen, COLOR_END, finish_rect)
    pygame.draw.rect(screen, (255, 255, 255), finish_rect, 3)
    
    font_finish = pygame.font.Font(None, 36)
    finish_text = font_finish.render("FINISH", True, (0, 0, 0))
    screen.blit(finish_text, (finish_rect.centerx - finish_text.get_width() // 2, 
                             finish_rect.centery - finish_text.get_height() // 2))
    
    # Add star decoration
    star_font = pygame.font.Font(None, 48)
    star = star_font.render("★", True, (255, 255, 255))
    screen.blit(star, (finish_rect.centerx - star.get_width() // 2, finish_rect.top - 30))
    
    return p1_start_rect, p2_start_rect, finish_rect

def draw_darkness_overlay(players, light_radius):
    """Draw darkness with light around each player"""
    darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, 230))
    
    for player in players:
        # Draw gradient circles for light
        num_layers = 8
        for layer in range(num_layers, 0, -1):
            ratio = layer / num_layers
            alpha = int(230 * (1 - ratio))
            current_radius = int(light_radius * ratio)
            
            if current_radius > 0:
                layer_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.circle(layer_surf, (0, 0, 0, alpha), 
                                 (int(player.x), int(player.y)), current_radius)
                darkness.blit(layer_surf, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    
    screen.blit(darkness, (0, 0))

# ==========================
# MENU & UI
# ==========================
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
    
    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 3, border_radius=10)
        
        font = pygame.font.Font(None, 36)
        text_surf = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def is_clicked(self, mouse_pos, mouse_clicked):
        return self.rect.collidepoint(mouse_pos) and mouse_clicked

def draw_main_menu():
    screen.fill(COLOR_BG)
    
    font_title = pygame.font.Font(None, 90)
    title_text = font_title.render("MAZE RACE", True, (255, 255, 0))
    title_rect = title_text.get_rect(center=(WIDTH // 2, 100))
    screen.blit(title_text, title_rect)
    
    font_subtitle = pygame.font.Font(None, 36)
    subtitle = font_subtitle.render("Race to the finish line!", True, (200, 200, 200))
    subtitle_rect = subtitle.get_rect(center=(WIDTH // 2, 180))
    screen.blit(subtitle, subtitle_rect)
    
    # Player controls info
    font_info = pygame.font.Font(None, 32)
    p1_text = font_info.render("Player 1 (Blue): W/A/S/D", True, COLOR_P1)
    p2_text = font_info.render("Player 2 (Pink): Arrow Keys", True, COLOR_P2)
    screen.blit(p1_text, (WIDTH // 2 - p1_text.get_width() // 2, 240))
    screen.blit(p2_text, (WIDTH // 2 - p2_text.get_width() // 2, 280))
    
    button_width = 300
    button_height = 70
    button_x = WIDTH // 2 - button_width // 2
    
    start_btn = Button(button_x, 380, button_width, button_height, 
                      "START RACE", (50, 150, 50), (70, 200, 70))
    
    quit_btn = Button(button_x, 480, button_width, button_height, 
                     "QUIT", (150, 50, 50), (200, 70, 70))
    
    start_btn.draw(screen)
    quit_btn.draw(screen)
    
    return start_btn, quit_btn

def draw_settings_menu():
    screen.fill(COLOR_BG)
    
    font_title = pygame.font.Font(None, 70)
    title_text = font_title.render("LIGHTING MODE", True, (255, 255, 0))
    title_rect = title_text.get_rect(center=(WIDTH // 2, 100))
    screen.blit(title_text, title_rect)
    
    font_info = pygame.font.Font(None, 32)
    info_text = font_info.render("Choose your challenge:", True, (200, 200, 200))
    screen.blit(info_text, (WIDTH // 2 - info_text.get_width() // 2, 180))
    
    button_width = 250
    button_height = 80
    
    light_btn = Button(WIDTH // 2 - button_width - 30, 280, button_width, button_height,
                       "LIGHT MODE", (100, 150, 200), (120, 180, 230))
    
    dark_btn = Button(WIDTH // 2 + 30, 280, button_width, button_height,
                      "DARK MODE 🌙", (80, 50, 120), (110, 70, 150))
    
    # Highlight selected mode
    if darkness_mode == "light":
        pygame.draw.rect(screen, (255, 255, 0), light_btn.rect, 5, border_radius=10)
    else:
        pygame.draw.rect(screen, (255, 255, 0), dark_btn.rect, 5, border_radius=10)
    
    light_btn.draw(screen)
    dark_btn.draw(screen)
    
    # Mode descriptions
    font_desc = pygame.font.Font(None, 26)
    if darkness_mode == "light":
        desc = "Full visibility - Race with no restrictions!"
    else:
        desc = "Limited vision - Navigate carefully in the dark!"
    desc_text = font_desc.render(desc, True, (200, 200, 200))
    screen.blit(desc_text, (WIDTH // 2 - desc_text.get_width() // 2, 400))
    
    # Start button
    start_btn = Button(WIDTH // 2 - 180, 480, 360, 70,
                       "START GAME", (50, 150, 50), (70, 200, 70))
    start_btn.draw(screen)
    
    # Back button
    back_btn = Button(WIDTH // 2 - 100, 580, 200, 50,
                      "BACK", (100, 100, 100), (150, 150, 150))
    back_btn.draw(screen)
    
    return light_btn, dark_btn, start_btn, back_btn

def draw_victory_screen(winner_name, winner_time, loser_time):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    font_huge = pygame.font.Font(None, 90)
    font_big = pygame.font.Font(None, 60)
    font_med = pygame.font.Font(None, 40)
    
    # Winner announcement
    winner_color = COLOR_P1 if winner_name == "Player 1" else COLOR_P2
    winner_text = font_huge.render(f"👑 {winner_name.upper()} WINS! 👑", True, winner_color)
    screen.blit(winner_text, (WIDTH // 2 - winner_text.get_width() // 2, HEIGHT // 2 - 120))
    
    # Times
    winner_time_text = font_med.render(f"{winner_name}: {winner_time:.2f}s", True, winner_color)
    screen.blit(winner_time_text, (WIDTH // 2 - winner_time_text.get_width() // 2, HEIGHT // 2 - 30))
    
    if loser_time > 0:
        loser_name = "Player 2" if winner_name == "Player 1" else "Player 1"
        loser_color = COLOR_P2 if loser_name == "Player 2" else COLOR_P1
        loser_time_text = font_med.render(f"{loser_name}: {loser_time:.2f}s", True, loser_color)
        screen.blit(loser_time_text, (WIDTH // 2 - loser_time_text.get_width() // 2, HEIGHT // 2 + 20))
    
    button_width = 250
    button_height = 60
    
    play_again = Button(WIDTH // 2 - button_width - 20, HEIGHT // 2 + 100, 
                       button_width, button_height, "RACE AGAIN", (50, 150, 50), (70, 200, 70))
    
    menu_btn = Button(WIDTH // 2 + 20, HEIGHT // 2 + 100, 
                     button_width, button_height, "MAIN MENU", (100, 100, 150), (120, 120, 200))
    
    play_again.draw(screen)
    menu_btn.draw(screen)
    
    return play_again, menu_btn

# ==========================
# GAME INITIALIZATION
# ==========================
maze_walls = []
players = []
start_rect = None
finish_rect = None

def start_new_game():
    global maze_walls, players, start_rect, finish_rect, timer_start, winner
    
    # Generate new random maze
    maze_walls = generate_maze(MAZE_COLS, MAZE_ROWS)
    
    # Create players at opposite starting positions
    players = []
    
    # Player 1 (Blue) - Top-Left corner
    p1_controls = {
        'up': pygame.K_w,
        'down': pygame.K_s,
        'left': pygame.K_a,
        'right': pygame.K_d
    }
    players.append(RacePlayer(CELL_SIZE / 2, CELL_SIZE / 2, COLOR_P1, p1_controls, "Player 1"))
    
    # Player 2 (Pink) - Top-Right corner
    p2_controls = {
        'up': pygame.K_UP,
        'down': pygame.K_DOWN,
        'left': pygame.K_LEFT,
        'right': pygame.K_RIGHT
    }
    p2_x = (MAZE_COLS - 1) * CELL_SIZE
    players.append(RacePlayer(p2_x, CELL_SIZE / 2, COLOR_P2, p2_controls, "Player 2"))
    
    timer_start = pygame.time.get_ticks()
    winner = None

# ==========================
# MAIN GAME LOOP
# ==========================
running = True
mouse_clicked = False

print("🏁 2-Player Maze Race")
print("Player 1 (Blue): W/A/S/D")
print("Player 2 (Pink): Arrow Keys")
print("Race to the finish!")

while running:
    clock.tick(60)
    mouse_clicked = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_clicked = True
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state == "playing":
                    game_state = "menu"
                elif game_state == "settings":
                    game_state = "menu"
    
    mouse_pos = pygame.mouse.get_pos()
    
    # ==================
    # MAIN MENU
    # ==================
    if game_state == "menu":
        start_btn, quit_btn = draw_main_menu()
        
        for btn in [start_btn, quit_btn]:
            btn.is_hovered = btn.rect.collidepoint(mouse_pos)
        
        if start_btn.is_clicked(mouse_pos, mouse_clicked):
            game_state = "settings"
        
        if quit_btn.is_clicked(mouse_pos, mouse_clicked):
            running = False
    
    # ==================
    # SETTINGS MENU
    # ==================
    elif game_state == "settings":
        light_btn, dark_btn, start_btn, back_btn = draw_settings_menu()
        
        for btn in [light_btn, dark_btn, start_btn, back_btn]:
            btn.is_hovered = btn.rect.collidepoint(mouse_pos)
        
        if light_btn.is_clicked(mouse_pos, mouse_clicked):
            darkness_mode = "light"
        
        if dark_btn.is_clicked(mouse_pos, mouse_clicked):
            darkness_mode = "dark"
        
        if start_btn.is_clicked(mouse_pos, mouse_clicked):
            start_new_game()
            game_state = "playing"
        
        if back_btn.is_clicked(mouse_pos, mouse_clicked):
            game_state = "menu"
    
    # ==================
    # PLAYING
    # ==================
    elif game_state == "playing":
        keys = pygame.key.get_pressed()
        
        # Update players
        for player in players:
            dx, dy = player.handle_input(keys)
            player.move(dx, dy, maze_walls)
        
        # Check if players reached finish
        finish_x = (MAZE_COLS // 2 - 1) * CELL_SIZE
        finish_y = (MAZE_ROWS - 2) * CELL_SIZE
        finish_rect = pygame.Rect(finish_x, finish_y, CELL_SIZE * 2, CELL_SIZE * 2)
        
        current_time = (pygame.time.get_ticks() - timer_start) / 1000.0
        
        for player in players:
            if not player.finished and player.rect.colliderect(finish_rect):
                player.finished = True
                player.finish_time = current_time
                if winner is None:
                    winner = player.name
                    print(f"🏆 {player.name} finished first in {player.finish_time:.2f}s!")
        
        # Check if both finished
        if all(p.finished for p in players):
            elapsed_time = current_time
            game_state = "won"
        
        # Draw game
        screen.fill((30, 30, 30))
        p1_start_rect, p2_start_rect, finish_rect = draw_start_finish()
        draw_maze_walls(maze_walls)
        
        for player in players:
            player.draw(screen)
        
        # Apply darkness if dark mode
        if darkness_mode == "dark":
            draw_darkness_overlay(players, PLAYER_LIGHT_RADIUS)
        
        # Draw HUD
        elapsed = current_time
        font = pygame.font.Font(None, 36)
        
        # Time
        time_text = font.render(f"Time: {elapsed:.1f}s", True, (255, 255, 255))
        screen.blit(time_text, (10, 10))
        
        # Player positions
        p1_status = f"P1: {'FINISHED!' if players[0].finished else 'Racing...'}"
        p2_status = f"P2: {'FINISHED!' if players[1].finished else 'Racing...'}"
        
        p1_text = font.render(p1_status, True, COLOR_P1)
        p2_text = font.render(p2_status, True, COLOR_P2)
        
        screen.blit(p1_text, (10, 50))
        screen.blit(p2_text, (10, 90))
        
        # Dark mode indicator
        if darkness_mode == "dark":
            dark_text = font.render("🌙 DARK", True, (150, 150, 255))
            screen.blit(dark_text, (WIDTH - dark_text.get_width() - 10, 10))
        
        # ESC hint
        font_small = pygame.font.Font(None, 24)
        hint_text = font_small.render("ESC = Menu", True, (200, 200, 200))
        screen.blit(hint_text, (10, HEIGHT - 30))
    
    # ==================
    # VICTORY SCREEN
    # ==================
    elif game_state == "won":
        # Draw game in background
        screen.fill((30, 30, 30))
        p1_start_rect, p2_start_rect, finish_rect = draw_start_finish()
        draw_maze_walls(maze_walls)
        
        for player in players:
            player.draw(screen)
        
        if darkness_mode == "dark":
            draw_darkness_overlay(players, PLAYER_LIGHT_RADIUS)
        
        # Get winner and loser times
        winner_player = players[0] if players[0].name == winner else players[1]
        loser_player = players[1] if players[0].name == winner else players[0]
        
        # Draw victory overlay
        play_again, menu_btn = draw_victory_screen(winner, winner_player.finish_time, loser_player.finish_time)
        
        for btn in [play_again, menu_btn]:
            btn.is_hovered = btn.rect.collidepoint(mouse_pos)
        
        if play_again.is_clicked(mouse_pos, mouse_clicked):
            start_new_game()
            game_state = "playing"
        
        if menu_btn.is_clicked(mouse_pos, mouse_clicked):
            game_state = "menu"
    
    pygame.display.flip()

pygame.quit()