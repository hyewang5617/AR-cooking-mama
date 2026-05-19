import cv2
import numpy as np
import time

from .hand_tracker import HandTracker
from .score_manager import ScoreManager
from .ui import (draw_panel, draw_progress_bar, draw_text, draw_text_centered,
                 dim, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER,
                 COLOR_WHITE, COLOR_GREY, FONT)
from .minigames.cutting import CuttingGame
from .minigames.stirring import StirringGame
from .minigames.flipping import FlippingGame

SEQUENCE = [CuttingGame, StirringGame, FlippingGame]
POINTS   = {'cut': 10, 'stir': 15, 'flip': 20}
BONUS    = {CuttingGame: 80, StirringGame: 100, FlippingGame: 120}


def _grade(score):
    if score >= 900: return 'S'
    if score >= 650: return 'A'
    if score >= 400: return 'B'
    if score >= 200: return 'C'
    return 'D'


class GameManager:
    def __init__(self):
        self.tracker  = HandTracker()
        self.score    = ScoreManager()
        self.state    = 'MENU'
        self.game_idx = 0
        self.game     = None
        self.hand_pos = None

        self._countdown_start = 0.0
        self._result_start    = 0.0
        self._game_start_score = 0
        self._last_success    = False
        self._last_game_score = 0
        self._player_name     = ''

    # ------------------------------------------------------------------ public

    def update(self, frame):
        results = self.tracker.process(frame)
        self.hand_pos = self.tracker.get_position(results, frame.shape)
        self.tracker.draw(frame, results)

        return {
            'MENU':       self._menu,
            'COUNTDOWN':  self._countdown,
            'PLAYING':    self._playing,
            'RESULT':     self._result,
            'NAME_INPUT': self._name_input,
            'GAME_OVER':  self._game_over,
            'RANKING':    self._ranking,
        }.get(self.state, lambda f: f)(frame)

    def handle_key(self, key):
        if self.state == 'MENU' and key == ord(' '):
            self._begin_countdown()

        elif self.state == 'NAME_INPUT':
            if key == 13 and self._player_name:
                self.score.save(self._player_name)
                self.state = 'GAME_OVER'
            elif key == 8:
                self._player_name = self._player_name[:-1]
            elif 32 <= key <= 126 and len(self._player_name) < 12:
                self._player_name += chr(key)

        elif self.state == 'GAME_OVER':
            if key == ord(' '):
                self.state = 'RANKING'
            elif key == ord('r'):
                self._reset()

        elif self.state == 'RANKING':
            if key in (ord(' '), ord('r')):
                self._reset()

    # ----------------------------------------------------------------- private

    def _begin_countdown(self):
        self._countdown_start = time.time()
        self.state = 'COUNTDOWN'

    def _launch_game(self):
        cls = SEQUENCE[self.game_idx]
        self.game = cls()
        self.game.start()
        self._game_start_score = self.score.total_score
        self.state = 'PLAYING'

    def _reset(self):
        self.state = 'MENU'
        self.game_idx = 0
        self.game = None
        self._player_name = ''
        self.score.reset()

    # ------------------------------------------------------------------ states

    def _menu(self, frame):
        h, w = frame.shape[:2]
        dim(frame, 0.5)

        draw_text_centered(frame, 'Vision Cooking Challenge',
                           h // 5, scale=1.7, color=COLOR_PRIMARY, thickness=3)
        draw_text_centered(frame, 'Webcam Cooking Mama',
                           h // 5 + 65, scale=0.9, color=COLOR_WHITE)

        lines = [
            '1. Cutting Game   -  move hand LEFT <-> RIGHT',
            '2. Stirring Game  -  move hand in CIRCLES',
            '3. Flipping Game  -  move hand UP quickly',
        ]
        for i, line in enumerate(lines):
            draw_text_centered(frame, line, h // 2 + i * 50, scale=0.75, color=COLOR_GREY)

        if int(time.time() * 2) % 2 == 0:
            draw_text_centered(frame, 'Press SPACE to start!',
                               h * 4 // 5, scale=1.2, color=COLOR_SUCCESS, thickness=2)
        return frame

    def _countdown(self, frame):
        h, w = frame.shape[:2]
        elapsed = time.time() - self._countdown_start
        dim(frame, 0.5)

        if self.game_idx < len(SEQUENCE):
            cls = SEQUENCE[self.game_idx]
            draw_text_centered(frame, cls.name,        h // 4,      scale=1.8, color=COLOR_PRIMARY, thickness=3)
            draw_text_centered(frame, cls.instruction, h // 4 + 70, scale=0.85, color=COLOR_WHITE)

        remaining = 3 - int(elapsed)
        if remaining > 0:
            draw_text_centered(frame, str(remaining), h // 2 + 40,
                               scale=6.0, color=(0, 255, 255), thickness=10)
        else:
            draw_text_centered(frame, 'GO!', h // 2 + 40,
                               scale=6.0, color=COLOR_SUCCESS, thickness=10)
            if elapsed >= 4.0:
                self._launch_game()
        return frame

    def _playing(self, frame):
        events = self.game.update(self.hand_pos)

        for ev in events:
            self.score.add_score(POINTS.get(ev, 10))

        frame = self.game.draw(frame, self.hand_pos)
        self._hud(frame)

        if self.game.check_done():
            self._last_success = self.game.succeeded
            if self._last_success:
                base   = BONUS.get(type(self.game), 80)
                time_b = int(self.game.time_remaining * 5)
                self.score.add_bonus(base + time_b)
            self._last_game_score = self.score.total_score - self._game_start_score
            self.score.record_game(self.game.name, self._last_game_score)
            self.game_idx += 1
            self._result_start = time.time()
            self.state = 'RESULT'
        return frame

    def _result(self, frame):
        h, w = frame.shape[:2]
        dim(frame, 0.55)
        elapsed = time.time() - self._result_start

        label = 'SUCCESS!' if self._last_success else 'TIME UP!'
        color = COLOR_SUCCESS if self._last_success else COLOR_DANGER
        draw_text_centered(frame, label,                       h // 3,      scale=3.0, color=color,        thickness=5)
        draw_text_centered(frame, f'+{self._last_game_score}', h // 2,      scale=2.0, color=COLOR_PRIMARY, thickness=3)
        draw_text_centered(frame, f'Total: {self.score.total_score}', h // 2 + 70, scale=1.1, color=COLOR_WHITE)

        if elapsed > 3.0:
            if self.game_idx >= len(SEQUENCE):
                self.state = 'NAME_INPUT'
            else:
                self._begin_countdown()
        return frame

    def _name_input(self, frame):
        h, w = frame.shape[:2]
        dim(frame, 0.7)

        draw_text_centered(frame, 'All Clear!',                   h // 5,      scale=2.5, color=COLOR_PRIMARY, thickness=4)
        draw_text_centered(frame, f'Final Score: {self.score.total_score}', h // 3, scale=1.6, color=COLOR_WHITE, thickness=2)
        draw_text_centered(frame, 'Enter your name:',             h // 2 - 20, scale=1.0, color=COLOR_GREY)

        bw, bh = 420, 62
        bx, by = (w - bw) // 2, h // 2 + 20
        draw_panel(frame, bx, by, bw, bh, alpha=0.7, color=(20, 20, 20))
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), COLOR_PRIMARY, 2)
        cursor = '_' if int(time.time() * 2) % 2 == 0 else ' '
        cv2.putText(frame, self._player_name + cursor, (bx + 14, by + 44),
                    FONT, 1.3, COLOR_WHITE, 2)

        draw_text_centered(frame, 'Press Enter to save', h * 4 // 5, scale=0.9, color=COLOR_GREY)
        return frame

    def _game_over(self, frame):
        h, w = frame.shape[:2]
        dim(frame, 0.7)

        draw_text_centered(frame, 'GAME OVER',
                           h // 6, scale=2.8, color=COLOR_PRIMARY, thickness=4)
        draw_text_centered(frame, f'Final Score: {self.score.total_score}',
                           h // 3, scale=1.8, color=COLOR_WHITE, thickness=3)

        for i, gs in enumerate(self.score.game_scores):
            draw_text_centered(frame, f"{gs['game']}:  +{gs['score']}",
                               h // 2 + i * 50, scale=0.9, color=COLOR_GREY)

        draw_text_centered(frame, f'Grade:  {_grade(self.score.total_score)}',
                           h * 3 // 4, scale=1.6, color=COLOR_SUCCESS, thickness=2)
        draw_text_centered(frame, 'SPACE: Ranking     R: Retry',
                           h * 5 // 6, scale=0.9, color=COLOR_GREY)
        return frame

    def _ranking(self, frame):
        h, w = frame.shape[:2]
        dim(frame, 0.8)

        draw_text_centered(frame, 'RANKING', 70, scale=2.2, color=COLOR_PRIMARY, thickness=3)

        rank_colors = [COLOR_PRIMARY, (180, 180, 220), (0, 165, 210)]
        for i, entry in enumerate(self.score.rankings[:8]):
            color = rank_colors[i] if i < 3 else COLOR_WHITE
            text  = f"  {i+1}.  {entry['name']:<12}  {entry['score']:>6}    {entry['date']}"
            draw_text_centered(frame, text, 145 + i * 58, scale=0.85, color=color)

        draw_text_centered(frame, 'SPACE / R: Play again', h - 55, scale=1.0, color=COLOR_GREY)
        return frame

    def _hud(self, frame):
        h, w = frame.shape[:2]
        draw_panel(frame, 0, 0, w, 75)

        draw_text(frame, self.game.name, (18, 50), scale=1.1, color=COLOR_PRIMARY, thickness=2)

        t = self.game.time_remaining
        t_str = f'TIME  {int(t) + 1:02d}'
        sz = cv2.getTextSize(t_str, FONT, 1.1, 2)[0]
        draw_text(frame, t_str, (w - sz[0] - 18, 50), scale=1.1,
                  color=COLOR_DANGER if t < 5 else COLOR_WHITE, thickness=2)

        s_str = f'Score: {self.score.total_score}'
        ssz = cv2.getTextSize(s_str, FONT, 0.85, 2)[0]
        draw_text(frame, s_str, ((w - ssz[0]) // 2, 50), scale=0.85, color=COLOR_WHITE)

        # Time bar
        draw_progress_bar(frame, 15, h - 28, w - 30, 14, self.game.time_ratio,
                          color=COLOR_DANGER if t < 5 else COLOR_SUCCESS)

        # Action progress
        pt = self.game.progress_text
        if pt:
            draw_text(frame, pt, (18, 110), scale=0.9, color=COLOR_WHITE)
