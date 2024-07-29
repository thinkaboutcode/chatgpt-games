import pygame
import random
import math
import numpy as np

# Initialize Pygame
pygame.init()

# Initialize Mixer
pygame.mixer.init(frequency=22050, size=-16, channels=2)

# Constants
FPS = 60
SMALLEST_SIZE = 10
FRAGMENT_LIFETIME = 30  # Frames
SHIP_ACCELERATION = 0.1
SHIP_DECELERATION = 0.05
MAX_SHIP_SPEED = 5

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Set up display for fullscreen
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Asteroids")

# Set up clock
clock = pygame.time.Clock()

def synthesize_sound(frequency, duration, sample_rate=22050, modulation_frequency=2.0):
    """Synthesize a sound with optional amplitude modulation."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    carrier_wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    modulator_wave = 0.5 * (1 + np.sin(2 * np.pi * modulation_frequency * t))
    wave = carrier_wave * modulator_wave
    wave = (wave * 32767).astype(np.int16)  # Convert to 16-bit PCM

    # Create stereo sound by duplicating the mono wave for both channels
    stereo_wave = np.stack((wave, wave), axis=-1)

    return pygame.sndarray.make_sound(stereo_wave)

def synthesize_white_noise(duration, sample_rate=22050, depth=0.1):
    """Synthesize a white noise sound with fading effect."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    noise = np.random.uniform(-1, 1, size=t.shape)
    envelope = np.linspace(1, 0, t.shape[0])  # Linear fade-out
    noise = noise * envelope * depth
    noise = (noise * 32767).astype(np.int16)  # Convert to 16-bit PCM

    # Create stereo sound by duplicating the mono wave for both channels
    stereo_noise = np.stack((noise, noise), axis=-1)

    return pygame.sndarray.make_sound(stereo_noise)

# Sound Effects
move_sound = synthesize_sound(100, 0.1, modulation_frequency=2.0)  # Deeper sound with modulation
shoot_sound = synthesize_sound(880, 0.1)  # Frequency: 880 Hz (A5), Duration: 0.1 sec
squeesh_sound = synthesize_white_noise(0.3, depth=0.2)  # Longer, deeper squeesh sound

def draw_spaceship(screen, x, y, angle):
    size = 30
    short_side = size * 0.7
    long_side = size
    half_short_side = short_side / 2
    half_long_side = long_side / 2

    point1 = (x + half_long_side * math.cos(math.radians(angle)),
              y - half_long_side * math.sin(math.radians(angle)))
    point2 = (x + half_short_side * math.cos(math.radians(angle + 120)),
              y - half_short_side * math.sin(math.radians(angle + 120)))
    point3 = (x + half_short_side * math.cos(math.radians(angle - 120)),
              y - half_short_side * math.sin(math.radians(angle - 120)))
    pygame.draw.polygon(screen, WHITE, [point1, point2, point3], 1)

    # Draw exit points
    exit_point1 = (x + long_side * math.cos(math.radians(angle + 90)),
                   y - long_side * math.sin(math.radians(angle + 90)))
    exit_point2 = (x + long_side * math.cos(math.radians(angle - 90)),
                   y - long_side * math.sin(math.radians(angle - 90)))
    pygame.draw.circle(screen, WHITE, (int(exit_point1[0]), int(exit_point1[1])), 3)
    pygame.draw.circle(screen, WHITE, (int(exit_point2[0]), int(exit_point2[1])), 3)

def draw_asteroid(screen, x, y, vertices, angle, size):
    points = []
    for i in range(vertices):
        angle_deg = 360 / vertices * i + angle
        point_x = x + size * math.cos(math.radians(angle_deg))
        point_y = y + size * math.sin(math.radians(angle_deg))
        points.append((point_x, point_y))
    pygame.draw.polygon(screen, WHITE, points, 1)

def draw_bullet(screen, x, y):
    pygame.draw.rect(screen, WHITE, (x, y, 4, 10), 1)

