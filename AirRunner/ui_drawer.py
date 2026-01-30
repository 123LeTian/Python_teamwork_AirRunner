import cv2
import numpy as np
import time


class CyberHUD:
    def __init__(self):
        # 配色方案
        self.C_BG_HEADER = (249, 192, 78)
        self.C_ACCENT = (7, 193, 255)
        self.C_OK = (54, 194, 91)
        self.C_WARN = (82, 82, 255)
        self.C_TEXT_MAIN = (255, 255, 255)
        self.C_TEXT_DARK = (82, 72, 61)
        self.C_GUIDE = (230, 230, 230)

        self.prev_time = time.time()
        self.fps = 0

    def draw_warning(self, frame, message):
        h, w, _ = frame.shape
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        self._draw_text_with_outline(frame, "WARNING", (w // 2 - 100, h // 2 - 20), 1.5, self.C_WARN, 3,
                                     (255, 255, 255))
        self._draw_text_with_outline(frame, message, (w // 2 - 150, h // 2 + 30), 1.0, (255, 255, 255), 2)
        return frame

    # 自动暂停界面
    def draw_auto_pause(self, frame):
        h, w, _ = frame.shape
        # 变暗背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        cx, cy = w // 2, h // 2
        # 绘制暂停图标
        cv2.rectangle(frame, (cx - 40, cy - 50), (cx - 15, cy + 50), self.C_ACCENT, -1)
        cv2.rectangle(frame, (cx + 15, cy - 50), (cx + 40, cy + 50), self.C_ACCENT, -1)

        self._draw_text_with_outline(frame, "AUTO PAUSED", (cx - 140, cy + 100), 1.2, self.C_TEXT_MAIN, 2)
        self._draw_text_with_outline(frame, "User Not Detected", (cx - 110, cy + 140), 0.7, self.C_GUIDE, 1)
        return frame

    def draw_interface(self, frame, action, hand_pos, thresholds, countdown=0):
        curr_time = time.time()
        self.fps = 1 / (curr_time - self.prev_time + 1e-5)
        self.prev_time = curr_time

        self._draw_guidelines(frame, thresholds, action)

        if action != "NEUTRAL":
            self._draw_action_feedback(frame, action)

        if hand_pos:
            cx, cy = hand_pos
            color = self.C_WARN if action != "NEUTRAL" else self.C_ACCENT
            cv2.circle(frame, (cx, cy), 18, self.C_TEXT_DARK, 4)
            cv2.circle(frame, (cx, cy), 15, color, -1)
            cv2.line(frame, (cx - 22, cy), (cx + 22, cy), self.C_TEXT_MAIN, 2)
            cv2.line(frame, (cx, cy - 22), (cx, cy + 22), self.C_TEXT_MAIN, 2)

        self._draw_status_bar(frame, action)

        if countdown > 0:
            self._draw_countdown(frame, countdown)

        return frame

    def _draw_action_feedback(self, img, action):
        h, w, _ = img.shape
        thickness = 15

        if action == "JUMP":
            cv2.rectangle(img, (0, 0), (w, thickness), self.C_OK, -1)
        elif action == "DUCK":
            cv2.rectangle(img, (0, h - thickness), (w, h), self.C_ACCENT, -1)
        elif action == "LEFT":
            cv2.rectangle(img, (0, 0), (thickness, h), self.C_OK, -1)
        elif action == "RIGHT":
            cv2.rectangle(img, (w - thickness, 0), (w, h), self.C_OK, -1)
        elif action == "PAUSE":
            cv2.rectangle(img, (0, 0), (w, h), self.C_WARN, thickness)

    def _draw_text_with_outline(self, img, text, pos, scale, color, thickness=2, outline_color=None):
        if outline_color is None:
            outline_color = self.C_TEXT_DARK
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, text, pos, font, scale, outline_color, thickness + 3)
        cv2.putText(img, text, pos, font, scale, color, thickness)

    def _draw_guidelines(self, img, thresh, action):
        h, w, _ = img.shape
        y_jump = int(thresh['jump'] * h)
        y_duck = int(thresh['duck'] * h)
        x_left = int(thresh['left'] * w)
        x_right = int(thresh['right'] * w)

        overlay = img.copy()
        cv2.rectangle(overlay, (x_left, y_jump), (x_right, y_duck), (255, 255, 255), -1)
        cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)

        c = self.C_WARN if action == "JUMP" else self.C_GUIDE
        t = 4 if action == "JUMP" else 2
        cv2.line(img, (0, y_jump), (w, y_jump), c, t)

        c = self.C_WARN if action == "DUCK" else self.C_GUIDE
        t = 4 if action == "DUCK" else 2
        cv2.line(img, (0, y_duck), (w, y_duck), c, t)

        color_lr = self.C_WARN if action in ["LEFT", "RIGHT"] else self.C_GUIDE
        cv2.line(img, (x_left, 0), (x_left, h), color_lr, 2)
        cv2.line(img, (x_right, 0), (x_right, h), color_lr, 2)

    def _draw_status_bar(self, img, action):
        h, w, _ = img.shape
        header_h = 60
        cv2.rectangle(img, (0, 0), (w, header_h), self.C_BG_HEADER, -1)
        cv2.line(img, (0, header_h), (w, header_h), (255, 255, 255), 3)

        self._draw_text_with_outline(img, "AIR RUNNER", (20, 42), 1.0, self.C_ACCENT, 2)

        (logo_w, _), _ = cv2.getTextSize("AIR RUNNER", cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        hint_x = 20 + logo_w + 15
        cv2.putText(img, "[ESC to EXIT]", (hint_x, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.C_TEXT_MAIN, 1)

        if action != "NEUTRAL":
            text = action
            font_scale = 1.2
            thickness = 3
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            cx = (w - tw) // 2
            pad_x, pad_y = 20, 10
            cv2.rectangle(img, (cx - pad_x, 15), (cx + tw + pad_x, 15 + th + pad_y + 10), self.C_OK, -1)
            self._draw_text_with_outline(img, text, (cx, 52), font_scale, self.C_TEXT_MAIN, thickness)

        fps_text = f"FPS: {int(self.fps)}"
        self._draw_text_with_outline(img, fps_text, (w - 130, 42), 0.6, self.C_OK, 2)

    def _draw_countdown(self, img, num):
        h, w, _ = img.shape
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (255, 255, 255), -1)
        cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)

        text = str(int(num) + 1)
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale, thick = 6, 15
        size = cv2.getTextSize(text, font, scale, thick)[0]
        cx, cy = (w - size[0]) // 2, (h + size[1]) // 2 - 20
        self._draw_text_with_outline(img, text, (cx, cy), scale, self.C_ACCENT, 5)

        sub_text = "GET READY!"
        sub_scale, sub_thick = 1.5, 3
        sub_size = cv2.getTextSize(sub_text, font, sub_scale, sub_thick)[0]
        sub_x = (w - sub_size[0]) // 2
        self._draw_text_with_outline(img, sub_text, (sub_x, cy + 80), sub_scale, self.C_WARN, sub_thick)