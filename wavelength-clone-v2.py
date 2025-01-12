import pygame
import sys
import random
import json
import math
from typing import List, Tuple, Dict

pygame.init()
pygame.font.init()

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_BLUE = (100, 149, 237)
DARK_BLUE = (25, 25, 112)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
BRONZE = (205, 127, 50)

ZONE_COLORS = [
    (46, 204, 113),
    (52, 152, 219),
    (241, 196, 15),
    (231, 76, 60)
]

REVEAL_ANIMATION_DURATION = 60
SCORE_POPUP_DURATION = 90

FONT_LARGE = pygame.font.Font(None, 48)
FONT_MEDIUM = pygame.font.Font(None, 36)
FONT_SMALL = pygame.font.Font(None, 24)

PSYCHIC_TURN = "psychic_turn"
GUESS_TURN = "guess_turn"
REVEAL = "reveal"
GAME_END = "game_end"

class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, color: Tuple[int, int, int]):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hovered = False

    def draw(self, screen: pygame.Surface):
        color = self.color if not self.hovered else tuple(max(0, c - 30) for c in self.color)
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        text_surface = FONT_SMALL.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

class Slider:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect = pygame.Rect(x, y, width, height)
        self.handle_rect = pygame.Rect(x, y - 10, 20, height + 20)
        self.value = 0.5
        self.dragging = False

    def draw(self, screen: pygame.Surface, color: Tuple[int, int, int] = GRAY):
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, DARK_BLUE, self.handle_rect, border_radius=5)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.handle_rect.collidepoint(event.pos):
                self.dragging = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.value = (event.pos[0] - self.rect.x) / self.rect.width
            self.value = max(0, min(1, self.value))
            self.handle_rect.centerx = self.rect.x + (self.value * self.rect.width)
            return True
        return False

    def set_value(self, value: float):
        self.value = max(0, min(1, value))
        self.handle_rect.centerx = self.rect.x + (self.value * self.rect.width)

class TextInput:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.active = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif len(self.text) < 30:
                self.text += event.unicode
        return False

    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, WHITE, self.rect, 2)
        text_surface = FONT_MEDIUM.render(self.text, True, WHITE)
        screen.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))