class Spaceship(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((40, 40), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.velocity = pygame.math.Vector2(0, 0)
        self.angle = 0
        self.moving = False

    def update(self, keys_pressed):
        self.moving = False

        if keys_pressed[pygame.K_LEFT]:
            self.angle += 5
        if keys_pressed[pygame.K_RIGHT]:
            self.angle -= 5
        if keys_pressed[pygame.K_UP]:
            direction = pygame.math.Vector2(1, 0).rotate(self.angle)
            self.velocity += direction * SHIP_ACCELERATION
            self.moving = True
        else:
            self.velocity *= (1 - SHIP_DECELERATION)

        # Limit the velocity to the maximum speed
        if self.velocity.length() > MAX_SHIP_SPEED:
            self.velocity.scale_to_length(MAX_SHIP_SPEED)

        self.rect.x += self.velocity.x
        self.rect.y -= self.velocity.y

        self.rect.x %= WIDTH
        self.rect.y %= HEIGHT

        if self.moving:
            move_sound.play()

    def draw(self, screen):
        draw_spaceship(screen, self.rect.centerx, self.rect.centery, self.angle)

    def fire_bullet(self):
        direction = pygame.math.Vector2(1, 0).rotate(self.angle)
        long_side = 30
        bullet_pos1 = (self.rect.centerx + long_side * math.cos(math.radians(self.angle + 90)),
                       self.rect.centery - long_side * math.sin(math.radians(self.angle + 90)))
        bullet_pos2 = (self.rect.centerx + long_side * math.cos(math.radians(self.angle - 90)),
                       self.rect.centery - long_side * math.sin(math.radians(self.angle - 90)))

        shoot_sound.play()
        return [Bullet(*bullet_pos1, self.angle), Bullet(*bullet_pos2, self.angle)]

class Asteroid(pygame.sprite.Sprite):
    def __init__(self, x=None, y=None, size=40):
        super().__init__()
        self.size = size
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(
            center=(x if x is not None else random.randint(0, WIDTH),
                    y if y is not None else random.randint(0, HEIGHT)))
        self.speed = random.randint(1, 3)
        self.angle = random.randint(0, 360)
        self.vertices = random.randint(5, 8)
        self.fragment_timer = FRAGMENT_LIFETIME if self.size == SMALLEST_SIZE else None
        self.has_split = False

    def update(self, *args):
        self.rect.x += self.speed * math.cos(math.radians(self.angle))
        self.rect.y -= self.speed * math.sin(math.radians(self.angle))

        self.rect.x %= WIDTH
        self.rect.y %= HEIGHT

        if self.fragment_timer is not None:
            self.fragment_timer -= 1
            if self.fragment_timer <= 0:
                self.kill()

    def draw(self, screen):
        draw_asteroid(screen, self.rect.centerx, self.rect.centery, self.vertices, self.angle, self.size)

    def split(self):
        if not self.has_split and self.size > SMALLEST_SIZE:
            self.has_split = True
            new_size = self.size // 2
            return [Asteroid(self.rect.centerx, self.rect.centery, new_size),
                    Asteroid(self.rect.centerx, self.rect.centery, new_size)]
        elif self.has_split:
            return self.create_explosion()
        else:
            return []

    def create_explosion(self):
        fragments = []
        for _ in range(10):
            fragment = Asteroid(self.rect.centerx, self.rect.centery, SMALLEST_SIZE)
            fragment.angle = random.randint(0, 360)
            fragment.speed = random.randint(2, 5)
            fragment.fragment_timer = FRAGMENT_LIFETIME
            fragments.append(fragment)
        return fragments

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle):
        super().__init__()
        self.image = pygame.Surface((4, 10), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 10
        self.angle = angle

    def update(self, *args):
        self.rect.x += self.speed * math.cos(math.radians(self.angle))
        self.rect.y -= self.speed * math.sin(math.radians(self.angle))

        if not (0 <= self.rect.x <= WIDTH) or not (0 <= self.rect.y <= HEIGHT):
            self.kill()

    def draw(self, screen):
        draw_bullet(screen, self.rect.x, self.rect.y)

def draw_start_screen(screen):
    font = pygame.font.Font(None, 74)
    title_text = font.render("ASTEROIDS", True, WHITE)
    instruction_text = font.render("Press any key to start", True, WHITE)
    screen.fill(BLACK)
    screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 2 - title_text.get_height() // 2 - 50))
    screen.blit(instruction_text, (WIDTH // 2 - instruction_text.get_width() // 2, HEIGHT // 2 + 50))
    pygame.display.flip()

def draw_game_over_screen(screen, score):
    font = pygame.font.Font(None, 74)
    game_over_text = font.render("GAME OVER", True, WHITE)
    score_text = font.render(f"Score: {score}", True, WHITE)
    instruction_text = font.render("Press any key to restart", True, WHITE)
    screen.fill(BLACK)
    screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2 - game_over_text.get_height() // 2 - 50))
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 + 10))
    screen.blit(instruction_text, (WIDTH // 2 - instruction_text.get_width() // 2, HEIGHT // 2 + 70))
    pygame.display.flip()

def game_loop():
    spaceship = Spaceship()
    asteroids = pygame.sprite.Group()
    for _ in range(5):
        asteroids.add(Asteroid())

    all_sprites = pygame.sprite.Group(spaceship, *asteroids)
    bullets = pygame.sprite.Group()
    score = 0

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bullets.add(spaceship.fire_bullet())
                    all_sprites.add(bullets)

        keys_pressed = pygame.key.get_pressed()
        spaceship.update(keys_pressed)
        bullets.update()
        asteroids.update()

        for bullet in bullets:
            asteroid_hit = pygame.sprite.spritecollideany(bullet, asteroids)
            if asteroid_hit:
                bullet.kill()
                squeesh_sound.play()  # Play the squeesh sound effect
                fragments = asteroid_hit.split()
                if fragments:
                    for fragment in fragments:
                        asteroids.add(fragment)
                        all_sprites.add(fragment)
                else:
                    score += 1
                asteroid_hit.kill()

        if pygame.sprite.spritecollideany(spaceship, asteroids):
            return score

        screen.fill(BLACK)
        for sprite in all_sprites:
            sprite.draw(screen)

        font = pygame.font.Font(None, 36)
        score_text = font.render(f'Score: {score}', True, WHITE)
        screen.blit(score_text, (10, 10))

        pygame.display.flip()

def main():
    while True:
        draw_start_screen(screen)
        waiting_for_start = True
        while waiting_for_start:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    waiting_for_start = False
                    break

        score = game_loop()
        draw_game_over_screen(screen, score)
        waiting_for_restart = True
        while waiting_for_restart:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    waiting_for_restart = False
                    break

main()
pygame.quit()
