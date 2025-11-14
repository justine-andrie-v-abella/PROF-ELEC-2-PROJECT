import pygame
import sys
from player import Mario

pygame.init()

# Settings
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mario Game")
clock = pygame.time.Clock()

# Create Mario
mario = Mario(WIDTH // 2, HEIGHT // 2)

# Main loop
running = True
while running:
    clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Update player
    mario.update(WIDTH, HEIGHT)
    
    # Draw
    screen.fill((50, 50, 50))  # Simple background
    
    # Draw player
    mario.draw(screen)
    
    pygame.display.flip()

pygame.quit()
sys.exit()