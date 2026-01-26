import cv2
import mediapipe as mp
import math

# ==========================================
# 🏃 模块 1: 全身控制 (BodyController)
# ==========================================
class BodyController:
    def __init__(self, detection_confidence=0.7):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.current_action = "NEUTRAL"

    def process(self, frame, draw=False):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        action = "NEUTRAL"
        body_data = None

        # 阈值设定
        JUMP_THRESH = 0.3  # 肩膀高于画面 30% 处算跳
        DUCK_THRESH = 0.7  # 肩膀低于画面 70% 处算蹲
        LEFT_THRESH = 0.4  # 髋部偏左
        RIGHT_THRESH = 0.6 # 髋部偏右

        if results.pose_landmarks:
            if draw:
                self.mp_draw.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            landmarks = results.pose_landmarks.landmark

            # 获取关键点
            left_shoulder_y = landmarks[11].y
            right_shoulder_y = landmarks[12].y
            center_shoulder_y = (left_shoulder_y + right_shoulder_y) / 2

            left_hip_x = landmarks[23].x
            right_hip_x = landmarks[24].x
            center_hip_x = (left_hip_x + right_hip_x) / 2

            body_data = (int(center_hip_x * frame.shape[1]), int(center_shoulder_y * frame.shape[0]))

            # 判定逻辑
            if center_shoulder_y < JUMP_THRESH:
                action = "JUMP"
            elif center_shoulder_y > DUCK_THRESH:
                action = "DUCK"
            elif center_hip_x < LEFT_THRESH:
                action = "LEFT"
            elif center_hip_x > RIGHT_THRESH:
                action = "RIGHT"
            else:
                action = "NEUTRAL"

        return action, frame, body_data


# ==========================================
# 🖐 模块 2: 手势控制 (HandController)
# ==========================================
class HandController:
    def __init__(self, detection_confidence=0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
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
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)

        h, w, _ = frame.shape
        action = "NEUTRAL"
        landmark_data = None 

        # 定义中心安全区
        x_min, x_max = 0.3, 0.7
        y_min, y_max = 0.3, 0.7

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