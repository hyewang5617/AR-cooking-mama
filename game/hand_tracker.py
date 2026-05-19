import cv2
import mediapipe as mp


class HandTracker:
    def __init__(self):
        mp_hands = mp.solutions.hands
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )
        self.mp_hands = mp_hands
        mp_draw = mp.solutions.drawing_utils
        self._lm_spec = mp_draw.DrawingSpec(color=(0, 230, 120), thickness=2, circle_radius=4)
        self._cn_spec = mp_draw.DrawingSpec(color=(255, 200, 0), thickness=2)
        self._draw = mp_draw

    def process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True
        return results

    def get_position(self, results, frame_shape, landmark_id=8):
        if not results.multi_hand_landmarks:
            return None
        h, w = frame_shape[:2]
        lm = results.multi_hand_landmarks[0].landmark[landmark_id]
        return (int(lm.x * w), int(lm.y * h))

    def draw(self, frame, results):
        if results.multi_hand_landmarks:
            for hand_lm in results.multi_hand_landmarks:
                self._draw.draw_landmarks(
                    frame, hand_lm, self.mp_hands.HAND_CONNECTIONS,
                    self._lm_spec, self._cn_spec,
                )
        return frame
