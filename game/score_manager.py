import json
import os
from datetime import datetime

RANKING_FILE = 'rankings.json'


class ScoreManager:
    def __init__(self):
        self.total_score = 0
        self.combo = 0
        self.max_combo = 0
        self.game_scores = []
        self.rankings = self._load()

    def add_score(self, base_points):
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        multiplier = min(1.0 + (self.combo // 4) * 0.25, 2.5)
        earned = int(base_points * multiplier)
        self.total_score += earned
        return earned

    def add_bonus(self, points):
        self.total_score += points

    def record_game(self, name, score):
        self.game_scores.append({'game': name, 'score': score})

    def save(self, player_name):
        entry = {
            'name': player_name,
            'score': self.total_score,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        self.rankings.append(entry)
        self.rankings.sort(key=lambda e: e['score'], reverse=True)
        self.rankings = self.rankings[:10]
        with open(RANKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.rankings, f, ensure_ascii=False, indent=2)

    def reset(self):
        self.total_score = 0
        self.combo = 0
        self.max_combo = 0
        self.game_scores = []
        self.rankings = self._load()

    def _load(self):
        if os.path.exists(RANKING_FILE):
            try:
                with open(RANKING_FILE, encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []
