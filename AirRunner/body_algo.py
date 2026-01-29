import cv2
import mediapipe as mp

#测试文件，不参与主循环
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
        RIGHT_THRESH = 0.6  # 髋部偏右

        if results.pose_landmarks:
            if draw:
                self.mp_draw.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            landmarks = results.pose_landmarks.landmark

            # 获取关键点
            # 11: 左肩, 12: 右肩 -> 计算肩膀中心 Y
            left_shoulder_y = landmarks[11].y
            right_shoulder_y = landmarks[12].y
            center_shoulder_y = (left_shoulder_y + right_shoulder_y) / 2

            # 23: 左髋, 24: 右髋 -> 计算髋部中心 X
            left_hip_x = landmarks[23].x
            right_hip_x = landmarks[24].x
            center_hip_x = (left_hip_x + right_hip_x) / 2

            body_data = (center_hip_x, center_shoulder_y)

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


# --- 本地测试代码 ---
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    handler = BodyController()
    window_name = "Body Mode Test"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    while True:
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        act, img, _ = handler.process(frame, draw=True)

        cv2.putText(img, f"Action: {act}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # 画出阈值线供调试
        h, w, _ = frame.shape
        cv2.line(img, (0, int(h * 0.3)), (w, int(h * 0.3)), (0, 255, 255), 2)  # Jump Line
        cv2.line(img, (0, int(h * 0.7)), (w, int(h * 0.7)), (0, 255, 255), 2)  # Duck Line

        cv2.imshow(window_name, img)
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break
        if cv2.waitKey(1) & 0xFF == 27: break
    cap.release()
    cv2.destroyAllWindows()
