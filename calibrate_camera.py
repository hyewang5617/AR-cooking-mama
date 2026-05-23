"""
calibrate_camera.py
─────────────────────────────────────────────────────────
Camera Calibration: 체스보드로 카메라 내부 파라미터 K와 왜곡 계수를 계산.

실행 방법:
  python calibrate_camera.py
  - 체스보드를 웹캠 앞에서 다양한 각도로 보여주기
  - SPACE: 코너 감지되면 캡처 (최소 10장 권장)
  - Q / ESC: 캘리브레이션 실행 후 종료

출력:
  camera_params.json  ← hand_tracking_sender.py가 자동으로 읽음

────────────────────────────────────────────────
핵심 개념:
  Camera Matrix K = [[fx, 0,  cx],
                     [0,  fy, cy],
                     [0,  0,  1 ]]
  - fx, fy : 초점거리 (픽셀 단위)
  - cx, cy : 주점 (이미지 중심)

  Pinhole 투영:
    [u]   [fx  0  cx] [X/Z]
    [v] = [0  fy  cy] [Y/Z]
    [1]   [0   0   1] [ 1 ]

  Reprojection Error (RMSE):
    3D → 2D 역투영 시 실제 코너와의 평균 픽셀 오차
    낮을수록 K가 정확함 (1.0 이하면 양호)
────────────────────────────────────────────────
"""

import cv2
import numpy as np
import json
import os

CHESSBOARD   = (9, 6)      # 체스보드 내부 코너 수 (가로, 세로)
SQUARE_SIZE  = 0.025       # 체스보드 한 칸 실제 크기 (미터, 2.5cm)
OUTPUT_FILE  = "camera_params.json"


def main():
    # ── 3D 기준점 생성 (체스보드 평면, Z=0) ──
    # 동차좌표로 쓸 수 있게 (N, 3) 형태로 준비
    objp = np.zeros((CHESSBOARD[0] * CHESSBOARD[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:CHESSBOARD[0], 0:CHESSBOARD[1]].T.reshape(-1, 2)
    objp *= SQUARE_SIZE

    obj_points = []   # 실세계 3D 코너 좌표
    img_points = []   # 이미지 2D 코너 좌표
    image_size = None

    cap = None
    for idx in range(3):
        c = cv2.VideoCapture(idx)
        if c.isOpened():
            ret, _ = c.read()
            if ret:
                cap = c
                break
            c.release()
    if cap is None:
        print("Error: 카메라를 찾을 수 없습니다.")
        return

    count = 0
    print("체스보드를 카메라 앞에서 다양한 각도/거리로 보여주세요.")
    print("SPACE: 캡처  |  Q/ESC: 캘리브레이션 실행")

    cv2.namedWindow("Calibration", cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        image_size = gray.shape[::-1]  # (width, height)

        # 체스보드 코너 탐색
        found, corners = cv2.findChessboardCorners(gray, CHESSBOARD, None)

        display = frame.copy()
        if found:
            # 서브픽셀 정밀도로 코너 보정
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            cv2.drawChessboardCorners(display, CHESSBOARD, corners2, found)
            cv2.putText(display, f"Found! [{count} saved]  SPACE to capture",
                        (20, 45), cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 255, 80), 2)
        else:
            cv2.putText(display, f"Searching...  [{count} saved]",
                        (20, 45), cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 80, 255), 2)

        cv2.imshow("Calibration", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(' ') and found:
            obj_points.append(objp)
            img_points.append(corners2)
            count += 1
            print(f"  [{count}] 캡처 완료")
        elif key in (ord('q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()

    if count < 5:
        print(f"이미지가 부족합니다 ({count}장). 최소 5장 필요.")
        return

    # ── Camera Calibration ──────────────────────────────────
    print(f"\n{count}장으로 캘리브레이션 중...")
    rmse, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, image_size, None, None)

    print(f"\n▶ RMSE (재투영 오차): {rmse:.4f} px  ({'양호' if rmse < 1.0 else '높음 - 더 많은 이미지 권장'})")
    print(f"\n▶ Camera Matrix K:\n{K}")
    print(f"   fx={K[0,0]:.1f}  fy={K[1,1]:.1f}  cx={K[0,2]:.1f}  cy={K[1,2]:.1f}")
    print(f"\n▶ Distortion Coefficients (k1,k2,p1,p2,k3):\n   {dist.ravel()}")

    # ── JSON 저장 ────────────────────────────────────────────
    data = {
        "K":          K.tolist(),
        "dist":       dist.tolist(),
        "rmse":       round(rmse, 6),
        "image_size": list(image_size),
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ '{OUTPUT_FILE}' 저장 완료")
    print("  hand_tracking_sender.py 실행 시 자동으로 읽힙니다.")


if __name__ == "__main__":
    main()
