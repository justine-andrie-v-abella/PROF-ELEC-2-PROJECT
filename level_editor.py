import pygame
import json
import os
import sys

pygame.init()

# =====================
# SETTINGS
# =====================
WIDTH, HEIGHT = 800, 600
TILE_SIZE = 50
# Set level size to exactly 5x7 sections
SECTION_COLS = 5  # 5 sections wide
SECTION_ROWS = 7  # 7 sections tall
ROWS = SECTION_ROWS * (HEIGHT // TILE_SIZE)  # Calculate total rows based on sections
COLS = SECTION_COLS * (WIDTH // TILE_SIZE)   # Calculate total columns based on sections

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Level Editor - Enhanced with Flashlight Items")
clock = pygame.time.Clock()

# Zoom settings
ZOOM_LEVEL = 1.0
MIN_ZOOM = 0.25
MAX_ZOOM = 3.0
ZOOM_STEP = 0.25

# Special tiles
TILE_EMPTY = 0
TILE_WALL = 1
TILE_START = 2
TILE_END = 3
TILE_FLASHLIGHT = 4  # NEW: Flashlight item

# Colors for special tiles
COLOR_START = (0, 255, 0)  # Green for start
COLOR_END = (255, 0, 0)    # Red for end
COLOR_FLASHLIGHT = (255, 255, 0)  # Yellow for flashlight

# Improved Minimap settings
MINIMAP_WIDTH = 100
MINIMAP_HEIGHT = 100
MINIMAP_POS = (WIDTH - MINIMAP_WIDTH - 10, 10)
MINIMAP_BG_COLOR = (30, 30, 30, 230)
MINIMAP_BORDER_COLOR = (255, 255, 255)
MINIMAP_WALL_COLOR = (200, 100, 50)
MINIMAP_PLAYER_COLOR = (0, 255, 255)
MINIMAP_VIEW_COLOR = (255, 255, 0, 150)
MINIMAP_GRID_COLOR = (80, 80, 80, 100)
MINIMAP_START_COLOR = (0, 255, 0)  # Green
MINIMAP_END_COLOR = (255, 0, 0)    # Red
MINIMAP_FLASHLIGHT_COLOR = (255, 255, 0)  # Yellow

# Edit mode settings
EDIT_MODE = False
EDIT_MODE_COLOR = (255, 100, 100)

# Camera panning
camera_x = 0
camera_y = 0
panning = False
last_mouse_pos = (0, 0)

# Level naming
current_level_name = "level1"
input_mode = False
input_text = ""
input_mode_type = ""  # "name" or "load" or "delete"

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
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=8)
        
        font = pygame.font.Font(None, 28)
        text_surf = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def is_clicked(self, mouse_pos, mouse_clicked):
        if self.rect.collidepoint(mouse_pos) and mouse_clicked:
            return True
        return False

# ==========================
# SMART CROP FUNCTION
# ==========================
def crop_surface(surface):
    """Automatically crops transparent or empty edges from a surface."""
    rect = surface.get_bounding_rect(min_alpha=1)
    if rect.width == 0 or rect.height == 0:
        return surface
    cropped = pygame.Surface(rect.size, pygame.SRCALPHA)
    cropped.blit(surface, (0, 0), rect)
    return cropped

# ==========================
# FRAME LOADER (AUTO SLICE)
# ==========================
def load_frames(sprite_sheet_path, frame_count):
    try:
        sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        print(f"✅ Successfully loaded: {sprite_sheet_path}")
    except pygame.error as e:
        print(f"❌ Could not load {sprite_sheet_path}: {e}")
        frames = []
        for i in range(frame_count):
            fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
            color = (100 + i * 20, 100, 200)
            pygame.draw.circle(fallback, color, (16, 16), 8)
            frames.append(fallback)
        return frames

    if sprite_sheet.get_width() > 0 and sprite_sheet.get_height() > 0:
        bg_color = sprite_sheet.get_at((0, 0))
        sprite_sheet.lock()
        for x in range(sprite_sheet.get_width()):
            for y in range(sprite_sheet.get_height()):
                r, g, b, a = sprite_sheet.get_at((x, y))
                if abs(r - bg_color.r) < 10 and abs(g - bg_color.g) < 10 and abs(b - bg_color.b) < 10 and a > 0:
                    sprite_sheet.set_at((x, y), (r, g, b, 0))
        sprite_sheet.unlock()

    sheet_width, sheet_height = sprite_sheet.get_size()
    frame_width = sheet_width // frame_count
    frame_height = sheet_height

    frames = []
    for i in range(frame_count):
        raw_frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
        raw_frame.blit(sprite_sheet, (0, 0), (i * frame_width, 0, frame_width, frame_height))
        cropped_frame = crop_surface(raw_frame)
        frames.append(cropped_frame)
    
    return frames

# =====================
# LOAD BACKGROUND & WALLS
# =====================
try:
    background = pygame.image.load("background.png").convert()
except:
    print("⚠️ Could not load background.png, using fallback")
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill((100, 100, 100))

try:
    wall_img = pygame.image.load("wall.png").convert_alpha()
except:
    print("⚠️ Could not load wall.png, using fallback")
    wall_img = pygame.Surface((TILE_SIZE, TILE_SIZE))
    wall_img.fill((150, 75, 0))

# Scale background
bg_width = background.get_width() * 2
bg_height = background.get_height() * 2
background = pygame.transform.scale(background, (bg_width, bg_height))
wall_img = pygame.transform.scale(wall_img, (TILE_SIZE, TILE_SIZE))

# Create start and end tiles
start_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
pygame.draw.rect(start_img, COLOR_START, (0, 0, TILE_SIZE, TILE_SIZE))
pygame.draw.circle(start_img, (255, 255, 255), (TILE_SIZE//2, TILE_SIZE//2), TILE_SIZE//3)
font_marker = pygame.font.Font(None, 36)
start_text = font_marker.render("S", True, (0, 0, 0))
start_img.blit(start_text, (TILE_SIZE//2 - start_text.get_width()//2, TILE_SIZE//2 - start_text.get_height()//2))

end_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
pygame.draw.rect(end_img, COLOR_END, (0, 0, TILE_SIZE, TILE_SIZE))
pygame.draw.circle(end_img, (255, 255, 255), (TILE_SIZE//2, TILE_SIZE//2), TILE_SIZE//3)
end_text = font_marker.render("E", True, (0, 0, 0))
end_img.blit(end_text, (TILE_SIZE//2 - end_text.get_width()//2, TILE_SIZE//2 - end_text.get_height()//2))

# Create flashlight tile
flashlight_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
pygame.draw.rect(flashlight_img, COLOR_FLASHLIGHT, (0, 0, TILE_SIZE, TILE_SIZE))
# Draw flashlight icon
pygame.draw.rect(flashlight_img, (200, 200, 0), (TILE_SIZE//2 - 8, TILE_SIZE//2 - 15, 16, 25))
pygame.draw.circle(flashlight_img, (255, 255, 150), (TILE_SIZE//2, TILE_SIZE//2 - 15), 10)
# Light beam
for i in range(5):
    alpha = 100 - i * 20
    beam_color = (255, 255, 200, alpha)
    beam_surf = pygame.Surface((20 + i * 4, 8), pygame.SRCALPHA)
    beam_surf.fill(beam_color)
    flashlight_img.blit(beam_surf, (TILE_SIZE//2 - (10 + i * 2), TILE_SIZE//2 + 10 + i * 3))
flashlight_text = font_marker.render("F", True, (0, 0, 0))
flashlight_img.blit(flashlight_text, (TILE_SIZE//2 - flashlight_text.get_width()//2, TILE_SIZE//2 + 8))

# ==========================
# PLAYER CLASS
# ==========================
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.scaled_frames_cache = {}
        
        possible_idle_files = ["slime_idle.png", "slime_idle.jpg", "idle.png", "idle.jpg", "player_idle.png"]
        possible_walk_files = ["slime_walk.png", "slime_walk.jpg", "walk.png", "walk.jpg", "player_walk.png"]
        
        self.idle_frames = None
        for filename in possible_idle_files:
            if os.path.exists(filename):
                self.idle_frames = load_frames(filename, 8)
                break
        
        self.walk_frames = None
        for filename in possible_walk_files:
            if os.path.exists(filename):
                self.walk_frames = load_frames(filename, 8)
                break
        
        if self.idle_frames is None:
            self.idle_frames = []
            for i in range(8):
                fallback = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.circle(fallback, (100, 200, 100), (12, 12), 8)
                self.idle_frames.append(fallback)
        
        if self.walk_frames is None:
            self.walk_frames = []
            for i in range(8):
                fallback = pygame.Surface((24, 24), pygame.SRCALPHA)
                bounce_offset = abs(4 - (i % 8)) - 2
                pygame.draw.circle(fallback, (100, 100, 200), (12, 12 + bounce_offset), 6)
                self.walk_frames.append(fallback)
        
        self.frame_index = 0
        self.animation_speed = 0.15
        self.last_update = pygame.time.get_ticks()
        self.state = "idle"
        self.facing_right = True
        self.direction = pygame.Vector2(0, 0)
        self.is_moving = False
        self.speed = 3
        self.collision_buffer = 5
        self.scale_factor = 0.4
        
        self.image = self.idle_frames[0]
        self.image = self.scale_frame(self.image)
        self.rect = self.image.get_rect(center=(x, y))
        self.collision_rect = pygame.Rect(0, 0, self.rect.width * 0.6, self.rect.height * 0.6)
        self.collision_rect.center = self.rect.center
    
    def scale_frame(self, frame):
        key = id(frame)
        if key not in self.scaled_frames_cache:
            new_width = max(12, int(frame.get_width() * self.scale_factor))
            new_height = max(12, int(frame.get_height() * self.scale_factor))
            scaled = pygame.transform.scale(frame, (new_width, new_height))
            self.scaled_frames_cache[key] = scaled
        return self.scaled_frames_cache[key]
    
    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = keys[pygame.K_d] - keys[pygame.K_a]
        self.direction.y = keys[pygame.K_s] - keys[pygame.K_w]
        
        if self.direction.length() > 0:
            self.direction = self.direction.normalize()
        
        if self.direction.x > 0:
            self.facing_right = True
        elif self.direction.x < 0:
            self.facing_right = False
        
        self.is_moving = (self.direction.x != 0 or self.direction.y != 0)
    
    def animate(self):
        now = pygame.time.get_ticks()
        frames = self.idle_frames if self.state == "idle" else self.walk_frames
        
        if len(frames) == 0:
            return
        
        if now - self.last_update > self.animation_speed * 1000:
            self.last_update = now
            self.frame_index = (self.frame_index + 1) % len(frames)
        
        frame = frames[int(self.frame_index)]
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)
        
        self.image = self.scale_frame(frame)
        old_center = self.rect.center
        self.rect = self.image.get_rect(center=old_center)
        self.collision_rect = pygame.Rect(0, 0, self.rect.width * 0.6, self.rect.height * 0.6)
        self.collision_rect.center = self.rect.center
    
    def move(self, walls):
        old_x, old_y = self.rect.x, self.rect.y
        dx = self.direction.x * self.speed
        dy = self.direction.y * self.speed
        
        self.rect.x += dx
        self.collision_rect.centerx = self.rect.centerx
        
        horizontal_collision = False
        vertical_collision = False
        
        if not EDIT_MODE:
            for wall in walls:
                if self.collision_rect.colliderect(wall):
                    horizontal_collision = True
                    if dx > 0:
                        self.rect.right = wall.left - self.collision_buffer
                    elif dx < 0:
                        self.rect.left = wall.right + self.collision_buffer
                    self.collision_rect.centerx = self.rect.centerx
                    break
        
        self.rect.y += dy
        self.collision_rect.centery = self.rect.centery
        
        if not EDIT_MODE:
            for wall in walls:
                if self.collision_rect.colliderect(wall):
                    vertical_collision = True
                    if dy > 0:
                        self.rect.bottom = wall.top - self.collision_buffer
                    elif dy < 0:
                        self.rect.top = wall.bottom + self.collision_buffer
                    self.collision_rect.centery = self.rect.centery
                    break
        
        moved_horizontally = (self.rect.x != old_x)
        moved_vertically = (self.rect.y != old_y)
        actually_moved = moved_horizontally or moved_vertically
        
        if self.is_moving and actually_moved:
            self.state = "walking"
        elif (horizontal_collision or vertical_collision) and not EDIT_MODE:
            self.state = "idle"
        elif not self.is_moving:
            self.state = "idle"
        else:
            self.state = "idle"
        
        return horizontal_collision, vertical_collision
    
    def update(self, walls):
        self.handle_input()
        collision_h, collision_v = self.move(walls)
        self.animate()
        return collision_h, collision_v

# =====================
# GRID DATA
# =====================
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]

player = Player(WIDTH // 2, HEIGHT // 2)

def get_walls():
    walls = []
    for row in range(ROWS):
        for col in range(COLS):
            if grid[row][col] == TILE_WALL:
                wall_rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                walls.append(wall_rect)
    return walls

def zoom_in():
    global ZOOM_LEVEL
    ZOOM_LEVEL = min(ZOOM_LEVEL + ZOOM_STEP, MAX_ZOOM)
    print(f"🔍 Zoom: {ZOOM_LEVEL:.2f}x")

def zoom_out():
    global ZOOM_LEVEL
    ZOOM_LEVEL = max(ZOOM_LEVEL - ZOOM_STEP, MIN_ZOOM)
    print(f"🔍 Zoom: {ZOOM_LEVEL:.2f}x")

def reset_zoom():
    global ZOOM_LEVEL
    ZOOM_LEVEL = 1.0
    print(f"🔍 Zoom reset to 1.0x")

# =====================
# LEVEL MANAGEMENT
# =====================
def get_levels_folder():
    """Get or create the levels folder"""
    if not os.path.exists("levels"):
        os.makedirs("levels")
    return "levels"

def list_levels():
    """List all available levels"""
    folder = get_levels_folder()
    levels = []
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            levels.append(filename[:-5])
    
    def natural_sort_key(s):
        import re
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', s)]
    
    return sorted(levels, key=natural_sort_key)

def save_level():
    """Save the current level with the current name"""
    folder = get_levels_folder()
    filepath = os.path.join(folder, f"{current_level_name}.json")
    
    data = {
        "grid": grid,
        "rows": ROWS,
        "cols": COLS,
        "name": current_level_name
    }
    
    with open(filepath, "w") as f:
        json.dump(data, f)
    
    print(f"✅ Level saved as: {current_level_name}")

def load_level(level_name):
    """Load a specific level"""
    global grid, current_level_name
    folder = get_levels_folder()
    filepath = os.path.join(folder, f"{level_name}.json")
    
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
            grid = data["grid"]
            current_level_name = data.get("name", level_name)
        print(f"📂 Level loaded: {current_level_name}")
        return True
    else:
        print(f"⚠️ Level not found: {level_name}")
        return False

def delete_level(level_name):
    """Delete a specific level"""
    folder = get_levels_folder()
    filepath = os.path.join(folder, f"{level_name}.json")
    
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"🗑️ Level deleted: {level_name}")
        return True
    else:
        print(f"⚠️ Level not found: {level_name}")
        return False

def clear_all_walls():
    """Clear all walls from the maze"""
    global grid
    grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    print("🗑️ All walls cleared! Clean slate ready.")

def toggle_edit_mode():
    """Toggle edit mode on/off"""
    global EDIT_MODE
    EDIT_MODE = not EDIT_MODE
    print(f"🎮 EDIT MODE: {'ENABLED' if EDIT_MODE else 'DISABLED'}")

def start_name_input():
    """Start naming/renaming the level"""
    global input_mode, input_text, input_mode_type
    input_mode = True
    input_mode_type = "name"
    input_text = current_level_name
    print("📝 Enter level name (press ENTER to confirm, ESC to cancel)")

def start_load_input():
    """Start load level dialog"""
    global input_mode, input_text, input_mode_type
    input_mode = True
    input_mode_type = "load"
    input_text = ""
    draw_level_selector.scroll_offset = 0
    print("📂 Select level to load")

def start_delete_input():
    """Start delete level dialog"""
    global input_mode, input_text, input_mode_type
    input_mode = True
    input_mode_type = "delete"
    input_text = ""
    draw_level_selector.scroll_offset = 0
    print("🗑️ Select level to delete")

# =====================
# IMPROVED MINIMAP
# =====================
def draw_minimap():
    minimap_surface = pygame.Surface((MINIMAP_WIDTH, MINIMAP_HEIGHT), pygame.SRCALPHA)
    minimap_surface.fill(MINIMAP_BG_COLOR)
    
    scale_x = MINIMAP_WIDTH / (COLS * TILE_SIZE)
    scale_y = MINIMAP_HEIGHT / (ROWS * TILE_SIZE)
    
    # Draw section grid
    for x in range(1, SECTION_COLS):
        grid_x = int(x * (WIDTH // TILE_SIZE) * TILE_SIZE * scale_x)
        pygame.draw.line(minimap_surface, MINIMAP_GRID_COLOR, 
                        (grid_x, 0), (grid_x, MINIMAP_HEIGHT), 1)
    
    for y in range(1, SECTION_ROWS):
        grid_y = int(y * (HEIGHT // TILE_SIZE) * TILE_SIZE * scale_y)
        pygame.draw.line(minimap_surface, MINIMAP_GRID_COLOR, 
                        (0, grid_y), (MINIMAP_WIDTH, grid_y), 1)
    
    # Draw tiles
    for row in range(ROWS):
        for col in range(COLS):
            tile = grid[row][col]
            if tile != TILE_EMPTY:
                minimap_x = int(col * TILE_SIZE * scale_x)
                minimap_y = int(row * TILE_SIZE * scale_y)
                minimap_width = max(2, int(TILE_SIZE * scale_x))
                minimap_height = max(2, int(TILE_SIZE * scale_y))
                
                if tile == TILE_WALL:
                    color = MINIMAP_WALL_COLOR
                elif tile == TILE_START:
                    color = MINIMAP_START_COLOR
                elif tile == TILE_END:
                    color = MINIMAP_END_COLOR
                elif tile == TILE_FLASHLIGHT:
                    color = MINIMAP_FLASHLIGHT_COLOR
                
                pygame.draw.rect(minimap_surface, color, 
                               (minimap_x, minimap_y, minimap_width, minimap_height))
    
    # Draw current view area
    view_x = int(camera_x * scale_x)
    view_y = int(camera_y * scale_y)
    view_width = int(WIDTH / ZOOM_LEVEL * scale_x)
    view_height = int(HEIGHT / ZOOM_LEVEL * scale_y)
    
    view_surface = pygame.Surface((view_width, view_height), pygame.SRCALPHA)
    view_surface.fill(MINIMAP_VIEW_COLOR)
    minimap_surface.blit(view_surface, (view_x, view_y))
    pygame.draw.rect(minimap_surface, (255, 255, 0), 
                   (view_x, view_y, view_width, view_height), 2)
    
    # Draw player
    player_minimap_x = int(player.rect.centerx * scale_x)
    player_minimap_y = int(player.rect.centery * scale_y)
    player_minimap_size = max(3, int(12 * scale_x))
    
    pygame.draw.circle(minimap_surface, (255, 255, 255), 
                     (player_minimap_x, player_minimap_y), player_minimap_size + 1)
    pygame.draw.circle(minimap_surface, MINIMAP_PLAYER_COLOR, 
                     (player_minimap_x, player_minimap_y), player_minimap_size)
    
    pygame.draw.rect(minimap_surface, MINIMAP_BORDER_COLOR, 
                   (0, 0, MINIMAP_WIDTH, MINIMAP_HEIGHT), 3)
    
    screen.blit(minimap_surface, MINIMAP_POS)

# =====================
# DRAWING FUNCTIONS
# =====================
def draw_scrolling_background():
    offset_x = -camera_x % bg_width
    offset_y = -camera_y % bg_height
    screen.blit(background, (offset_x - bg_width, offset_y - bg_height))
    screen.blit(background, (offset_x, offset_y - bg_height))
    screen.blit(background, (offset_x - bg_width, offset_y))
    screen.blit(background, (offset_x, offset_y))

def draw_level():
    level_surface = pygame.Surface((COLS * TILE_SIZE, ROWS * TILE_SIZE), pygame.SRCALPHA)
    
    for row in range(ROWS):
        for col in range(COLS):
            tile = grid[row][col]
            if tile == TILE_WALL:
                level_surface.blit(wall_img, (col * TILE_SIZE, row * TILE_SIZE))
            elif tile == TILE_START:
                level_surface.blit(start_img, (col * TILE_SIZE, row * TILE_SIZE))
            elif tile == TILE_END:
                level_surface.blit(end_img, (col * TILE_SIZE, row * TILE_SIZE))
            elif tile == TILE_FLASHLIGHT:
                level_surface.blit(flashlight_img, (col * TILE_SIZE, row * TILE_SIZE))
    
    scaled_width = int(COLS * TILE_SIZE * ZOOM_LEVEL)
    scaled_height = int(ROWS * TILE_SIZE * ZOOM_LEVEL)
    scaled_surface = pygame.transform.scale(level_surface, (scaled_width, scaled_height))
    
    screen.blit(scaled_surface, (-camera_x * ZOOM_LEVEL, -camera_y * ZOOM_LEVEL))

def draw_level_selector():
    """Draw the level load/delete selector"""
    if not input_mode or input_mode_type not in ["load", "delete"]:
        return None
    
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    box_width = 500
    box_height = 450
    box_x = WIDTH // 2 - box_width // 2
    box_y = HEIGHT // 2 - box_height // 2
    
    pygame.draw.rect(screen, (50, 50, 70), (box_x, box_y, box_width, box_height), border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 3, border_radius=10)
    
    font_title = pygame.font.Font(None, 40)
    title_text = "Load Level" if input_mode_type == "load" else "Delete Level"
    title_surf = font_title.render(title_text, True, (255, 255, 255))
    screen.blit(title_surf, (box_x + 20, box_y + 20))
    
    levels = list_levels()
    
    if not levels:
        font_msg = pygame.font.Font(None, 28)
        msg_text = font_msg.render("No levels found!", True, (255, 100, 100))
        screen.blit(msg_text, (box_x + box_width // 2 - msg_text.get_width() // 2, box_y + 150))
        
        cancel_btn = Button(box_x + box_width // 2 - 80, box_y + box_height - 70, 160, 50, 
                          "Cancel", (100, 100, 100), (150, 150, 150))
        cancel_btn.draw(screen)
        return [cancel_btn]
    
    buttons = []
    button_width = box_width - 40
    button_height = 45
    start_y = box_y + 70
    max_visible = 6
    
    scroll_offset = getattr(draw_level_selector, 'scroll_offset', 0)
    
    for i, level_name in enumerate(levels[scroll_offset:scroll_offset + max_visible]):
        y = start_y + i * (button_height + 5)
        
        color = (50, 100, 150) if input_mode_type == "load" else (150, 50, 50)
        hover_color = (70, 130, 200) if input_mode_type == "load" else (200, 70, 70)
        
        btn = Button(box_x + 20, y, button_width, button_height, 
                    level_name, color, hover_color)
        btn.level_name = level_name
        btn.draw(screen)
        buttons.append(btn)
    
    if scroll_offset > 0:
        font_arrow = pygame.font.Font(None, 36)
        up_arrow = font_arrow.render("▲", True, (255, 255, 255))
        screen.blit(up_arrow, (box_x + box_width // 2 - up_arrow.get_width() // 2, start_y - 30))
    
    if scroll_offset + max_visible < len(levels):
        font_arrow = pygame.font.Font(None, 36)
        down_arrow = font_arrow.render("▼", True, (255, 255, 255))
        screen.blit(down_arrow, (box_x + box_width // 2 - down_arrow.get_width() // 2, 
                                start_y + max_visible * (button_height + 5) + 5))
    
    font_small = pygame.font.Font(None, 24)
    if input_mode_type == "load":
        instr_text = font_small.render("Click a level to load it", True, (200, 200, 200))
    else:
        instr_text = font_small.render("Click a level to DELETE it (cannot be undone!)", True, (255, 150, 150))
    screen.blit(instr_text, (box_x + 20, box_y + box_height - 100))
    
    cancel_btn = Button(box_x + box_width // 2 - 80, box_y + box_height - 70, 160, 50, 
                      "Cancel", (100, 100, 100), (150, 150, 150))
    cancel_btn.draw(screen)
    buttons.append(cancel_btn)
    
    draw_level_selector.scroll_offset = scroll_offset
    
    return buttons

def draw_input_box():
    """Draw the input box for naming levels"""
    if not input_mode or input_mode_type != "name":
        return
    
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    box_width = 400
    box_height = 150
    box_x = WIDTH // 2 - box_width // 2
    box_y = HEIGHT // 2 - box_height // 2
    
    pygame.draw.rect(screen, (50, 50, 70), (box_x, box_y, box_width, box_height), border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 3, border_radius=10)
    
    font_title = pygame.font.Font(None, 36)
    title_text = font_title.render("Enter Level Name:", True, (255, 255, 255))
    screen.blit(title_text, (box_x + 20, box_y + 20))
    
    input_box_rect = pygame.Rect(box_x + 20, box_y + 70, box_width - 40, 40)
    pygame.draw.rect(screen, (30, 30, 40), input_box_rect, border_radius=5)
    pygame.draw.rect(screen, (100, 150, 255), input_box_rect, 2, border_radius=5)
    
    font_input = pygame.font.Font(None, 32)
    cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
    text_surface = font_input.render(input_text + cursor, True, (255, 255, 255))
    screen.blit(text_surface, (box_x + 30, box_y + 78))
    
    font_small = pygame.font.Font(None, 24)
    instr_text = font_small.render("ENTER to save | ESC to cancel", True, (200, 200, 200))
    screen.blit(instr_text, (box_x + 20, box_y + 120))

# =====================
# MAIN LOOP
# =====================
running = True
current_tile = TILE_WALL
mouse_clicked = False
selector_buttons = []

print("🎮 Level Editor - Enhanced with Flashlight Items")
print("\n📁 Controls:")
print("WASD - Move player")
print("Arrow Keys - Pan camera view")
print("Mouse Left - Place current tile")
print("Mouse Right - Remove tile")
print("Mouse Middle - Click and drag to pan")
print("Scroll - Zoom in/out")
print("\n🎨 Tools:")
print("0 - Toggle Edit Mode")
print("4 - Select Wall tile")
print("5 - Select Start tile")
print("6 - Select End tile")
print("7 - Reset zoom")
print("8 - Select Flashlight tile 💡")
print("\n💾 File Operations:")
print("N - Name/Rename current level")
print("S - Save level")
print("L - Load level (shows level selector)")
print("D - Delete level (shows level selector)")
print("C - Clear all walls")
print(f"\n📝 Current level: {current_level_name}")
print("\n💡 TIP: Place flashlight items for dark levels (level 6+)!")

while running:
    clock.tick(60)
    walls = get_walls()
    
    if not input_mode or input_mode_type == "name":
        player.update(walls)
    
    mouse_clicked = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_clicked = True

        if event.type == pygame.KEYDOWN:
            if input_mode and input_mode_type == "name":
                if event.key == pygame.K_RETURN:
                    if input_text.strip():
                        current_level_name = input_text.strip()
                        print(f"📝 Level renamed to: {current_level_name}")
                    input_mode = False
                elif event.key == pygame.K_ESCAPE:
                    input_mode = False
                    input_text = current_level_name
                    print("❌ Naming cancelled")
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if event.unicode.isalnum() or event.unicode in ['-', '_', ' ']:
                        if len(input_text) < 30:
                            input_text += event.unicode
            
            elif input_mode and input_mode_type in ["load", "delete"]:
                if event.key == pygame.K_UP:
                    scroll_offset = getattr(draw_level_selector, 'scroll_offset', 0)
                    draw_level_selector.scroll_offset = max(0, scroll_offset - 1)
                elif event.key == pygame.K_DOWN:
                    scroll_offset = getattr(draw_level_selector, 'scroll_offset', 0)
                    levels = list_levels()
                    draw_level_selector.scroll_offset = min(max(0, len(levels) - 6), scroll_offset + 1)
                elif event.key == pygame.K_ESCAPE:
                    input_mode = False
                    print("❌ Cancelled")
            
            else:
                if event.key == pygame.K_s:
                    save_level()
                elif event.key == pygame.K_l:
                    start_load_input()
                elif event.key == pygame.K_d:
                    start_delete_input()
                elif event.key == pygame.K_c:
                    clear_all_walls()
                elif event.key == pygame.K_0:
                    toggle_edit_mode()
                elif event.key == pygame.K_4:
                    current_tile = TILE_WALL
                    print("🧱 Selected: Wall")
                elif event.key == pygame.K_5:
                    current_tile = TILE_START
                    print("🟢 Selected: Start Point")
                elif event.key == pygame.K_6:
                    current_tile = TILE_END
                    print("🔴 Selected: End Point")
                elif event.key == pygame.K_7:
                    reset_zoom()
                elif event.key == pygame.K_8:
                    current_tile = TILE_FLASHLIGHT
                    print("💡 Selected: Flashlight Item")
                elif event.key == pygame.K_n:
                    start_name_input()
        
        elif event.type == pygame.MOUSEWHEEL:
            if not input_mode:
                if event.y > 0:
                    zoom_in()
                else:
                    zoom_out()
            elif input_mode_type in ["load", "delete"]:
                scroll_offset = getattr(draw_level_selector, 'scroll_offset', 0)
                levels = list_levels()
                if event.y > 0:
                    draw_level_selector.scroll_offset = max(0, scroll_offset - 1)
                else:
                    draw_level_selector.scroll_offset = min(max(0, len(levels) - 6), scroll_offset + 1)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2:
                panning = True
                last_mouse_pos = pygame.mouse.get_pos()
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:
                panning = False

    draw_scrolling_background()
    draw_level()
    
    player_x = (player.rect.x - camera_x) * ZOOM_LEVEL
    player_y = (player.rect.y - camera_y) * ZOOM_LEVEL
    player_scaled = pygame.transform.scale(player.image, 
                                          (int(player.image.get_width() * ZOOM_LEVEL),
                                           int(player.image.get_height() * ZOOM_LEVEL)))
    screen.blit(player_scaled, (player_x, player_y))
    
    draw_minimap()
    
    font = pygame.font.Font(None, 28)
    y_pos = 10
    
    tile_names = ['Empty', 'Wall', 'Start', 'End', 'Flashlight']
    
    info_texts = [
        f"Level: {current_level_name} (Press N to rename)",
        f"Zoom: {ZOOM_LEVEL:.2f}x",
        f"Edit Mode: {'ON' if EDIT_MODE else 'OFF'}",
        f"Tile: {tile_names[current_tile]}",
        f"Walls: {sum(1 for row in grid for tile in row if tile == TILE_WALL)}",
        f"Flashlights: {sum(1 for row in grid for tile in row if tile == TILE_FLASHLIGHT)}"
    ]
    
    for text in info_texts:
        color = EDIT_MODE_COLOR if EDIT_MODE and "Edit Mode" in text else (255, 255, 255)
        surf = font.render(text, True, color)
        screen.blit(surf, (10, y_pos))
        y_pos += 30
    
    selector_buttons = draw_level_selector()
    draw_input_box()
    
    if selector_buttons:
        mouse_pos = pygame.mouse.get_pos()
        for btn in selector_buttons:
            btn.is_hovered = btn.rect.collidepoint(mouse_pos)
            
            if btn.is_clicked(mouse_pos, mouse_clicked):
                if btn.text == "Cancel":
                    input_mode = False
                    print("❌ Cancelled")
                elif hasattr(btn, 'level_name'):
                    if input_mode_type == "load":
                        if load_level(btn.level_name):
                            input_mode = False
                    elif input_mode_type == "delete":
                        if delete_level(btn.level_name):
                            if current_level_name == btn.level_name:
                                current_level_name = "level1"
                                clear_all_walls()
                        input_mode = False

    if not input_mode:
        if panning:
            mx, my = pygame.mouse.get_pos()
            dx = (mx - last_mouse_pos[0]) / ZOOM_LEVEL
            dy = (my - last_mouse_pos[1]) / ZOOM_LEVEL
            camera_x -= dx
            camera_y -= dy
            last_mouse_pos = (mx, my)
        
        keys = pygame.key.get_pressed()
        pan_speed = 10 / ZOOM_LEVEL
        if keys[pygame.K_LEFT]:
            camera_x -= pan_speed
        if keys[pygame.K_RIGHT]:
            camera_x += pan_speed
        if keys[pygame.K_UP]:
            camera_y -= pan_speed
        if keys[pygame.K_DOWN]:
            camera_y += pan_speed
    
    camera_x = max(0, min(camera_x, COLS * TILE_SIZE - WIDTH / ZOOM_LEVEL))
    camera_y = max(0, min(camera_y, ROWS * TILE_SIZE - HEIGHT / ZOOM_LEVEL))

    if not input_mode:
        mouse_buttons = pygame.mouse.get_pressed()
        if (mouse_buttons[0] or mouse_buttons[2]) and not panning:
            mx, my = pygame.mouse.get_pos()
            
            world_x = (mx / ZOOM_LEVEL) + camera_x
            world_y = (my / ZOOM_LEVEL) + camera_y
            
            grid_x = int(world_x // TILE_SIZE)
            grid_y = int(world_y // TILE_SIZE)
            
            if 0 <= grid_x < COLS and 0 <= grid_y < ROWS:
                if mouse_buttons[0]:
                    if current_tile == TILE_START:
                        for r in range(ROWS):
                            for c in range(COLS):
                                if grid[r][c] == TILE_START:
                                    grid[r][c] = TILE_EMPTY
                    elif current_tile == TILE_END:
                        for r in range(ROWS):
                            for c in range(COLS):
                                if grid[r][c] == TILE_END:
                                    grid[r][c] = TILE_EMPTY
                    grid[grid_y][grid_x] = current_tile
                elif mouse_buttons[2]:
                    grid[grid_y][grid_x] = TILE_EMPTY

    pygame.display.flip()

pygame.quit()
sys.exit()