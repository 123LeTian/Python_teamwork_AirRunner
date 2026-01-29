import cv2
import mediapipe as mp


class BaseController:
    """ 控制器基类，用于统一管理阈值 """

    def __init__(self, settings=None):
        # 默认设置
        self.settings = {
            "jump_thresh": 0.4,
            "duck_thresh": 0.6,
            "left_thresh": 0.4,
            "right_thresh": 0.6
        }
        if settings:
            self.settings.update(settings)

    def get_thresholds(self):
        return {
            "jump": self.settings["jump_thresh"],
            "duck": self.settings["duck_thresh"],
            "left": self.settings["left_thresh"],
            "right": self.settings["right_thresh"]
        }


class BodyController(BaseController):
    def __init__(self, detection_confidence=0.7, settings=None):
        super().__init__(settings)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            model_complexity=0,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=0.5
        )

    def process(self, frame):
        frame.flags.writeable = False
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        frame.flags.writeable = True

        action = "NEUTRAL"
        body_data = None

        # 读取设置
        s = self.settings

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            # 鼻尖控制
            nose = landmarks[0]
            x, y = nose.x, nose.y
            body_data = (int(x * frame.shape[1]), int(y * frame.shape[0]))

            if y < s["jump_thresh"]:
                action = "JUMP"
            elif y > s["duck_thresh"]:
                action = "DUCK"
            elif x < s["left_thresh"]:
                action = "LEFT"
            elif x > s["right_thresh"]:
                action = "RIGHT"

        return action, body_data


class HandController(BaseController):
    def __init__(self, detection_confidence=0.7, settings=None):
        super().__init__(settings)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            model_complexity=0,
            max_num_hands=1,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=0.5
        )

    def process(self, frame):
        frame.flags.writeable = False
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        frame.flags.writeable = True

        action = "NEUTRAL"
        hand_data = None
        s = self.settings
        h, w, _ = frame.shape

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                # 握拳检测
                tips = [8, 12, 16]
                pips = [6, 10, 14]
                folded = sum([1 for t, p in zip(tips, pips) if hand_lms.landmark[t].y > hand_lms.landmark[p].y])

                # 中指根部坐标
                lm = hand_lms.landmark[9]
                cx, cy = lm.x, lm.y
                hand_data = (int(cx * w), int(cy * h))

                if folded >= 3:
                    action = "PAUSE"
                else:
                    if cy < s["jump_thresh"]:
                        action = "JUMP"
                    elif cy > s["duck_thresh"]:
                        action = "DUCK"
                    elif cx < s["left_thresh"]:
                        action = "LEFT"
                    elif cx > s["right_thresh"]:
                        action = "RIGHT"

        return action, hand_data