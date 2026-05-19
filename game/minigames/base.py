import time


class BaseMiniGame:
    name = 'Mini Game'
    instruction = 'Follow the instructions!'
    duration = 15.0

    def __init__(self):
        self._start_time = None
        self._complete = False

    def start(self):
        self._start_time = time.time()

    @property
    def time_remaining(self):
        if self._start_time is None:
            return self.duration
        return max(0.0, self.duration - (time.time() - self._start_time))

    @property
    def time_ratio(self):
        return self.time_remaining / self.duration

    @property
    def succeeded(self):
        return False

    @property
    def progress_text(self):
        return ''

    def check_done(self):
        if self._complete or self.time_remaining <= 0:
            self._complete = True
            return True
        return False

    def update(self, hand_pos):
        raise NotImplementedError

    def draw(self, frame, hand_pos):
        raise NotImplementedError
