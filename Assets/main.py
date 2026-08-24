

import json
import os
import random

import pygame

WIDTH, HEIGHT, FPS = 1000, 800, 60
PLAYER_SIZE, PLAYER_SPEED, LIVES = (48, 64), 520, 3
SAVE_FILE = "space_dodge_high_score.json"
WHITE, CYAN, GOLD, RED, NAVY, MUTED = (245, 248, 255), (89, 220, 255), (255, 210, 68), (255, 92, 100), (8, 16, 42), (130, 145, 175)


class FallingObject:
    def __init__(self, kind, x, speed):
        self.kind, self.speed = kind, speed
        if kind == "meteor":
            size = random.randint(18, 42)
            self.rect = pygame.Rect(x, -size, size, size)
            self.color = random.choice([(255, 104, 75), (244, 152, 72), (200, 83, 100)])
        else:
            self.rect = pygame.Rect(x, -24, 24, 24)
            self.color = CYAN if kind == "shield" else GOLD

    def update(self, dt):
        self.rect.y += round(self.speed * dt)

    def draw(self, screen):
        if self.kind == "meteor":
            pygame.draw.circle(screen, self.color, self.rect.center, self.rect.width // 2)
            pygame.draw.circle(screen, (92, 47, 58), self.rect.center, max(2, self.rect.width // 6))
        else:
            pygame.draw.rect(screen, self.color, self.rect, border_radius=6)
            if self.kind == "shield":
                pygame.draw.circle(screen, WHITE, self.rect.center, 7, 2)
            else:
                pygame.draw.line(screen, WHITE, self.rect.midtop, self.rect.midbottom, 2)



class SpaceDodgeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Space Dodge")
        self.clock = pygame.time.Clock()
        self.font, self.large_font, self.small_font = pygame.font.Font(None, 32), pygame.font.Font(None, 72), pygame.font.Font(None, 24)
        self.background = self.load_background()
        self.data = self.load_data()
        self.volume, self.control_scheme = self.data["volume"], self.data["controls"]
        self.state, self.menu_index, self.settings_index = "menu", 0, 0
        self.reset_game()

    @property
    def high_score(self):
        return self.data["high_score"]

    def load_background(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background_SD.jpg")
        if os.path.exists(path):
            return pygame.transform.smoothscale(pygame.image.load(path).convert(), (WIDTH, HEIGHT))
        surface = pygame.Surface((WIDTH, HEIGHT))
        surface.fill(NAVY)
        return surface

    def load_data(self):
        defaults = {"high_score": 0, "highest_level": 0, "meteors_dodged": 0, "games_played": 0, "volume": 0.6, "controls": "Arrows"}
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

    def reset_game(self):
        self.player = pygame.Rect(WIDTH // 2 - PLAYER_SIZE[0] // 2, HEIGHT - 100, *PLAYER_SIZE)
        self.objects = []
        self.score, self.level, self.lives = 0.0, 1, LIVES
        self.shield_time = self.invulnerable_time = 0.0
        self.spawn_timer, self.power_timer = 0.75, random.uniform(8, 13)
        self.run_meteors_dodged = 0

    def start_game(self):
        self.reset_game()
        self.data["games_played"] += 1
        self.save_data()
        self.state = "playing"

    def spawn_meteor(self):
        self.objects.append(FallingObject("meteor", random.randint(0, WIDTH - 42), random.uniform(240, 350) + (self.level - 1) * 42))

    def spawn_power_up(self):
        self.objects.append(FallingObject(random.choice(["shield", "score"]), random.randint(0, WIDTH - 24), 220 + self.level * 15))

    def update_playing(self, dt):
        keys = pygame.key.get_pressed()
        left, right = (pygame.K_LEFT, pygame.K_RIGHT) if self.control_scheme == "Arrows" else (pygame.K_a, pygame.K_d)
        self.player.x += round((int(keys[right]) - int(keys[left])) * PLAYER_SPEED * dt)
        self.player.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
        self.score += dt * (10 + self.level * 2)
        self.level = 1 + int(self.score // 150)
        self.shield_time, self.invulnerable_time = max(0, self.shield_time - dt), max(0, self.invulnerable_time - dt)
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_meteor()
            self.spawn_timer = max(0.18, 0.72 - self.level * 0.045)
        self.power_timer -= dt
        if self.power_timer <= 0:
            self.spawn_power_up()
            self.power_timer = random.uniform(8, 13)
        for obj in self.objects[:]:
            obj.update(dt)
            if obj.rect.top > HEIGHT:
                self.objects.remove(obj)
                if obj.kind == "meteor":
                    self.run_meteors_dodged += 1
                    self.data["meteors_dodged"] += 1
                continue
            if not obj.rect.colliderect(self.player):
                continue
            self.objects.remove(obj)
            if obj.kind == "shield":
                self.shield_time = 5.0
            elif obj.kind == "score":
                self.score += 75
            elif self.shield_time <= 0 and self.invulnerable_time <= 0:
                self.lives -= 1
                self.invulnerable_time = 1.2
                if self.lives <= 0:
                    self.finish_game()

    def finish_game(self):
        self.score = int(self.score)
        self.data["high_score"] = max(self.high_score, self.score)
        self.data["highest_level"] = max(self.data["highest_level"], self.level)
        self.save_data()
        self.state = "game_over"

    def centered(self, text, font, y, color=WHITE):
        image = font.render(text, True, color)
        self.screen.blit(image, image.get_rect(center=(WIDTH // 2, y)))

    def options(self, entries, selected, y):
        for index, entry in enumerate(entries):
            self.centered(("> " if index == selected else "  ") + entry, self.font, y + 48 * index, GOLD if index == selected else WHITE)

    def draw_background(self):
        self.screen.blit(self.background, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*NAVY, 105))
        self.screen.blit(overlay, (0, 0))

    def draw_game(self):
        for obj in self.objects:
            obj.draw(self.screen)
        ship_color = CYAN if self.shield_time > 0 else WHITE
        if self.invulnerable_time <= 0 or int(self.invulnerable_time * 12) % 2 == 0:
            pygame.draw.polygon(self.screen, ship_color, [self.player.midtop, self.player.bottomright, self.player.bottomleft])
            pygame.draw.rect(self.screen, (38, 76, 145), (self.player.x + 13, self.player.y + 28, 22, 22))
        if self.shield_time > 0:
            pygame.draw.circle(self.screen, CYAN, self.player.center, 45, 2)
        self.screen.blit(self.font.render(f"Score: {int(self.score):04d}    Level: {self.level}    Lives: {self.lives}", True, WHITE), (18, 16))
        best = self.small_font.render(f"Best: {self.high_score:04d}", True, GOLD)
        self.screen.blit(best, (WIDTH - best.get_width() - 18, 20))
        if self.shield_time > 0:
            self.screen.blit(self.small_font.render(f"Shield {self.shield_time:0.1f}s", True, CYAN), (18, 52))

    def draw(self):
        self.draw_background()
        if self.state == "menu":
            self.centered("SPACE DODGE", self.large_font, 220, CYAN)
            self.centered("Survive the meteor field.", self.font, 290)
            self.options(["Start Game", "Settings", "Statistics", "Quit"], self.menu_index, 380)
            self.centered("Arrow keys: select   Enter: confirm", self.small_font, 625, MUTED)
        elif self.state == "settings":
            self.centered("SETTINGS", self.large_font, 210, CYAN)
            self.options([f"Volume: {int(self.volume * 100)}%", f"Controls: {self.control_scheme}"], self.settings_index, 360)
            self.centered("Left/Right: change    Esc: back", self.small_font, 530, MUTED)
        elif self.state == "statistics":
            self.centered("STATISTICS", self.large_font, 210, CYAN)
            self.centered(f"Highest Level: {self.data['highest_level']}", self.font, 350)
            self.centered(f"Meteors Dodged: {self.data['meteors_dodged']}", self.font, 405)
            self.centered(f"Games Played: {self.data['games_played']}", self.font, 460)
            self.centered("Esc or Enter: back", self.small_font, 560, MUTED)
        else:
            self.draw_game()
            if self.state == "paused":
                self.centered("PAUSED", self.large_font, HEIGHT // 2, GOLD)
                self.centered("Press P to continue", self.font, HEIGHT // 2 + 60)
            elif self.state == "game_over":
                self.centered("MISSION FAILED", self.large_font, HEIGHT // 2 - 80, RED)
                self.centered(f"Score: {self.score}    High Score: {self.high_score}", self.font, HEIGHT // 2 - 15)
                self.centered(f"Level reached: {self.level}    Meteors dodged: {self.run_meteors_dodged}", self.small_font, HEIGHT // 2 + 35)
                self.centered("Press R or Enter to restart  |  Esc for menu", self.font, HEIGHT // 2 + 90, GOLD)
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
                if self.menu_index == 0: self.start_game()
                elif self.menu_index == 1: self.state = "settings"
                elif self.menu_index == 2: self.state = "statistics"
                else: return False
            elif event.key == pygame.K_ESCAPE: return False
        elif self.state == "settings":
            if event.key in (pygame.K_UP, pygame.K_DOWN): self.settings_index = 1 - self.settings_index
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN, pygame.K_SPACE):
                if self.settings_index == 0:
                    self.volume = max(0, min(1, round(self.volume + (-.1 if event.key == pygame.K_LEFT else .1), 1)))
                else: self.control_scheme = "A / D" if self.control_scheme == "Arrows" else "Arrows"
                self.save_data()
            elif event.key == pygame.K_ESCAPE: self.state = "menu"
        elif self.state == "statistics" and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE): self.state = "menu"
        elif self.state == "playing":
            if event.key == pygame.K_p: self.state = "paused"
            elif event.key == pygame.K_ESCAPE: self.state = "menu"; self.save_data()
        elif self.state == "paused":
            if event.key == pygame.K_p: self.state = "playing"
            elif event.key == pygame.K_ESCAPE: self.state = "menu"; self.save_data()
        elif self.state == "game_over":
            if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE): self.start_game()
            elif event.key == pygame.K_ESCAPE: self.state = "menu"
        return True

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000, .05)
            for event in pygame.event.get(): running = self.handle_event(event) and running
            if self.state == "playing": self.update_playing(dt)
            self.draw()
        self.save_data()
        pygame.quit()


if __name__ == "__main__":
    SpaceDodgeGame().run()
