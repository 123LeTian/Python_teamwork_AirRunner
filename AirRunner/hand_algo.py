import cv2
import mediapipe as mp
import math

#测试文件，不参与主循环
class HandController:
    def __init__(self, detection_confidence=0.7):
        # 初始化 MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

        # 状态记录
        self.current_action = "NEUTRAL"

    def is_fist(self, landmarks):
        """
        简单的握拳检测：如果食指、中指、无名指的指尖(Tip)都在指关节(Pip)下方(Y坐标更大)，视为握拳
        注意：OpenCV坐标系中，Y轴向下增加
        """
        # 指尖: 8, 12, 16; 指关节: 6, 10, 14
        tips = [8, 12, 16]
        pips = [6, 10, 14]

        folded_fingers = 0
        for tip, pip in zip(tips, pips):
            if landmarks[tip].y > landmarks[pip].y:  # 指尖在关节下面
                folded_fingers += 1

        return folded_fingers >= 3  # 3根手指弯曲算握拳

    def process(self, frame, draw=False):
        """
        输入视频帧，返回动作指令和处理后的图像
        指令集: JUMP, DUCK, LEFT, RIGHT, PAUSE, NEUTRAL
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)

        h, w, _ = frame.shape
        action = "NEUTRAL"
        landmark_data = None  # 传给UI绘制用

        # 定义中心安全区 (屏幕中间的 30% - 70% 区域)
        x_min, x_max = 0.3, 0.7
        y_min, y_max = 0.3, 0.7

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(frame, hand_lms, self.mp_hands.HAND_CONNECTIONS)

                # 获取关键点：我们用手腕(0)或中指根部(9)作为控制核心，这里用中指根部更稳定
                cx, cy = hand_lms.landmark[9].x, hand_lms.landmark[9].y
                landmark_data = (cx, cy)  # 归一化坐标

                # 1. 优先检测握拳 (暂停)
                if self.is_fist(hand_lms.landmark):
                    action = "PAUSE"
                else:
                    # 2. 坐标判定逻辑 (虚拟摇杆)
                    if cy < y_min:
                        action = "JUMP"  # 手向上移
                    elif cy > y_max:
                        action = "DUCK"  # 手向下移 (滑铲)
                    elif cx < x_min:
                        action = "LEFT"  # 镜像后，手向画面左边移
                    elif cx > x_max:
                        action = "RIGHT"  # 镜像后，手向画面右边移
                    else:
                        action = "NEUTRAL"

        self.current_action = action
        return action, frame, landmark_data


# --- 本地测试代码 (仅 Member A 自测用) ---
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    handler = HandController()
    while True:
        ret, frame = cap.read()
        if not ret: break

        # 镜像翻转，符合游戏直觉
        frame = cv2.flip(frame, 1)

        act, img, _ = handler.process(frame, draw=True)

        # 简单的测试UI
        cv2.putText(img, f"Action: {act}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # 画出安全区框供调试
        h, w, _ = frame.shape
        cv2.rectangle(img, (int(w * 0.3), int(h * 0.3)), (int(w * 0.7), int(h * 0.7)), (255, 0, 0), 2)

        cv2.imshow("Hand Mode Test", img)
        if cv2.waitKey(1) & 0xFF == 27: break
    cap.release()
    cv2.destroyAllWindows()