import json
import math
import os
import random
import sys

import pygame

# --- CONSTANTS & CONFIGURATION ---
WIDTH, HEIGHT, FPS = 1000, 800, 60
PLAYER_SIZE = (58, 62)
PLAYER_SPEED = 540
LIVES = 3
SAVE_FILE = "space_dodge_high_score.json"

# Palette
WHITE = (245, 248, 255)
CYAN = (89, 220, 255)
DEEP_CYAN = (20, 140, 220)
GOLD = (255, 215, 65)
ORANGE = (255, 120, 45)
RED = (255, 75, 85)
NAVY = (8, 16, 42)
DARK_BG = (5, 9, 26)
MUTED = (135, 150, 180)
PURPLE = (180, 90, 255)


def get_asset_path(filename):
    """Finds asset path reliably across different execution working directories."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "images", filename),
        os.path.join(base_dir, "Assets", "images", filename),
        os.path.join(base_dir, filename),
        os.path.join(os.getcwd(), "Assets", "images", filename),
        os.path.join(os.getcwd(), "images", filename),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


# --- PARTICLE SYSTEM ---
class Particle:
    __slots__ = (
        "x", "y", "vx", "vy", "size", "start_size", "end_size",
        "color", "end_color", "life", "max_life", "shape",
        "drag", "gravity", "alpha", "blend_add"
    )

    def __init__(
        self,
        x,
        y,
        vx,
        vy,
        size,
        end_size,
        color,
        end_color,
        max_life,
        shape="circle",
        drag=0.98,
        gravity=0.0,
        blend_add=True,
    ):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.start_size = float(size)
        self.end_size = float(end_size)
        self.size = float(size)
        self.color = color
        self.end_color = end_color
        self.life = float(max_life)
        self.max_life = float(max_life)
        self.shape = shape
        self.drag = float(drag)
        self.gravity = float(gravity)
        self.alpha = 255.0
        self.blend_add = blend_add

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            return False
        progress = 1.0 - (self.life / self.max_life)
        self.vx *= self.drag ** (dt * 60)
        self.vy = (self.vy + self.gravity * dt) * (self.drag ** (dt * 60))
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.size = max(0.5, self.start_size + (self.end_size - self.start_size) * progress)
        self.alpha = max(0.0, 255.0 * (1.0 - progress))
        return True

    def get_current_color(self):
        progress = 1.0 - (self.life / self.max_life)
        r = int(self.color[0] + (self.end_color[0] - self.color[0]) * progress)
        g = int(self.color[1] + (self.end_color[1] - self.color[1]) * progress)
        b = int(self.color[2] + (self.end_color[2] - self.color[2]) * progress)
        return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))


class Shockwave:
    __slots__ = ("x", "y", "radius", "max_radius", "color", "life", "max_life", "width")

    def __init__(self, x, y, max_radius, color, duration=0.45, width=3):
        self.x = float(x)
        self.y = float(y)
        self.radius = 4.0
        self.max_radius = float(max_radius)
        self.color = color
        self.life = float(duration)
        self.max_life = float(duration)
        self.width = width

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            return False
        progress = 1.0 - (self.life / self.max_life)
        self.radius = 4.0 + (self.max_radius - 4.0) * (progress ** 0.6)
        return True

    def draw(self, surface):
        if self.life <= 0 or self.radius <= 1:
            return
        progress = 1.0 - (self.life / self.max_life)
        alpha = int(255 * (1.0 - progress))
        if alpha <= 0:
            return
        r_int = max(2, int(self.radius))
        shock_surf = pygame.Surface((r_int * 2 + 4, r_int * 2 + 4), pygame.SRCALPHA)
        col = (*self.color[:3], alpha)
        pygame.draw.circle(
            shock_surf, col, (r_int + 2, r_int + 2), r_int, max(1, int(self.width * (1.0 - progress * 0.5)))
        )
        surface.blit(shock_surf, (int(self.x - r_int - 2), int(self.y - r_int - 2)), special_flags=pygame.BLEND_ADD)


class ParticleManager:
    def __init__(self):
        self.particles = []
        self.shockwaves = []

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        self.shockwaves = [s for s in self.shockwaves if s.update(dt)]

    def draw(self, surface):
        # Draw shockwaves first
        for shock in self.shockwaves:
            shock.draw(surface)

        # Batch draw particles
        for p in self.particles:
            color = p.get_current_color()
            alpha_int = int(p.alpha)
            if alpha_int <= 0 or p.size < 0.5:
                continue

            r = max(1, int(p.size))
            surf_size = r * 2 + 4
            p_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)

            if p.shape == "glow":
                # Soft glowing particle
                p_surf.fill((0, 0, 0, 0))
                pygame.draw.circle(p_surf, (*color, alpha_int // 3), (r + 2, r + 2), r + 1)
                pygame.draw.circle(p_surf, (*color, alpha_int), (r + 2, r + 2), max(1, r // 2))
                pygame.draw.circle(p_surf, (255, 255, 255, alpha_int), (r + 2, r + 2), max(1, r // 3))
            elif p.shape == "spark":
                # Diamond / star spark
                p_surf.fill((0, 0, 0, 0))
                pts = [(r + 2, 0), (r * 2 + 4, r + 2), (r + 2, r * 2 + 4), (0, r + 2)]
                pygame.draw.polygon(p_surf, (*color, alpha_int), pts)
            elif p.shape == "smoke":
                p_surf.fill((0, 0, 0, 0))
                pygame.draw.circle(p_surf, (*color, int(alpha_int * 0.45)), (r + 2, r + 2), r)
            else:
                # Normal circle
                pygame.draw.circle(p_surf, (*color, alpha_int), (r + 2, r + 2), r)

            flags = pygame.BLEND_ADD if p.blend_add else 0
            surface.blit(p_surf, (int(p.x - r - 2), int(p.y - r - 2)), special_flags=flags)

    def emit_engine(self, x, y, moving_dir=0, speed_boost=1.0):
        """Emits glowing plasma jet particles from the spaceship engine."""
        for _ in range(random.randint(2, 4)):
            spread_x = random.uniform(-4, 4)
            vx = moving_dir * -40 + random.uniform(-25, 25)
            vy = random.uniform(160, 320) * speed_boost
            size = random.uniform(3.5, 6.5)
            life = random.uniform(0.18, 0.38)
            # Plasma colors from white-hot -> cyan -> deep purple/blue
            c_choice = random.random()
            if c_choice < 0.4:
                start_c = (230, 250, 255)
                end_c = CYAN
            elif c_choice < 0.8:
                start_c = CYAN
                end_c = (30, 80, 240)
            else:
                start_c = (140, 220, 255)
                end_c = (160, 40, 255)

            self.particles.append(
                Particle(
                    x + spread_x,
                    y,
                    vx,
                    vy,
                    size,
                    0.5,
                    start_c,
                    end_c,
                    life,
                    shape="glow",
                    drag=0.92,
                    blend_add=True,
                )
            )

    def emit_meteor_trail(self, x, y, radius, color_type):
        """Emits fiery sparks and dissipating smoke along the meteor path."""
        # Fiery spark
        if random.random() < 0.85:
            spread = radius * 0.6
            px = x + random.uniform(-spread, spread)
            py = y - random.uniform(2, radius * 0.5)
            vx = random.uniform(-30, 30)
            vy = random.uniform(-60, -10)
            life = random.uniform(0.2, 0.45)
            size = random.uniform(2.5, max(3.5, radius * 0.28))
            start_col = (255, 230, 110) if random.random() < 0.5 else (255, 120, 40)
            end_col = (180, 35, 20)
            self.particles.append(
                Particle(
                    px, py, vx, vy, size, 0.5, start_col, end_col, life, shape="glow", drag=0.94, blend_add=True
                )
            )

        # Smoke puff
        if random.random() < 0.4:
            px = x + random.uniform(-radius * 0.4, radius * 0.4)
            py = y - random.uniform(4, radius * 0.8)
            life = random.uniform(0.35, 0.6)
            size = random.uniform(radius * 0.25, radius * 0.5)
            self.particles.append(
                Particle(
                    px,
                    py,
                    random.uniform(-15, 15),
                    random.uniform(-30, -5),
                    size,
                    size * 2.2,
                    (90, 75, 85),
                    (30, 25, 35),
                    life,
                    shape="smoke",
                    drag=0.96,
                    blend_add=False,
                )
            )

    def emit_explosion(self, x, y, radius=40, count=36, is_player=False):
        """Creates a vibrant multi-stage explosion with shockwave, fire, sparks and smoke."""
        shock_color = (255, 160, 60) if not is_player else (255, 90, 110)
        self.shockwaves.append(Shockwave(x, y, max_radius=radius * 2.4, color=shock_color, duration=0.42, width=4))

        # Core flash sparks
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(70, 380) * (1.3 if is_player else 1.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = random.uniform(3.5, 8.0)
            life = random.uniform(0.35, 0.85)

            if random.random() < 0.35:
                c1, c2 = (255, 250, 200), (255, 140, 30)
            elif random.random() < 0.7:
                c1, c2 = (255, 140, 40), (220, 30, 30)
            else:
                c1, c2 = (255, 80, 80), (120, 20, 50)

            self.particles.append(
                Particle(
                    x, y, vx, vy, size, 0.5, c1, c2, life, shape="glow", drag=0.93, gravity=40.0, blend_add=True
                )
            )

        # Debris chunks
        for _ in range(count // 2):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(120, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(0.4, 0.7)
            size = random.uniform(2.0, 4.5)
            self.particles.append(
                Particle(
                    x,
                    y,
                    vx,
                    vy,
                    size,
                    1.0,
                    (255, 220, 120),
                    (180, 50, 20),
                    life,
                    shape="spark",
                    drag=0.95,
                    gravity=60.0,
                    blend_add=True,
                )
            )

        # Billowing smoke
        for _ in range(count // 3):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(30, 110)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(0.5, 1.0)
            size = random.uniform(6.0, 14.0)
            self.particles.append(
                Particle(
                    x,
                    y,
                    vx,
                    vy,
                    size,
                    size * 2.8,
                    (80, 70, 80),
                    (20, 18, 25),
                    life,
                    shape="smoke",
                    drag=0.94,
                    gravity=-10.0,
                    blend_add=False,
                )
            )

    def emit_collect(self, x, y, kind="shield"):
        """Emits radiant sparkles when a powerup or bonus is collected."""
        color = CYAN if kind == "shield" else GOLD
        second_col = WHITE
        self.shockwaves.append(Shockwave(x, y, max_radius=45, color=color, duration=0.35, width=3))

        for _ in range(24):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 240)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(0.3, 0.6)
            size = random.uniform(2.5, 5.5)
            c1 = second_col if random.random() < 0.4 else color
            c2 = color if c1 == second_col else DEEP_CYAN
            self.particles.append(
                Particle(
                    x,
                    y,
                    vx,
                    vy,
                    size,
                    0.5,
                    c1,
                    c2,
                    life,
                    shape="spark" if random.random() < 0.6 else "glow",
                    drag=0.92,
                    blend_add=True,
                )
            )

    def emit_shield_sparkle(self, x, y):
        """Emits a faint ambient shield sparkle around the player."""
        self.particles.append(
            Particle(
                x,
                y,
                random.uniform(-15, 15),
                random.uniform(-15, 15),
                random.uniform(2.0, 4.0),
                0.5,
                (200, 245, 255),
                CYAN,
                random.uniform(0.25, 0.45),
                shape="glow",
                drag=0.95,
                blend_add=True,
            )
        )


# --- ANIMATED STARFIELD ---
class Starfield:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.layers = []
        # Layer configs: (count, speed_base, size_range, base_brightness, twinkle_speed)
        configs = [
            (85, 30, (1.0, 1.2), 120, 1.5),  # Distant background stars
            (55, 75, (1.4, 2.2), 180, 2.5),  # Midground stars
            (28, 140, (2.2, 3.2), 240, 4.0),  # Foreground fast glittering stars
        ]
        for count, speed, size_range, base_bright, twinkle_speed in configs:
            stars = []
            for _ in range(count):
                stars.append(
                    {
                        "x": random.uniform(0, width),
                        "y": random.uniform(0, height),
                        "size": random.uniform(size_range[0], size_range[1]),
                        "speed": speed * random.uniform(0.85, 1.2),
                        "brightness": base_bright,
                        "twinkle_phase": random.uniform(0, math.tau),
                        "twinkle_speed": twinkle_speed * random.uniform(0.7, 1.4),
                        "color_tint": random.choice(
                            [
                                (255, 255, 255),
                                (220, 240, 255),
                                (200, 225, 255),
                                (255, 240, 210),
                                (255, 220, 200),
                            ]
                        ),
                    }
                )
            self.layers.append(stars)

    def update(self, dt, speed_multiplier=1.0):
        for stars in self.layers:
            for s in stars:
                s["y"] += s["speed"] * speed_multiplier * dt
                if s["y"] > self.height:
                    s["y"] -= self.height
                    s["x"] = random.uniform(0, self.width)
                s["twinkle_phase"] = (s["twinkle_phase"] + s["twinkle_speed"] * dt) % math.tau

    def draw(self, surface):
        for stars in self.layers:
            for s in stars:
                twinkle = (math.sin(s["twinkle_phase"]) + 1.0) * 0.5  # 0.0 to 1.0
                alpha = int(s["brightness"] * (0.55 + 0.45 * twinkle))
                alpha = min(255, max(20, alpha))
                tint = s["color_tint"]
                color = (
                    int(tint[0] * alpha / 255),
                    int(tint[1] * alpha / 255),
                    int(tint[2] * alpha / 255),
                )
                x, y = int(s["x"]), int(s["y"])
                size = s["size"]

                if size > 2.0:
                    # Draw a glowing cross / star sparkle for bright foreground stars
                    pygame.draw.circle(surface, color, (x, y), int(size))
                    if alpha > 180:
                        pygame.draw.line(surface, color, (x - 2, y), (x + 2, y), 1)
                        pygame.draw.line(surface, color, (x, y - 2), (x, y + 2), 1)
                else:
                    surface.set_at((x, y), color)


# --- GAMEPLAY OBJECTS ---
class FallingObject:
    def __init__(self, kind, x, speed):
        self.kind = kind
        self.speed = speed
        self.rot_angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-120, 120)
        self.time_alive = 0.0

        if kind == "meteor":
            size = random.randint(22, 46)
            self.rect = pygame.Rect(x, -size, size, size)
            self.color = random.choice([(255, 108, 70), (255, 155, 60), (220, 75, 95), (245, 130, 75)])
            self.crater_seed = [
                (random.uniform(-0.35, 0.35), random.uniform(-0.35, 0.35), random.uniform(0.12, 0.28))
                for _ in range(random.randint(2, 4))
            ]
        else:
            self.rect = pygame.Rect(x, -26, 26, 26)
            self.color = CYAN if kind == "shield" else GOLD

    def update(self, dt, particle_manager=None):
        self.rect.y += round(self.speed * dt)
        self.rot_angle = (self.rot_angle + self.rot_speed * dt) % 360
        self.time_alive += dt

        if self.kind == "meteor" and particle_manager is not None:
            particle_manager.emit_meteor_trail(
                self.rect.centerx, self.rect.centery, self.rect.width // 2, self.color
            )

    def draw(self, screen):
        center = self.rect.center
        rad = self.rect.width // 2

        if self.kind == "meteor":
            # Outer atmospheric burning halo
            halo_surf = pygame.Surface((rad * 2 + 16, rad * 2 + 16), pygame.SRCALPHA)
            pygame.draw.circle(halo_surf, (*self.color, 45), (rad + 8, rad + 8), rad + 6)
            pygame.draw.circle(halo_surf, (255, 200, 80, 80), (rad + 8, rad + 8), rad + 2)
            screen.blit(halo_surf, (center[0] - rad - 8, center[1] - rad - 8), special_flags=pygame.BLEND_ADD)

            # Core meteor rock body
            pygame.draw.circle(screen, self.color, center, rad)
            pygame.draw.circle(screen, (85, 38, 48), center, max(2, rad // 4))

            # Internal crater details rotated
            for cx_pct, cy_pct, cr_pct in self.crater_seed:
                rad_ang = math.radians(self.rot_angle)
                cos_a, sin_a = math.cos(rad_ang), math.sin(rad_ang)
                rx = (cx_pct * cos_a - cy_pct * sin_a) * rad
                ry = (cx_pct * sin_a + cy_pct * cos_a) * rad
                cr_rad = max(1, int(cr_pct * rad))
                pygame.draw.circle(screen, (60, 25, 35), (int(center[0] + rx), int(center[1] + ry)), cr_rad)

            # Fiery rim highlight on top
            pygame.draw.arc(
                screen,
                (255, 240, 180),
                (center[0] - rad + 2, center[1] - rad + 2, rad * 2 - 4, rad * 2 - 4),
                math.radians(30),
                math.radians(150),
                2,
            )
        else:
            # Power-up with glowing bobbing effect and pulsing aura
            pulse = math.sin(self.time_alive * 6.0) * 2.0
            glow_rad = int(rad + 6 + pulse)
            glow_surf = pygame.Surface((glow_rad * 2, glow_rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*self.color, 60), (glow_rad, glow_rad), glow_rad)
            screen.blit(glow_surf, (center[0] - glow_rad, center[1] - glow_rad), special_flags=pygame.BLEND_ADD)

            # Body rect
            pygame.draw.rect(screen, self.color, self.rect, border_radius=7)
            pygame.draw.rect(screen, WHITE, self.rect, width=2, border_radius=7)

            if self.kind == "shield":
                # Animated energy shield icon
                ring_r = 7 + int(math.sin(self.time_alive * 8.0) * 1.5)
                pygame.draw.circle(screen, WHITE, center, max(4, ring_r), 2)
                pygame.draw.circle(screen, (200, 245, 255), center, 3)
            else:
                # Golden Star/Diamond score icon
                ang = self.time_alive * 3.0
                pts = [
                    (center[0] + math.cos(ang + i * math.pi / 2) * 7, center[1] + math.sin(ang + i * math.pi / 2) * 7)
                    for i in range(4)
                ]
                pygame.draw.polygon(screen, WHITE, pts)


# --- MAIN GAME CLASS ---
class SpaceDodgeGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Meteor Space Dodge")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        # Fonts
        self.font = pygame.font.Font(None, 32)
        self.large_font = pygame.font.Font(None, 74)
        self.small_font = pygame.font.Font(None, 24)
        self.hud_font = pygame.font.Font(None, 36)

        # Systems & Assets
        self.particles = ParticleManager()
        self.starfield = Starfield(WIDTH, HEIGHT)
        self.background_img = self.load_background()
        self.ship_img = self.load_ship()

        # Dynamic Game Feel Controls
        self.screen_shake = 0.0  # Trauma 0.0 to 1.0
        self.hit_flash_alpha = 0.0
        self.hit_flash_color = RED
        self.bank_angle = 0.0
        self.game_time = 0.0
        self.bg_scroll_y = 0.0

        # Save data & menu states
        self.data = self.load_data()
        self.volume = self.data["volume"]
        self.control_scheme = self.data["controls"]
        self.state = "menu"
        self.menu_index = 0
        self.settings_index = 0

        self.reset_game()

    @property
    def high_score(self):
        return self.data.get("high_score", 0)

    def load_background(self):
        path = get_asset_path("background_SD.jpg")
        if path:
            try:
                img = pygame.image.load(path).convert()
                return pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
            except Exception as err:
                print(f"Warning: Failed to load background image: {err}")
        # Fallback dark space gradient surface
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.fill(NAVY)
        return surf

    def load_ship(self):
        path = get_asset_path("spaceship.png")
        if path:
            try:
                img = pygame.image.load(path).convert_alpha()
                # Scale cleanly to player size
                return pygame.transform.smoothscale(img, PLAYER_SIZE)
            except Exception as err:
                print(f"Warning: Failed to load spaceship image: {err}")
        return None

    def load_data(self):
        defaults = {
            "high_score": 0,
            "highest_level": 0,
            "meteors_dodged": 0,
            "games_played": 0,
            "volume": 0.6,
            "controls": "Arrows",
        }
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SAVE_FILE)
        try:
            with open(path, "r", encoding="utf-8") as file:
                defaults.update(json.load(file))
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        return defaults

    def save_data(self):
        self.data.update({"volume": self.volume, "controls": self.control_scheme})
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SAVE_FILE)
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(self.data, file, indent=2)
        except OSError:
            pass

    def trigger_shake(self, amount=0.5):
        """Adds trauma for screen shake."""
        self.screen_shake = min(1.0, self.screen_shake + amount)

    def trigger_flash(self, color=RED, alpha=180):
        """Triggers a full-screen impact / collection flash."""
        self.hit_flash_color = color
        self.hit_flash_alpha = float(alpha)

    def reset_game(self):
        self.player = pygame.Rect(WIDTH // 2 - PLAYER_SIZE[0] // 2, HEIGHT - 110, *PLAYER_SIZE)
        self.objects = []
        self.score = 0.0
        self.level = 1
        self.lives = LIVES
        self.shield_time = 0.0
        self.invulnerable_time = 0.0
        self.spawn_timer = 0.75
        self.power_timer = random.uniform(8, 13)
        self.run_meteors_dodged = 0
        self.bank_angle = 0.0
        self.screen_shake = 0.0
        self.hit_flash_alpha = 0.0

    def start_game(self):
        self.reset_game()
        self.data["games_played"] += 1
        self.save_data()
        self.state = "playing"

    def spawn_meteor(self):
        speed = random.uniform(250, 360) + (self.level - 1) * 40
        self.objects.append(FallingObject("meteor", random.randint(10, WIDTH - 52), speed))

    def spawn_power_up(self):
        kind = random.choice(["shield", "score"])
        speed = 220 + self.level * 15
        self.objects.append(FallingObject(kind, random.randint(20, WIDTH - 46), speed))

    def update_playing(self, dt):
        keys = pygame.key.get_pressed()
        left_key, right_key = (
            (pygame.K_LEFT, pygame.K_RIGHT) if self.control_scheme == "Arrows" else (pygame.K_a, pygame.K_d)
        )

        move_dir = int(keys[right_key]) - int(keys[left_key])
        self.player.x += round(move_dir * PLAYER_SPEED * dt)
        self.player.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

        # Smooth banking tilt when steering
        target_bank = -move_dir * 14.0
        self.bank_angle += (target_bank - self.bank_angle) * min(1.0, 16.0 * dt)

        # Player Engine Exhaust Animation
        engine_pos_x = self.player.centerx
        engine_pos_y = self.player.bottom - 4
        self.particles.emit_engine(engine_pos_x, engine_pos_y, move_dir, speed_boost=1.0 + (self.level * 0.05))

        # Ambient shield sparkles when shield is active
        if self.shield_time > 0:
            if random.random() < 0.35:
                ang = random.uniform(0, math.tau)
                r = 44 + random.uniform(-4, 4)
                self.particles.emit_shield_sparkle(
                    self.player.centerx + math.cos(ang) * r,
                    self.player.centery + math.sin(ang) * r,
                )

        # Progression & Timers
        self.score += dt * (10 + self.level * 2.5)
        self.level = 1 + int(self.score // 160)
        self.shield_time = max(0.0, self.shield_time - dt)
        self.invulnerable_time = max(0.0, self.invulnerable_time - dt)

        # Meteor Spawning
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_meteor()
            self.spawn_timer = max(0.16, 0.70 - self.level * 0.045)

        # Powerup Spawning
        self.power_timer -= dt
        if self.power_timer <= 0:
            self.spawn_power_up()
            self.power_timer = random.uniform(8, 13)

        # Object updates & collisions
        for obj in self.objects[:]:
            obj.update(dt, self.particles)

            if obj.rect.top > HEIGHT + 20:
                self.objects.remove(obj)
                if obj.kind == "meteor":
                    self.run_meteors_dodged += 1
                    self.data["meteors_dodged"] += 1
                continue

            # Collision check with player
            if not obj.rect.colliderect(self.player):
                continue

            self.objects.remove(obj)

            if obj.kind == "shield":
                self.shield_time = 6.0
                self.particles.emit_collect(obj.rect.centerx, obj.rect.centery, "shield")
                self.trigger_flash(CYAN, 100)
                self.trigger_shake(0.18)

            elif obj.kind == "score":
                self.score += 80
                self.particles.emit_collect(obj.rect.centerx, obj.rect.centery, "score")
                self.trigger_flash(GOLD, 90)
                self.trigger_shake(0.15)

            elif obj.kind == "meteor":
                if self.shield_time > 0:
                    # Shield absorbs & deflects impact!
                    self.particles.emit_explosion(obj.rect.centerx, obj.rect.centery, radius=32, count=22)
                    self.trigger_shake(0.35)
                    self.trigger_flash(CYAN, 120)
                elif self.invulnerable_time <= 0:
                    # Direct Hit!
                    self.lives -= 1
                    self.invulnerable_time = 1.4
                    self.trigger_shake(0.7)
                    self.trigger_flash(RED, 210)
                    self.particles.emit_explosion(self.player.centerx, self.player.centery, radius=48, count=42, is_player=True)

                    if self.lives <= 0:
                        self.trigger_shake(1.0)
                        self.particles.emit_explosion(self.player.centerx, self.player.centery, radius=70, count=65, is_player=True)
                        self.finish_game()

    def finish_game(self):
        self.score = int(self.score)
        self.data["high_score"] = max(self.high_score, self.score)
        self.data["highest_level"] = max(self.data["highest_level"], self.level)
        self.save_data()
        self.state = "game_over"

    def centered(self, text, font, y, color=WHITE, shadow=True):
        if shadow:
            s_img = font.render(text, True, (0, 0, 0))
            self.screen.blit(s_img, s_img.get_rect(center=(WIDTH // 2 + 2, y + 2)))
        image = font.render(text, True, color)
        self.screen.blit(image, image.get_rect(center=(WIDTH // 2, y)))

    def options(self, entries, selected, y):
        for index, entry in enumerate(entries):
            prefix = "> " if index == selected else "  "
            col = GOLD if index == selected else WHITE
            self.centered(prefix + entry, self.font, y + 50 * index, col)

    def draw_background(self, dt):
        """Renders the scrolling space backdrop, nebula tint and multi-layered starfield."""
        # Scroll background slowly
        scroll_speed = 40.0 if self.state != "playing" else (55.0 + self.level * 8.0)
        self.bg_scroll_y = (self.bg_scroll_y + scroll_speed * dt) % HEIGHT

        # Seamless vertical blit for infinite scroll
        rel_y = int(self.bg_scroll_y)
        self.screen.blit(self.background_img, (0, rel_y))
        if rel_y > 0:
            self.screen.blit(self.background_img, (0, rel_y - HEIGHT))

        # Soft deep space nebula vignette overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*NAVY, 110))
        self.screen.blit(overlay, (0, 0))

        # Parallax Starfield
        star_speed_mult = 1.0 if self.state != "playing" else (1.0 + (self.level - 1) * 0.12)
        self.starfield.update(dt, speed_multiplier=star_speed_mult)
        self.starfield.draw(self.screen)

    def draw_player_engine(self, surface, center_x, bottom_y):
        """Draws animated plasma thruster flame with core and outer glow."""
        flame_time = self.game_time * 24.0
        jitter = math.sin(flame_time) * 3.0 + random.uniform(-2.0, 2.0)
        flame_len = 22.0 + jitter + (self.level * 1.2 if self.state == "playing" else 0.0)
        flame_w = 12.0 + math.cos(flame_time * 0.8) * 2.0

        # Outer glowing flame
        flame_surf = pygame.Surface((int(flame_w + 20), int(flame_len + 20)), pygame.SRCALPHA)
        local_pts = [
            (10, 2),
            (10 + flame_w, 2),
            (10 + flame_w / 2, 2 + flame_len),
        ]
        pygame.draw.polygon(flame_surf, (*CYAN, 180), local_pts)
        surface.blit(flame_surf, (center_x - flame_w / 2 - 10, bottom_y - 4), special_flags=pygame.BLEND_ADD)

        # Inner hot white core
        core_len = flame_len * 0.55
        core_w = flame_w * 0.45
        core_pts = [
            (center_x - core_w / 2, bottom_y - 2),
            (center_x + core_w / 2, bottom_y - 2),
            (center_x, bottom_y + core_len),
        ]
        pygame.draw.polygon(surface, WHITE, core_pts)

    def draw_shield(self, surface, center):
        """Renders an animated, glowing, rotating energy shield."""
        t = self.game_time
        base_rad = 44
        pulse = math.sin(t * 7.0) * 3.0
        rad = int(base_rad + pulse)

        # Shield expiring warning pulsation
        is_expiring = self.shield_time < 1.6
        if is_expiring and int(t * 14) % 2 == 0:
            shield_col = (255, 110, 110)
            glow_alpha = 90
        else:
            shield_col = CYAN
            glow_alpha = 75

        # Translucent shield glow bubble
        shield_surf = pygame.Surface((rad * 2 + 16, rad * 2 + 16), pygame.SRCALPHA)
        pygame.draw.circle(shield_surf, (*shield_col, glow_alpha), (rad + 8, rad + 8), rad)
        pygame.draw.circle(shield_surf, (*shield_col, 160), (rad + 8, rad + 8), rad, 2)
        surface.blit(shield_surf, (center[0] - rad - 8, center[1] - rad - 8), special_flags=pygame.BLEND_ADD)

        # Rotating energy arcs
        num_arcs = 3
        for i in range(num_arcs):
            start_ang = t * 3.5 + i * (math.tau / num_arcs)
            end_ang = start_ang + math.pi * 0.42
            pygame.draw.arc(
                surface,
                WHITE if not is_expiring else (255, 200, 200),
                (center[0] - rad + 2, center[1] - rad + 2, (rad - 2) * 2, (rad - 2) * 2),
                start_ang,
                end_ang,
                2,
            )

        # Counter-rotating outer tech ring
        pygame.draw.circle(surface, shield_col, center, rad + 3, 1)

    def draw_player(self, surface):
        """Draws the player spaceship with tilt bank, engine fire, invulnerability flash, and shield."""
        center_x, center_y = self.player.centerx, self.player.centery

        # Invulnerability blinking
        if self.invulnerable_time > 0 and int(self.invulnerable_time * 16) % 2 != 0:
            return

        # Engine flame
        self.draw_player_engine(surface, center_x, self.player.bottom)

        # Spaceship image or procedural fallback
        if self.ship_img:
            # Rotate for banking tilt
            rotated_ship = pygame.transform.rotozoom(self.ship_img, self.bank_angle, 1.0)
            rect = rotated_ship.get_rect(center=(center_x, center_y))

            # Hit flash white tint when just damaged
            if self.invulnerable_time > 1.1:
                flash_surf = rotated_ship.copy()
                flash_surf.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(flash_surf, rect)
            else:
                surface.blit(rotated_ship, rect)
        else:
            # High-detail procedural fighter ship
            ship_col = CYAN if self.shield_time > 0 else WHITE
            pts = [
                (self.player.midtop[0], self.player.midtop[1] - 4),
                (self.player.bottomright[0] + 2, self.player.bottomright[1]),
                (self.player.centerx, self.player.bottom - 8),
                (self.player.bottomleft[0] - 2, self.player.bottomleft[1]),
            ]
            pygame.draw.polygon(surface, ship_col, pts)
            pygame.draw.polygon(surface, (40, 90, 180), pts, 2)
            # Cockpit
            pygame.draw.ellipse(
                surface, (80, 210, 255), (self.player.centerx - 6, self.player.centery - 10, 12, 18)
            )

        # Animated Shield
        if self.shield_time > 0:
            self.draw_shield(surface, (center_x, center_y))

    def draw_hud(self):
        """Draws modern glassmorphic HUD bar with score, level, lives and active shield."""
        # Top HUD Bar panel
        hud_panel = pygame.Surface((WIDTH, 56), pygame.SRCALPHA)
        hud_panel.fill((6, 12, 32, 160))
        pygame.draw.line(hud_panel, (40, 70, 120, 120), (0, 55), (WIDTH, 55), 1)
        self.screen.blit(hud_panel, (0, 0))

        # Score & Level
        score_text = self.font.render(f"SCORE: {int(self.score):05d}", True, WHITE)
        level_text = self.font.render(f"LEVEL: {self.level}", True, CYAN)
        self.screen.blit(score_text, (20, 16))
        self.screen.blit(level_text, (240, 16))

        # Lives indicators (heart / ship icons)
        lives_label = self.font.render("LIVES:", True, MUTED)
        self.screen.blit(lives_label, (420, 16))
        for i in range(LIVES):
            col = RED if i < self.lives else (60, 60, 80)
            hx = 510 + i * 26
            hy = 26
            # Draw glowing life crystal / dot
            pygame.draw.circle(self.screen, col, (hx, hy), 8)
            if i < self.lives:
                pygame.draw.circle(self.screen, (255, 180, 190), (hx - 2, hy - 2), 3)

        # High score
        best_str = f"BEST: {self.high_score:05d}"
        best_surf = self.font.render(best_str, True, GOLD)
        self.screen.blit(best_surf, (WIDTH - best_surf.get_width() - 22, 16))

        # Shield countdown gauge
        if self.shield_time > 0:
            gauge_w = 160
            gauge_h = 10
            gx = 20
            gy = 68
            # Background bar
            pygame.draw.rect(self.screen, (15, 25, 50), (gx, gy, gauge_w, gauge_h), border_radius=5)
            # Fill bar
            pct = min(1.0, self.shield_time / 6.0)
            bar_col = (255, 90, 90) if self.shield_time < 1.6 else CYAN
            pygame.draw.rect(self.screen, bar_col, (gx, gy, int(gauge_w * pct), gauge_h), border_radius=5)
            pygame.draw.rect(self.screen, WHITE, (gx, gy, gauge_w, gauge_h), 1, border_radius=5)
            shield_lbl = self.small_font.render(f"SHIELD {self.shield_time:0.1f}s", True, bar_col)
            self.screen.blit(shield_lbl, (gx + gauge_w + 10, gy - 2))

    def draw_game(self):
        # Falling objects
        for obj in self.objects:
            obj.draw(self.screen)

        # Particles (engine, trails, explosions, sparks)
        self.particles.draw(self.screen)

        # Player
        if self.lives > 0:
            self.draw_player(self.screen)

        # HUD
        self.draw_hud()

    def draw(self, dt):
        # Background & Starfield
        self.draw_background(dt)

        if self.state == "menu":
            self.particles.draw(self.screen)
            # Glowing title
            title_glow = (math.sin(self.game_time * 3.5) + 1.0) * 0.5
            title_col = (
                int(89 + 50 * title_glow),
                int(220 + 35 * title_glow),
                255,
            )
            self.centered("METEOR SPACE DODGE", self.large_font, 210, title_col)
            self.centered("Navigate the cosmos. Dodge incoming meteors.", self.font, 280, (200, 220, 255))
            self.options(["Start Mission", "Settings", "Statistics", "Quit"], self.menu_index, 375)
            self.centered("Arrow keys: navigate   |   Enter / Space: confirm", self.small_font, 630, MUTED)

        elif self.state == "settings":
            self.particles.draw(self.screen)
            self.centered("SETTINGS", self.large_font, 200, CYAN)
            self.options(
                [f"Master Volume: {int(self.volume * 100)}%", f"Steering Controls: {self.control_scheme}"],
                self.settings_index,
                355,
            )
            self.centered("Left / Right: change option   |   Esc: return to menu", self.small_font, 540, MUTED)

        elif self.state == "statistics":
            self.particles.draw(self.screen)
            self.centered("MISSION RECORDS", self.large_font, 200, CYAN)
            self.centered(f"High Score: {self.data['high_score']}", self.font, 320, GOLD)
            self.centered(f"Highest Level Reached: {self.data['highest_level']}", self.font, 370)
            self.centered(f"Total Meteors Dodged: {self.data['meteors_dodged']}", self.font, 420)
            self.centered(f"Total Missions Launched: {self.data['games_played']}", self.font, 470)
            self.centered("Press Esc or Enter to return", self.small_font, 570, MUTED)

        else:
            self.draw_game()

            if self.state == "paused":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((5, 10, 25, 175))
                self.screen.blit(overlay, (0, 0))
                self.centered("PAUSED", self.large_font, HEIGHT // 2 - 30, GOLD)
                self.centered("Press P or Esc to resume flight", self.font, HEIGHT // 2 + 40, WHITE)

            elif self.state == "game_over":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((20, 5, 10, 190))
                self.screen.blit(overlay, (0, 0))
                self.centered("MISSION TERMINATED", self.large_font, HEIGHT // 2 - 100, RED)
                self.centered(f"Final Score: {self.score}    |    High Score: {self.high_score}", self.font, HEIGHT // 2 - 25, WHITE)
                self.centered(
                    f"Level Reached: {self.level}    |    Meteors Dodged: {self.run_meteors_dodged}",
                    self.small_font,
                    HEIGHT // 2 + 30,
                    CYAN,
                )
                self.centered("Press R or Enter to relaunch   |   Esc for menu", self.font, HEIGHT // 2 + 95, GOLD)

        # Full-screen Hit / Collection Flash
        if self.hit_flash_alpha > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((*self.hit_flash_color[:3], int(self.hit_flash_alpha)))
            self.screen.blit(flash_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        # Apply Screen Shake Offset
        if self.screen_shake > 0:
            shake_mag = (self.screen_shake ** 2) * 18.0
            ox = random.uniform(-shake_mag, shake_mag)
            oy = random.uniform(-shake_mag, shake_mag)
            # Shift buffer
            shake_buffer = self.screen.copy()
            self.screen.fill(DARK_BG)
            self.screen.blit(shake_buffer, (int(ox), int(oy)))

        pygame.display.flip()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type != pygame.KEYDOWN:
            return True

        if self.state == "menu":
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                self.menu_index = (self.menu_index + (1 if event.key == pygame.K_DOWN else -1)) % 4
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.menu_index == 0:
                    self.start_game()
                elif self.menu_index == 1:
                    self.state = "settings"
                elif self.menu_index == 2:
                    self.state = "statistics"
                else:
                    return False
            elif event.key == pygame.K_ESCAPE:
                return False

        elif self.state == "settings":
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                self.settings_index = 1 - self.settings_index
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN, pygame.K_SPACE):
                if self.settings_index == 0:
                    delta = -0.1 if event.key == pygame.K_LEFT else 0.1
                    self.volume = max(0.0, min(1.0, round(self.volume + delta, 1)))
                else:
                    self.control_scheme = "A / D" if self.control_scheme == "Arrows" else "Arrows"
                self.save_data()
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"

        elif self.state == "statistics" and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            self.state = "menu"

        elif self.state == "playing":
            if event.key == pygame.K_p:
                self.state = "paused"
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"
                self.save_data()

        elif self.state == "paused":
            if event.key in (pygame.K_p, pygame.K_ESCAPE):
                self.state = "playing"

        elif self.state == "game_over":
            if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self.start_game()
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"

        return True

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.game_time += dt

            # Screen shake and hit flash decay
            self.screen_shake = max(0.0, self.screen_shake - dt * 2.2)
            self.hit_flash_alpha = max(0.0, self.hit_flash_alpha - dt * 500.0)

            # Particles update
            self.particles.update(dt)

            for event in pygame.event.get():
                running = self.handle_event(event) and running

            if self.state == "playing":
                self.update_playing(dt)

            self.draw(dt)

        self.save_data()
        pygame.quit()


if __name__ == "__main__":
    SpaceDodgeGame().run()