class ScorePopup:
    def __init__(self, score: int, x: int, y: int):
        self.score = score
        self.x = x
        self.y = y
        self.alpha = 255
        self.frame = 0
        
        if score == 5:
            self.color = GOLD
        elif score == 3:
            self.color = SILVER
        elif score == 1:
            self.color = BRONZE
        else:
            self.color = RED
    
    def update(self):
        self.frame += 1
        if self.frame > SCORE_POPUP_DURATION // 2:
            self.alpha = max(0, 255 * (1 - (self.frame - SCORE_POPUP_DURATION // 2) / (SCORE_POPUP_DURATION // 2)))
        self.y -= 1
    
    def draw(self, screen: pygame.Surface):
        score_text = FONT_LARGE.render(f"+{self.score}", True, self.color)
        score_surface = pygame.Surface(score_text.get_size(), pygame.SRCALPHA)
        score_surface.fill((0, 0, 0, 0))
        score_surface.blit(score_text, (0, 0))
        score_surface.set_alpha(self.alpha)
        screen.blit(score_surface, (self.x, self.y))

class WavelengthGame:
    def __init__(self, player_count: int):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Wavelength")
        self.clock = pygame.time.Clock()

        self.player_count = player_count
        self.current_player = 0
        self.scores = [0] * player_count
        self.game_state = PSYCHIC_TURN
        self.current_round = 0
        self.max_rounds = player_count

        self.slider = Slider(100, 300, WINDOW_WIDTH - 200, 20)
        self.clue_input = TextInput(WINDOW_WIDTH // 4, 200, WINDOW_WIDTH // 2, 40)
        
        new_spectrum_width = 150
        confirm_width = 100
        total_width = new_spectrum_width + confirm_width + 20
        start_x = WINDOW_WIDTH // 2 - total_width // 2
        
        self.new_spectrum_button = Button(start_x, 400, new_spectrum_width, 40, "New Spectrum", DARK_BLUE)
        self.confirm_button = Button(start_x + new_spectrum_width + 20, 400, confirm_width, 40, "Confirm", DARK_BLUE)

        self.reveal_progress = 0
        self.score_popup = None
        self.showing_distance = False

        with open('spectrum-pairs.json', 'r') as f:
            data = json.load(f)
            self.spectrum_pairs = data['spectrum_pairs']

        self.current_spectrum = random.choice(self.spectrum_pairs)
        self.current_clue = ""
        self.target_value = 0.5
        self.guess_value = 0.5

    def get_new_spectrum(self):
        available_pairs = [pair for pair in self.spectrum_pairs if pair != self.current_spectrum]
        if available_pairs:
            self.current_spectrum = random.choice(available_pairs)
            self.clue_input.text = ""
            self.slider.set_value(0.5)

    def calculate_score(self, guess: float, target: float) -> int:
        difference = abs(guess - target)
        if difference <= 0.05:
            return 5
        elif difference <= 0.15:
            return 3
        elif difference <= 0.25:
            return 1
        return 0

    def draw_scoring_zones(self, screen: pygame.Surface):
        zone_widths = [0.05, 0.15, 0.25, 1.0]
        prev_width = 0
        
        for i, width in enumerate(zone_widths):
            zone_width = int(self.slider.rect.width * width)
            left_pos = self.slider.rect.x + int(self.slider.rect.width * self.target_value) - zone_width // 2
            right_pos = left_pos + zone_width
            
            zone_surface = pygame.Surface((zone_width, self.slider.rect.height + 40), pygame.SRCALPHA)
            color = (*ZONE_COLORS[i], 128)
            pygame.draw.rect(zone_surface, color, (0, 0, zone_width, self.slider.rect.height + 40))
            
            screen.blit(zone_surface, (left_pos, self.slider.rect.y - 20))

    def draw_distance_indicator(self, screen: pygame.Surface):
        if not self.showing_distance:
            return
            
        guess_pos = self.slider.rect.x + (self.guess_value * self.slider.rect.width)
        target_pos = self.slider.rect.x + (self.target_value * self.slider.rect.width)
        
        center_y = self.slider.rect.y + self.slider.rect.height // 2
        distance = abs(guess_pos - target_pos)
        mid_point = (guess_pos + target_pos) // 2
        
        if distance > 0:
            control_point_y = center_y - 50
            points = [
                (guess_pos, center_y),
                (mid_point, control_point_y),
                (target_pos, center_y)
            ]
            pygame.draw.lines(screen, WHITE, False, points, 2)
            
            arrow_size = 10
            angle = math.atan2(center_y - control_point_y, target_pos - mid_point)
            pygame.draw.polygon(screen, WHITE, [
                (target_pos, center_y),
                (target_pos - arrow_size * math.cos(angle - math.pi/6),
                 center_y - arrow_size * math.sin(angle - math.pi/6)),
                (target_pos - arrow_size * math.cos(angle + math.pi/6),
                 center_y - arrow_size * math.sin(angle + math.pi/6))
            ])
            
            distance_percent = abs(self.guess_value - self.target_value) * 100
            distance_text = FONT_SMALL.render(f"{distance_percent:.1f}% off", True, WHITE)
            screen.blit(distance_text, (mid_point - distance_text.get_width()//2, control_point_y - 20))

    def draw(self):
        self.screen.fill(BLACK)

        left_word = FONT_LARGE.render(self.current_spectrum[0], True, WHITE)
        right_word = FONT_LARGE.render(self.current_spectrum[1], True, WHITE)
        self.screen.blit(left_word, (50, 50))
        self.screen.blit(right_word, (WINDOW_WIDTH - right_word.get_width() - 50, 50))

        if self.game_state == PSYCHIC_TURN:
            instruction = f"Player {self.current_player + 1}, enter your clue and set the target"
            self.clue_input.draw(self.screen)
            self.slider.draw(self.screen)
            self.new_spectrum_button.draw(self.screen)
            self.confirm_button.draw(self.screen)
        elif self.game_state == GUESS_TURN:
            instruction = f"Other players, make your guess! Clue: {self.current_clue}"
            self.slider.draw(self.screen)
            self.confirm_button.draw(self.screen)
        elif self.game_state == REVEAL:
            instruction = "Round Result"
            
            self.draw_scoring_zones(self.screen)
            self.slider.draw(self.screen)
            
            if self.reveal_progress < REVEAL_ANIMATION_DURATION:
                self.reveal_progress += 1
                progress_ratio = self.reveal_progress / REVEAL_ANIMATION_DURATION
                current_target = self.guess_value + (self.target_value - self.guess_value) * progress_ratio
                target_pos = self.slider.rect.x + (current_target * self.slider.rect.width)
            else:
                target_pos = self.slider.rect.x + (self.target_value * self.slider.rect.width)
                self.showing_distance = True
            
            pygame.draw.line(self.screen, RED, 
                           (target_pos, self.slider.rect.y - 20),
                           (target_pos, self.slider.rect.y + self.slider.rect.height + 20), 3)
            
            self.draw_distance_indicator(self.screen)
            
            if self.score_popup:
                self.score_popup.update()
                self.score_popup.draw(self.screen)
                if self.score_popup.alpha <= 0:
                    self.score_popup = None
            
            score = self.calculate_score(self.guess_value, self.target_value)
            score_text = FONT_LARGE.render(f"Score: {score}", True, WHITE)
            self.screen.blit(score_text, (WINDOW_WIDTH // 2 - score_text.get_width() // 2, 450))
            
        elif self.game_state == GAME_END:
            instruction = "Game Over!"
            for i, score in enumerate(self.scores):
                score_text = FONT_MEDIUM.render(f"Player {i + 1}: {score}", True, WHITE)
                self.screen.blit(score_text, (WINDOW_WIDTH // 2 - score_text.get_width() // 2, 200 + i * 50))

        instruction_surface = FONT_MEDIUM.render(instruction, True, WHITE)
        self.screen.blit(instruction_surface, (WINDOW_WIDTH // 2 - instruction_surface.get_width() // 2, 150))

        pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if self.game_state == PSYCHIC_TURN:
                self.clue_input.handle_event(event)
                self.slider.handle_event(event)
                
                if self.new_spectrum_button.handle_event(event):
                    self.get_new_spectrum()
                
                if self.confirm_button.handle_event(event) and self.clue_input.text:
                    self.current_clue = self.clue_input.text
                    self.target_value = self.slider.value
                    self.game_state = GUESS_TURN
                    self.slider.set_value(0.5)

            elif self.game_state == GUESS_TURN:
                self.slider.handle_event(event)
                if self.confirm_button.handle_event(event):
                    self.guess_value = self.slider.value
                    self.game_state = REVEAL
                    self.reveal_progress = 0
                    self.showing_distance = False
                    score = self.calculate_score(self.guess_value, self.target_value)
                    self.score_popup = ScorePopup(score, WINDOW_WIDTH // 2 - 20, 350)

            elif self.game_state == REVEAL:
                if self.confirm_button.handle_event(event):
                    score = self.calculate_score(self.guess_value, self.target_value)
                    self.scores[self.current_player] += score
                    self.current_player = (self.current_player + 1) % self.player_count
                    self.current_round += 1

                    if self.current_round >= self.max_rounds:
                        self.game_state = GAME_END
                    else:
                        self.game_state = PSYCHIC_TURN
                        self.current_spectrum = random.choice(self.spectrum_pairs)
                        self.clue_input.text = ""
                        self.slider.set_value(0.5)
                        self.score_popup = None
                        self.showing_distance = False

        return True
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = WavelengthGame(3)  # Start with 3 players
    game.run()
    pygame.quit()