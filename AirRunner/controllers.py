import cv2
import mediapipe as mp
import math

# ==========================================
# 模块 1: 全身控制 (BodyController)
# ==========================================
class BodyController:
    def __init__(self, detection_confidence=0.7):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            model_complexity=0,
            smooth_landmarks=False,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.current_action = "NEUTRAL"

    def process(self, frame, draw=False):
        frame.flags.writeable = False
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        frame.flags.writeable = True

        action = "NEUTRAL"
        body_data = None

        # 阈值设定 (上下更敏感，左右保持 0.4 ~ 0.6)
        JUMP_THRESH = 0.46  # 鼻尖高于画面 45% 处算跳
        DUCK_THRESH = 0.56  # 鼻尖低于画面 53% 处算蹲
        LEFT_THRESH = 0.45   # 鼻尖偏左
        RIGHT_THRESH = 0.55  # 鼻尖偏右

        if results.pose_landmarks:
            if draw:
                self.mp_draw.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            landmarks = results.pose_landmarks.landmark

            # 获取关键点
            # 使用鼻尖作为控制点 (0: nose)
            nose_x = landmarks[0].x
            nose_y = landmarks[0].y

            body_data = (int(nose_x * frame.shape[1]), int(nose_y * frame.shape[0]))

            # 判定逻辑
            if nose_y < JUMP_THRESH:
                action = "JUMP"
            elif nose_y > DUCK_THRESH:
                action = "DUCK"
            elif nose_x < LEFT_THRESH:
                action = "LEFT"
            elif nose_x > RIGHT_THRESH:
                action = "RIGHT"
            else:
                action = "NEUTRAL"

        return action, frame, body_data


# ==========================================
# 模块 2: 手势控制 (HandController)
# ==========================================
class HandController:
    def __init__(self, detection_confidence=0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            model_complexity=0,
            max_num_hands=1,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.current_action = "NEUTRAL"

    def is_fist(self, landmarks):
        """ 简单的握拳检测 """
        tips = [8, 12, 16]
        pips = [6, 10, 14]
        folded_fingers = 0
        for tip, pip in zip(tips, pips):
            if landmarks[tip].y > landmarks[pip].y: 
                folded_fingers += 1
        return folded_fingers >= 3

    def process(self, frame, draw=False):
        frame.flags.writeable = False
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        frame.flags.writeable = True

        h, w, _ = frame.shape
        action = "NEUTRAL"
        landmark_data = None 

        # 定义中心安全区
        x_min, x_max = 0.4, 0.6
        y_min, y_max = 0.4, 0.6

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(frame, hand_lms, self.mp_hands.HAND_CONNECTIONS)

                # 获取中指根部作为核心控制点
                lm = hand_lms.landmark[9]
                cx, cy = lm.x, lm.y
                landmark_data = (int(cx * w), int(cy * h)) # 转回像素坐标

                # 1. 优先检测握拳 (暂停)
                if self.is_fist(hand_lms.landmark):
                    action = "PAUSE"
                else:
                    # 2. 坐标判定逻辑
                    if cy < y_min: action = "JUMP"
                    elif cy > y_max: action = "DUCK"
                    elif cx < x_min: action = "LEFT"
                    elif cx > x_max: action = "RIGHT"
                    else: action = "NEUTRAL"

        self.current_action = action
        return action, frame, landmark_data
