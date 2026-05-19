import cv2
import sys
from game.game_manager import GameManager


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open webcam.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    game = GameManager()
    cv2.namedWindow('Vision Cooking Challenge', cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot read frame.")
            break

        frame = cv2.flip(frame, 1)
        output = game.update(frame)
        cv2.imshow('Vision Cooking Challenge', output)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key != 0xFF:
            game.handle_key(key)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
