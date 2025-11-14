import pygame
import json
import os
import sys
import math
from player import Mario

pygame.init()

# =====================
# SETTINGS
# =====================
WIDTH, HEIGHT = 1200, 800
TILE_SIZE = 50

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mario Maze Game - Dark Levels")
clock = pygame.time.Clock()

# Tile types
TILE_EMPTY = 0
TILE_WALL = 1
TILE_START = 2
TILE_END = 3
TILE_FLASHLIGHT = 4  # NEW: Flashlight collectible

# Colors
COLOR_START = (0, 255, 0)
COLOR_END = (255, 0, 0)
COLOR_FLASHLIGHT = (255, 255, 0)

# Game state
game_state = "menu"
timer_start = 0
elapsed_time = 0
current_level_name = None
completed_levels = []

# Dark level settings
DARK_LEVEL_THRESHOLD = 5  # Levels after this become dark
BASE_LIGHT_RADIUS = 80  # Initial light radius for player
FLASHLIGHT_LIGHT_BONUS = 60  # Additional radius per flashlight

# Player light tracking
player_flashlights = 0  # Number of flashlights collected
player_light_radius = BASE_LIGHT_RADIUS

# ==========================
# PROGRESS MANAGEMENT
# ==========================
def load_completed_levels():
    if os.path.exists("progress.json"):
        try:
            with open("progress.json", "r") as f:
                data = json.load(f)
                return data.get("completed", [])
        except:
            return []
    return []

def save_completed_level(level_name):
    completed = load_completed_levels()
    if level_name not in completed:
        completed.append(level_name)
    
    with open("progress.json", "w") as f:
        json.dump({"completed": completed}, f)
    
    print(f"✅ Level {level_name} completed!")

def is_level_unlocked(level_name, all_levels):
    completed = load_completed_levels()
    
    if not all_levels or level_name == all_levels[0]:
        return True
    
    try:
        index = all_levels.index(level_name)
        if index > 0:
            previous_level = all_levels[index - 1]
            return previous_level in completed
    except ValueError:
        pass
    
    return False

def reset_progress():
    if os.path.exists("progress.json"):
        os.remove("progress.json")
    print("🗑️ Progress reset!")

def is_dark_level(level_name):
    """Check if this level should be dark"""
    try:
        # Extract number from level name (e.g., "level6" -> 6)
        import re
        numbers = re.findall(r'\d+', level_name)
        if numbers:
            level_num = int(numbers[0])
            return level_num > DARK_LEVEL_THRESHOLD
    except:
        pass
    return False

# ==========================
# LEVEL MANAGEMENT
# ==========================
def get_levels_folder():
    return "levels"

def list_levels():
    folder = get_levels_folder()
    if not os.path.exists(folder):
        return []
    
    levels = []
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            levels.append(filename[:-5])
    
    def natural_sort_key(s):
        import re
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', s)]
    
    return sorted(levels, key=natural_sort_key)

