import pygame
import os

class Mario:
    def __init__(self, x, y):
        self.animations = self.load_animation_frames()
        self.direction = "down"
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_delay = 3
        
        # Set initial image
        if self.animations[self.direction]:
            self.image = self.animations[self.direction][self.current_frame]
            self.rect = self.image.get_rect(center=(x, y))
        else:
            # Fallback if no frames loaded
            self.image = pygame.Surface((34, 63))
            self.image.fill((255, 0, 0))
            self.rect = self.image.get_rect(center=(x, y))
        
        # Collision rect (smaller than visual sprite)
        self.collision_rect = pygame.Rect(0, 0, self.rect.width * 0.6, self.rect.height * 0.6)
        self.collision_rect.center = self.rect.center
        
        self.speed = 6
        self.is_walking = False
        self.collision_buffer = 5

    def load_animation_frames(self):
        """Load all animation frames for all directions"""
        animations = {
            'down': [],
            'right': [],
            'up': [],
            'left': []
        }
        scale_factor = .5  # Adjust this value to change size
        # Load walk down frames (0-7)
        for i in range(8):
            filename = f"images/mario_walkdown{i}.png"
            try:
                if os.path.exists(filename):
                    frame = pygame.image.load(filename).convert_alpha()
                    # Scale the frame
                    new_width = int(frame.get_width() * scale_factor)
                    new_height = int(frame.get_height() * scale_factor)
                    frame = pygame.transform.scale(frame, (new_width, new_height))
                    animations['down'].append(frame)
            except:
                pass
        
        # Load walk right frames (0-7)
        for i in range(8):
            filename = f"images/mario_walkright{i}.png"
            try:
                if os.path.exists(filename):
                    frame = pygame.image.load(filename).convert_alpha()
                    # Scale the frame
                    new_width = int(frame.get_width() * scale_factor)
                    new_height = int(frame.get_height() * scale_factor)
                    frame = pygame.transform.scale(frame, (new_width, new_height))
                    animations['right'].append(frame)
            except:
                pass
        
        # Load walk up frames (0-7)
        for i in range(8):
            filename = f"images/mario_walkup{i}.png"
            try:
                if os.path.exists(filename):
                    frame = pygame.image.load(filename).convert_alpha()
                    # Scale the frame
                    new_width = int(frame.get_width() * scale_factor)
                    new_height = int(frame.get_height() * scale_factor)
                    frame = pygame.transform.scale(frame, (new_width, new_height))
                    animations['up'].append(frame)
            except:
                pass
        
        # Create left frames by flipping right frames
        if animations['right']:
            for frame in animations['right']:
                flipped_frame = pygame.transform.flip(frame, True, False)
                animations['left'].append(flipped_frame)
        
        # Fallback frames if none loaded
        if not any(animations.values()):
            fallback = pygame.Surface((34, 63), pygame.SRCALPHA)
            pygame.draw.rect(fallback, (255, 0, 0), (0, 0, 34, 63))
            pygame.draw.circle(fallback, (255, 255, 255), (17, 20), 10)
            for direction in animations:
                animations[direction] = [fallback]
        
        return animations

    def handle_input(self):
        """Handle player input using WASD keys"""
        keys = pygame.key.get_pressed()
        
        # WASD controls
        move_x = keys[pygame.K_d] - keys[pygame.K_a]  # A = left, D = right
        move_y = keys[pygame.K_s] - keys[pygame.K_w]  # S = down, W = up
        
        # Update direction based on movement (prioritize horizontal)
        old_direction = self.direction
        
        if move_x < 0:
            self.direction = "left"
        elif move_x > 0:
            self.direction = "right"
        elif move_y > 0:
            self.direction = "down"
        elif move_y < 0:
            self.direction = "up"
        
        # Reset animation if direction changed
        if old_direction != self.direction:
            self.current_frame = 0
            self.animation_timer = 0
            if self.animations.get(self.direction):
                self.image = self.animations[self.direction][self.current_frame]
        
        # Check if walking
        self.is_walking = (move_x != 0 or move_y != 0)
        
        return move_x, move_y

    def animate(self):
        """Handle sprite animation"""
        current_animation = self.animations.get(self.direction, [])
        if not current_animation:
            return
            
        if self.is_walking:
            self.animation_timer += 1
            if self.animation_timer >= self.animation_delay:
                self.animation_timer = 0
                self.current_frame = (self.current_frame + 1) % len(current_animation)
                old_center = self.rect.center
                self.image = current_animation[self.current_frame]
                self.rect = self.image.get_rect(center=old_center)
        else:
            self.current_frame = 0
            old_center = self.rect.center
            self.image = current_animation[self.current_frame]
            self.rect = self.image.get_rect(center=old_center)

    def move(self, walls):
        """Handle player movement with wall collision"""
        move_x, move_y = self.handle_input()
        
        old_x, old_y = self.rect.x, self.rect.y
        dx = move_x * self.speed
        dy = move_y * self.speed
        
        # Move horizontally and check collisions
        self.rect.x += dx
        self.collision_rect.centerx = self.rect.centerx
        
        for wall in walls:
            if self.collision_rect.colliderect(wall):
                if dx > 0:  # Moving right
                    self.rect.right = wall.left - self.collision_buffer
                elif dx < 0:  # Moving left
                    self.rect.left = wall.right + self.collision_buffer
                self.collision_rect.centerx = self.rect.centerx
                break
        
        # Move vertically and check collisions
        self.rect.y += dy
        self.collision_rect.centery = self.rect.centery
        
        for wall in walls:
            if self.collision_rect.colliderect(wall):
                if dy > 0:  # Moving down
                    self.rect.bottom = wall.top - self.collision_buffer
                elif dy < 0:  # Moving up
                    self.rect.top = wall.bottom + self.collision_buffer
                self.collision_rect.centery = self.rect.centery
                break
        
        # Update collision rect
        self.collision_rect.center = self.rect.center

    def update(self, walls):
        """Update player state"""
        self.move(walls)
        self.animate()

    def draw(self, surface, camera_x, camera_y):
        """Draw player on surface with camera offset"""
        surface.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y))