def load_level(level_name):
    folder = get_levels_folder()
    filepath = os.path.join(folder, f"{level_name}.json")
    
    if not os.path.exists(filepath):
        print(f"❌ Level not found: {level_name}")
        return None
    
    with open(filepath, "r") as f:
        data = json.load(f)
    
    grid = data["grid"]
    rows = data["rows"]
    cols = data["cols"]
    
    start_pos = None
    end_pos = None
    flashlight_positions = []
    
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] == TILE_START:
                start_pos = (col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2)
            elif grid[row][col] == TILE_END:
                end_pos = (col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2)
            elif grid[row][col] == TILE_FLASHLIGHT:
                flashlight_positions.append((col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2))
    
    if start_pos is None:
        start_pos = (WIDTH // 2, HEIGHT // 2)
    
    if end_pos is None:
        end_pos = (WIDTH - 100, HEIGHT - 100)
    
    return grid, rows, cols, start_pos, end_pos, flashlight_positions

# =====================
# LOAD BACKGROUND & WALLS
# =====================
try:
    background = pygame.image.load("background.png").convert()
except:
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill((100, 100, 100))

try:
    wall_img = pygame.image.load("wall.png").convert_alpha()
except:
    wall_img = pygame.Surface((TILE_SIZE, TILE_SIZE))
    wall_img.fill((150, 75, 0))

bg_width = background.get_width() * 2
bg_height = background.get_height() * 2
background = pygame.transform.scale(background, (bg_width, bg_height))
wall_img = pygame.transform.scale(wall_img, (TILE_SIZE, TILE_SIZE))

end_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
pygame.draw.rect(end_img, COLOR_END, (0, 0, TILE_SIZE, TILE_SIZE))
pygame.draw.circle(end_img, (255, 255, 255), (TILE_SIZE//2, TILE_SIZE//2), TILE_SIZE//3)
font_marker = pygame.font.Font(None, 48)
end_text = font_marker.render("★", True, (255, 255, 0))
end_img.blit(end_text, (TILE_SIZE//2 - end_text.get_width()//2, TILE_SIZE//2 - end_text.get_height()//2))

# Create flashlight item image
flashlight_item_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
# Draw flashlight body
pygame.draw.rect(flashlight_item_img, (200, 200, 0), (TILE_SIZE//2 - 8, TILE_SIZE//2 - 15, 16, 25))
# Draw flashlight head
pygame.draw.circle(flashlight_item_img, (255, 255, 150), (TILE_SIZE//2, TILE_SIZE//2 - 15), 10)
# Draw light beam
for i in range(5):
    alpha = 150 - i * 30
    beam_y = TILE_SIZE//2 + 10 + i * 3
    beam_width = 20 + i * 4
    pygame.draw.ellipse(flashlight_item_img, (255, 255, 200, alpha), 
                       (TILE_SIZE//2 - beam_width//2, beam_y, beam_width, 8))

# ==========================
# FLASHLIGHT CLASS
# ==========================
class Flashlight:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x - 20, y - 20, 40, 40)
        self.collected = False
        self.pulse_offset = 0
    
    def update(self):
        # Pulsing animation
        self.pulse_offset = (self.pulse_offset + 0.1) % (2 * math.pi)
    
    def draw(self, surface, camera_x, camera_y):
        if not self.collected:
            # Draw with pulsing effect
            pulse_scale = 1.0 + math.sin(self.pulse_offset) * 0.1
            scaled_size = int(TILE_SIZE * pulse_scale)
            scaled_img = pygame.transform.scale(flashlight_item_img, (scaled_size, scaled_size))
            draw_x = self.x - camera_x - scaled_size // 2
            draw_y = self.y - camera_y - scaled_size // 2
            surface.blit(scaled_img, (draw_x, draw_y))
            
            # Draw glow effect
            glow_radius = int(30 + math.sin(self.pulse_offset) * 5)
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 255, 0, 50), (glow_radius, glow_radius), glow_radius)
            surface.blit(glow_surf, (self.x - camera_x - glow_radius, self.y - camera_y - glow_radius))
    
    def check_collection(self, player_rect):
        if not self.collected and self.rect.colliderect(player_rect):
            self.collected = True
            return True
        return False

# ==========================
# MAP PREVIEW CLASS
# ==========================
class MapPreviewButton:
    def __init__(self, x, y, width, height, level_name, grid, rows, cols, locked=False, completed=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.level_name = level_name
        self.grid = grid
        self.rows = rows
        self.cols = cols
        self.locked = locked
        self.completed = completed
        self.is_hovered = False
        self.is_dark = is_dark_level(level_name)
        self.preview_surface = self.create_preview()
    
    def create_preview(self):
        """Create a miniature preview of the level map"""
        preview = pygame.Surface((self.rect.width - 10, self.rect.height - 40), pygame.SRCALPHA)
        
        if self.grid is None:
            return preview
        
        scale_x = (self.rect.width - 10) / (self.cols * TILE_SIZE)
        scale_y = (self.rect.height - 40) / (self.rows * TILE_SIZE)
        scale = min(scale_x, scale_y)
        
        map_width = self.cols * TILE_SIZE * scale
        map_height = self.rows * TILE_SIZE * scale
        offset_x = ((self.rect.width - 10) - map_width) // 2
        offset_y = ((self.rect.height - 40) - map_height) // 2
        
        for row in range(self.rows):
            for col in range(self.cols):
                tile = self.grid[row][col]
                if tile != TILE_EMPTY:
                    x = int(offset_x + col * TILE_SIZE * scale)
                    y = int(offset_y + row * TILE_SIZE * scale)
                    w = max(1, int(TILE_SIZE * scale))
                    h = max(1, int(TILE_SIZE * scale))
                    
                    if tile == TILE_WALL:
                        color = (150, 75, 25) if not self.locked else (80, 80, 80)
                    elif tile == TILE_START:
                        color = (0, 255, 0) if not self.locked else (100, 100, 100)
                    elif tile == TILE_END:
                        color = (255, 0, 0) if not self.locked else (120, 120, 120)
                    elif tile == TILE_FLASHLIGHT:
                        color = (255, 255, 0) if not self.locked else (150, 150, 0)
                    
                    pygame.draw.rect(preview, color, (x, y, w, h))
        
        # Apply dark overlay if it's a dark level
        if self.is_dark and not self.locked:
            dark_overlay = pygame.Surface((self.rect.width - 10, self.rect.height - 40), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 120))
            preview.blit(dark_overlay, (0, 0))
        
        # Apply gray overlay if locked
        if self.locked:
            gray_overlay = pygame.Surface((self.rect.width - 10, self.rect.height - 40), pygame.SRCALPHA)
            gray_overlay.fill((100, 100, 100, 150))
            preview.blit(gray_overlay, (0, 0))
        
        return preview
    
    def draw(self, surface):
        if self.locked:
            bg_color = (60, 60, 60)
            border_color = (100, 100, 100)
        elif self.completed:
            bg_color = (40, 80, 40)
            border_color = (0, 255, 0)
        elif self.is_dark:
            bg_color = (30, 30, 50) if not self.is_hovered else (50, 50, 70)
            border_color = (200, 200, 255)
        else:
            bg_color = (50, 50, 80) if not self.is_hovered else (70, 70, 100)
            border_color = (255, 255, 255)
        
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=8)
        border_width = 4 if self.is_hovered and not self.locked else 2
        pygame.draw.rect(surface, border_color, self.rect, border_width, border_radius=8)
        
        surface.blit(self.preview_surface, (self.rect.x + 5, self.rect.y + 5))
        
        font = pygame.font.Font(None, 24)
        text_color = (150, 150, 150) if self.locked else (255, 255, 255)
        name_surf = font.render(self.level_name, True, text_color)
        name_rect = name_surf.get_rect(center=(self.rect.centerx, self.rect.bottom - 15))
        surface.blit(name_surf, name_rect)
        
        # Draw dark level indicator
        if self.is_dark and not self.locked:
            moon_font = pygame.font.Font(None, 30)
            moon_text = moon_font.render("🌙", True, (200, 200, 255))
            surface.blit(moon_text, (self.rect.left + 5, self.rect.top + 5))
        
        if self.locked:
            lock_font = pygame.font.Font(None, 48)
            lock_text = lock_font.render("🔒", True, (200, 200, 0))
            lock_rect = lock_text.get_rect(center=(self.rect.centerx, self.rect.centery))
            surface.blit(lock_text, lock_rect)
        
        if self.completed and not self.locked:
            check_font = pygame.font.Font(None, 36)
            check_text = check_font.render("✓", True, (0, 255, 0))
            surface.blit(check_text, (self.rect.right - 30, self.rect.top + 5))
    
    def is_clicked(self, mouse_pos, mouse_clicked):
        if not self.locked and self.rect.collidepoint(mouse_pos) and mouse_clicked:
            return True
        return False

# ==========================
# BUTTON CLASS
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
        
        font = pygame.font.Font(None, 32)
        text_surf = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def is_clicked(self, mouse_pos, mouse_clicked):
        if self.rect.collidepoint(mouse_pos) and mouse_clicked:
            return True
        return False

# =====================
# GAME FUNCTIONS
# =====================
def get_walls(grid, rows, cols):
    walls = []
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] == TILE_WALL:
                wall_rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                walls.append(wall_rect)
    return walls

def get_end_rect(grid, rows, cols):
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] == TILE_END:
                return pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    return None

def draw_scrolling_background(camera_x, camera_y):
    offset_x = -camera_x % bg_width
    offset_y = -camera_y % bg_height
    screen.blit(background, (offset_x - bg_width, offset_y - bg_height))
    screen.blit(background, (offset_x, offset_y - bg_height))
    screen.blit(background, (offset_x - bg_width, offset_y))
    screen.blit(background, (offset_x, offset_y))

def draw_level(grid, rows, cols, camera_x, camera_y):
    start_col = camera_x // TILE_SIZE
    end_col = (camera_x + WIDTH) // TILE_SIZE + 1
    start_row = camera_y // TILE_SIZE
    end_row = (camera_y + HEIGHT) // TILE_SIZE + 1

    for row in range(start_row, end_row):
        for col in range(start_col, end_col):
            if 0 <= row < rows and 0 <= col < cols:
                tile = grid[row][col]
                if tile == TILE_WALL:
                    screen.blit(wall_img, (col * TILE_SIZE - camera_x, row * TILE_SIZE - camera_y))
                elif tile == TILE_END:
                    screen.blit(end_img, (col * TILE_SIZE - camera_x, row * TILE_SIZE - camera_y))

def cast_ray(start_x, start_y, angle, max_distance, grid, rows, cols):
    """Cast a single ray and return the distance to the nearest wall"""
    dx = math.cos(angle)
    dy = math.sin(angle)
    
    # Use larger steps for better performance
    step_size = 2
    
    for distance in range(0, int(max_distance), step_size):
        check_x = start_x + dx * distance
        check_y = start_y + dy * distance
        
        # Convert to grid coordinates
        grid_x = int(check_x // TILE_SIZE)
        grid_y = int(check_y // TILE_SIZE)
        
        # Check boundaries
        if grid_x < 0 or grid_x >= cols or grid_y < 0 or grid_y >= rows:
            return distance
        
        # Check if wall
        if grid[grid_y][grid_x] == TILE_WALL:
            return distance
    
    return max_distance

def draw_darkness_overlay(player_x, player_y, light_radius):
    """Draw darkness with realistic light that's blocked by walls"""
    # Create darkness overlay
    darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, 240))
    
    # Calculate player's world position
    world_player_x = player_x + camera_x
    world_player_y = player_y + camera_y
    
    # Cast rays to create light polygon
    num_rays = 180  # 180 rays for balance between performance and smoothness
    visible_points = [(player_x, player_y)]  # Start with player position
    
    for i in range(num_rays + 1):
        angle = (i / num_rays) * 2 * math.pi
        
        # Cast ray from player position
        hit_distance = cast_ray(world_player_x, world_player_y, angle, light_radius, grid, ROWS, COLS)
        
        # Convert back to screen coordinates
        screen_x = player_x + math.cos(angle) * hit_distance
        screen_y = player_y + math.sin(angle) * hit_distance
        
        visible_points.append((screen_x, screen_y))
    
    # Draw the lit area with gradient
    if len(visible_points) > 2:
        # Draw multiple layers for smooth gradient
        num_layers = 8
        for layer in range(num_layers, 0, -1):
            ratio = layer / num_layers
            alpha = int(230 * (1 - ratio))
            
            # Scale points toward player
            scaled_points = [(player_x, player_y)]
            for px, py in visible_points[1:]:
                scaled_x = player_x + (px - player_x) * ratio
                scaled_y = player_y + (py - player_y) * ratio
                scaled_points.append((scaled_x, scaled_y))
            
            # Create a temporary surface for this layer
            layer_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            if len(scaled_points) > 2:
                pygame.draw.polygon(layer_surf, (0, 0, 0, alpha), scaled_points)
            
            # Subtract from darkness
            darkness.blit(layer_surf, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    
    # Draw to screen
    screen.blit(darkness, (0, 0))

def update_camera(player, rows, cols):
    camera_x = player.rect.centerx - WIDTH // 2
    camera_y = player.rect.centery - HEIGHT // 2
    
    camera_x = max(0, min(camera_x, cols * TILE_SIZE - WIDTH))
    camera_y = max(0, min(camera_y, rows * TILE_SIZE - HEIGHT))
    
    return camera_x, camera_y

def draw_main_menu():
    screen.fill((40, 40, 60))
    
    font_title = pygame.font.Font(None, 72)
    title_text = font_title.render("MARIO MAZE", True, (255, 255, 0))
    title_rect = title_text.get_rect(center=(WIDTH // 2, 100))
    screen.blit(title_text, title_rect)
    
    # Add subtitle about dark levels
    font_subtitle = pygame.font.Font(None, 32)
    subtitle_text = font_subtitle.render("🌙 Dark levels after Level 5! 💡", True, (200, 200, 255))
    subtitle_rect = subtitle_text.get_rect(center=(WIDTH // 2, 160))
    screen.blit(subtitle_text, subtitle_rect)
    
    button_width = 300
    button_height = 60
    button_x = WIDTH // 2 - button_width // 2
    
    play_button = Button(button_x, 250, button_width, button_height, 
                        "PLAY", (50, 150, 50), (70, 200, 70))
    
    reset_button = Button(button_x, 340, button_width, button_height, 
                         "RESET PROGRESS", (150, 50, 50), (200, 70, 70))
    
    quit_button = Button(button_x, 430, button_width, button_height, 
                        "QUIT", (50, 50, 150), (70, 70, 200))
    
    play_button.draw(screen)
    reset_button.draw(screen)
    quit_button.draw(screen)
    
    return play_button, reset_button, quit_button

def draw_level_select(all_levels):
    screen.fill((40, 40, 60))
    
    font_title = pygame.font.Font(None, 60)
    title_text = font_title.render("SELECT LEVEL", True, (255, 255, 0))
    title_rect = title_text.get_rect(center=(WIDTH // 2, 50))
    screen.blit(title_text, title_rect)
    
    if not all_levels:
        font_error = pygame.font.Font(None, 36)
        error_text = font_error.render("No levels found! Create levels in the editor.", True, (255, 100, 100))
        error_rect = error_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(error_text, error_rect)
        
        back_button = Button(WIDTH // 2 - 100, HEIGHT - 100, 200, 50, "BACK", (100, 100, 100), (150, 150, 150))
        back_button.draw(screen)
        return [], back_button
    
    buttons = []
    button_width = 220
    button_height = 200
    buttons_per_row = 4
    padding = 20
    
    total_width = buttons_per_row * button_width + (buttons_per_row - 1) * padding
    start_x = (WIDTH - total_width) // 2
    start_y = 120
    
    for i, level_name in enumerate(all_levels):
        row = i // buttons_per_row
        col = i % buttons_per_row
        x = start_x + col * (button_width + padding)
        y = start_y + row * (button_height + padding)
        
        level_data = load_level(level_name)
        if level_data:
            grid, rows, cols, _, _, _ = level_data
        else:
            grid, rows, cols = None, 0, 0
        
        locked = not is_level_unlocked(level_name, all_levels)
        completed = level_name in completed_levels
        
        button = MapPreviewButton(x, y, button_width, button_height, 
                                   level_name, grid, rows, cols, locked, completed)
        button.level_name = level_name
        buttons.append(button)
        button.draw(screen)
    
    back_button = Button(WIDTH // 2 - 100, HEIGHT - 70, 200, 50, "BACK", (100, 100, 100), (150, 150, 150))
    back_button.draw(screen)
    
    font_small = pygame.font.Font(None, 24)
    instr_text = font_small.render("Complete levels in order to unlock the next | 🌙 = Dark Level", True, (200, 200, 200))
    screen.blit(instr_text, (WIDTH // 2 - instr_text.get_width() // 2, HEIGHT - 100))
    
    return buttons, back_button

def draw_victory_screen(elapsed_time, level_name, all_levels):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    font_big = pygame.font.Font(None, 72)
    font_small = pygame.font.Font(None, 36)
    
    victory_text = font_big.render("🎉 LEVEL COMPLETE! 🎉", True, (255, 255, 0))
    time_text = font_small.render(f"Time: {elapsed_time:.2f} seconds", True, (255, 255, 255))
    flashlights_text = font_small.render(f"Flashlights collected: {player_flashlights}", True, (255, 255, 100))
    
    screen.blit(victory_text, (WIDTH // 2 - victory_text.get_width() // 2, HEIGHT // 2 - 140))
    screen.blit(time_text, (WIDTH // 2 - time_text.get_width() // 2, HEIGHT // 2 - 70))
    screen.blit(flashlights_text, (WIDTH // 2 - flashlights_text.get_width() // 2, HEIGHT // 2 - 30))
    
    try:
        current_index = all_levels.index(level_name)
        has_next = current_index < len(all_levels) - 1
        
        # Check if next level is dark
        if has_next:
            next_level = all_levels[current_index + 1]
            if is_dark_level(next_level):
                warning_font = pygame.font.Font(None, 30)
                warning_text = warning_font.render("⚠️ Next level is DARK! Collect flashlights! 💡", True, (255, 200, 100))
                screen.blit(warning_text, (WIDTH // 2 - warning_text.get_width() // 2, HEIGHT // 2 + 10))
    except:
        has_next = False
    
    button_width = 250
    button_height = 60
    button_x = WIDTH // 2 - button_width // 2
    
    if has_next:
        next_button = Button(button_x, HEIGHT // 2 + 60, button_width, button_height,
                           "NEXT LEVEL", (50, 150, 50), (70, 200, 70))
        next_button.draw(screen)
    else:
        next_button = None
        
        congrats_font = pygame.font.Font(None, 48)
        congrats_text = congrats_font.render("All levels completed!", True, (100, 255, 100))
        screen.blit(congrats_text, (WIDTH // 2 - congrats_text.get_width() // 2, HEIGHT // 2 + 60))
    
    menu_button = Button(button_x, HEIGHT // 2 + (140 if has_next else 120), button_width, button_height,
                        "LEVEL SELECT", (100, 100, 150), (120, 120, 200))
    menu_button.draw(screen)
    
    return next_button, menu_button

# =====================
# INITIALIZE
# =====================
print("🎮 Mario Maze Game - Dark Levels & Flashlights")
print("✅ Loading game...")

all_levels = list_levels()
completed_levels = load_completed_levels()

if all_levels:
    print(f"📂 Found {len(all_levels)} levels: {', '.join(all_levels)}")
    print(f"✓ Completed: {len(completed_levels)} levels")
    print(f"🌙 Dark levels start after level {DARK_LEVEL_THRESHOLD}")
else:
    print("⚠️ No levels found! Create levels in the editor first.")

# Game variables
player = None
grid = None
ROWS = COLS = 0
walls = []
end_rect = None
start_pos = end_pos = None
camera_x = camera_y = 0
flashlights = []
is_current_level_dark = False

# =====================
# MAIN LOOP
# =====================
running = True
mouse_clicked = False
level_buttons = []
back_button = None
next_button = None
menu_button = None

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
                    game_state = "level_select"
                elif game_state == "level_select":
                    game_state = "menu"
    
    mouse_pos = pygame.mouse.get_pos()
    
    if game_state == "menu":
        play_btn, reset_btn, quit_btn = draw_main_menu()
        
        for btn in [play_btn, reset_btn, quit_btn]:
            btn.is_hovered = btn.rect.collidepoint(mouse_pos)
        
        if play_btn.is_clicked(mouse_pos, mouse_clicked):
            game_state = "level_select"
            all_levels = list_levels()
        
        if reset_btn.is_clicked(mouse_pos, mouse_clicked):
            reset_progress()
            completed_levels = []
            print("🔄 Progress reset!")
        
        if quit_btn.is_clicked(mouse_pos, mouse_clicked):
            running = False
    
    elif game_state == "level_select":
        level_buttons, back_button = draw_level_select(all_levels)
        
        for btn in level_buttons:
            btn.is_hovered = btn.rect.collidepoint(mouse_pos)
            if btn.is_clicked(mouse_pos, mouse_clicked):
                current_level_name = btn.level_name
                level_data = load_level(current_level_name)
                
                if level_data:
                    grid, ROWS, COLS, start_pos, end_pos, flashlight_positions = level_data
                    player = Mario(start_pos[0], start_pos[1])
                    walls = get_walls(grid, ROWS, COLS)
                    end_rect = get_end_rect(grid, ROWS, COLS)
                    
                    # Create flashlight objects
                    flashlights = [Flashlight(x, y) for x, y in flashlight_positions]
                    
                    # Reset player light
                    player_flashlights = 0
                    player_light_radius = BASE_LIGHT_RADIUS
                    
                    # Check if this is a dark level
                    is_current_level_dark = is_dark_level(current_level_name)
                    
                    game_state = "playing"
                    timer_start = pygame.time.get_ticks()
                    elapsed_time = 0
                    
                    if is_current_level_dark:
                        print(f"🌙 Starting DARK level: {current_level_name}")
                    else:
                        print(f"🎮 Starting level: {current_level_name}")
        
        if back_button:
            back_button.is_hovered = back_button.rect.collidepoint(mouse_pos)
            if back_button.is_clicked(mouse_pos, mouse_clicked):
                game_state = "menu"
    
    elif game_state == "playing":
        player.update(walls)
        camera_x, camera_y = update_camera(player, ROWS, COLS)
        
        # Update and check flashlight collection
        for flashlight in flashlights:
            flashlight.update()
            if flashlight.check_collection(player.rect):
                player_flashlights += 1
                player_light_radius = BASE_LIGHT_RADIUS + (player_flashlights * FLASHLIGHT_LIGHT_BONUS)
                print(f"💡 Flashlight collected! Total: {player_flashlights} | Light radius: {player_light_radius}")
        
        # Check if player reached the end
        if end_rect and player.collision_rect.colliderect(end_rect):
            elapsed_time = (pygame.time.get_ticks() - timer_start) / 1000.0
            save_completed_level(current_level_name)
            completed_levels = load_completed_levels()
            game_state = "won"
            print(f"🎉 Level {current_level_name} completed in {elapsed_time:.2f}s!")
        else:
            elapsed_time = (pygame.time.get_ticks() - timer_start) / 1000.0
        
        # Draw game
        draw_scrolling_background(camera_x, camera_y)
        draw_level(grid, ROWS, COLS, camera_x, camera_y)
        
        # Draw flashlights
        for flashlight in flashlights:
            flashlight.draw(screen, camera_x, camera_y)
        
        player.draw(screen, camera_x, camera_y)
        
        # Apply darkness overlay if dark level
        if is_current_level_dark:
            player_screen_x = player.rect.centerx - camera_x
            player_screen_y = player.rect.centery - camera_y
            draw_darkness_overlay(player_screen_x, player_screen_y, player_light_radius)
        
        # Draw HUD
        font = pygame.font.Font(None, 36)
        level_text = font.render(f"Level: {current_level_name}", True, (255, 255, 255))
        time_text = font.render(f"Time: {elapsed_time:.2f}s", True, (255, 255, 255))
        screen.blit(level_text, (10, 10))
        screen.blit(time_text, (10, 50))
        
        # Show flashlight count if dark level
        if is_current_level_dark:
            flashlight_text = font.render(f"💡 Flashlights: {player_flashlights}", True, (255, 255, 100))
            light_radius_text = font.render(f"Light: {player_light_radius}px", True, (200, 200, 255))
            screen.blit(flashlight_text, (10, 90))
            screen.blit(light_radius_text, (10, 130))
            
            # Dark level indicator
            dark_indicator = font.render("🌙 DARK LEVEL", True, (150, 150, 255))
            screen.blit(dark_indicator, (WIDTH - dark_indicator.get_width() - 10, 10))
        
        # ESC hint
        font_small = pygame.font.Font(None, 24)
        hint_text = font_small.render("ESC to level select", True, (200, 200, 200))
        screen.blit(hint_text, (10, HEIGHT - 30))
    
    elif game_state == "won":
        # Still draw the game in background
        draw_scrolling_background(camera_x, camera_y)
        draw_level(grid, ROWS, COLS, camera_x, camera_y)
        
        for flashlight in flashlights:
            flashlight.draw(screen, camera_x, camera_y)
        
        player.draw(screen, camera_x, camera_y)
        
        if is_current_level_dark:
            player_screen_x = player.rect.centerx - camera_x
            player_screen_y = player.rect.centery - camera_y
            draw_darkness_overlay(player_screen_x, player_screen_y, player_light_radius)
        
        # Draw victory screen
        next_button, menu_button = draw_victory_screen(elapsed_time, current_level_name, all_levels)
        
        for btn in [next_button, menu_button]:
            if btn:
                btn.is_hovered = btn.rect.collidepoint(mouse_pos)
        
        if next_button and next_button.is_clicked(mouse_pos, mouse_clicked):
            try:
                current_index = all_levels.index(current_level_name)
                next_level_name = all_levels[current_index + 1]
                current_level_name = next_level_name
                
                level_data = load_level(current_level_name)
                if level_data:
                    grid, ROWS, COLS, start_pos, end_pos, flashlight_positions = level_data
                    player = Mario(start_pos[0], start_pos[1])
                    walls = get_walls(grid, ROWS, COLS)
                    end_rect = get_end_rect(grid, ROWS, COLS)
                    
                    # Create flashlight objects
                    flashlights = [Flashlight(x, y) for x, y in flashlight_positions]
                    
                    # Reset player light
                    player_flashlights = 0
                    player_light_radius = BASE_LIGHT_RADIUS
                    
                    # Check if this is a dark level
                    is_current_level_dark = is_dark_level(current_level_name)
                    
                    game_state = "playing"
                    timer_start = pygame.time.get_ticks()
                    elapsed_time = 0
                    
                    if is_current_level_dark:
                        print(f"🌙 Starting DARK level: {current_level_name}")
                    else:
                        print(f"🎮 Starting next level: {current_level_name}")
            except:
                game_state = "level_select"
        
        if menu_button and menu_button.is_clicked(mouse_pos, mouse_clicked):
            game_state = "level_select"
    
    pygame.display.flip()

pygame.quit()
sys.exit()