import cv2
import numpy as np
import time


class CyberHUD:
    def __init__(self):
        # --- 🎨 卡通街机配色 ---
        # 对应 main.py 的配色方案
        self.C_BG_HEADER = (249, 192, 78)  # 天空蓝 (Sky Blue)
        self.C_ACCENT = (7, 193, 255)  # 活力黄 (Yellow)
        self.C_OK = (54, 194, 91)  # 游戏绿 (Green)
        self.C_WARN = (82, 82, 255)  # 警告红/橙 (Red)
        self.C_TEXT_MAIN = (255, 255, 255)  # 纯白文字 (White)
        self.C_TEXT_DARK = (82, 72, 61)  # 深色描边 (Dark Gray)
        self.C_GUIDE = (230, 230, 230)  # 辅助线浅白

        self.prev_time = time.time()
        self.fps = 0

    def draw_interface(self, frame, action, hand_pos, thresholds, countdown=0):
        """
        主绘制函数
        """
        # 1. 计算 FPS
        curr_time = time.time()
        self.fps = 1 / (curr_time - self.prev_time + 1e-5)
        self.prev_time = curr_time

        # 2. 绘制阈值辅助线 
        self._draw_guidelines(frame, thresholds, action)

        # 3. 绘制手部/头部光标 
        if hand_pos:
            cx, cy = hand_pos
            # 触发动作时变红，平时是黄色
            color = self.C_WARN if action != "NEUTRAL" else self.C_ACCENT

            # 外圈描边 
            cv2.circle(frame, (cx, cy), 18, self.C_TEXT_DARK, 4)
            # 内圈填充
            cv2.circle(frame, (cx, cy), 15, color, -1)
            # 十字准心
            cv2.line(frame, (cx - 22, cy), (cx + 22, cy), self.C_TEXT_MAIN, 2)
            cv2.line(frame, (cx, cy - 22), (cx, cy + 22), self.C_TEXT_MAIN, 2)

        # 4. 绘制顶部状态栏 
        self._draw_status_bar(frame, action)

        # 5. 倒计时遮罩 
        if countdown > 0:
            self._draw_countdown(frame, countdown)

        return frame

    def _draw_text_with_outline(self, img, text, pos, scale, color, thickness=2, outline_color=None):
        """
        辅助函数：绘制带描边的文字 
        """
        if outline_color is None:
            outline_color = self.C_TEXT_DARK

        font = cv2.FONT_HERSHEY_SIMPLEX
        # 1. 先画深色描边 (粗线条)
        cv2.putText(img, text, pos, font, scale, outline_color, thickness + 3)
        # 2. 再画内部颜色 (细线条)
        cv2.putText(img, text, pos, font, scale, color, thickness)

    def _draw_guidelines(self, img, thresh, action):
        h, w, _ = img.shape

        # 解析阈值坐标
        y_jump = int(thresh['jump'] * h)
        y_duck = int(thresh['duck'] * h)
        x_left = int(thresh['left'] * w)
        x_right = int(thresh['right'] * w)

        # --- A. 绘制中心安全区 ---
        overlay = img.copy()
        # 在安全区位置画白色矩形
        cv2.rectangle(overlay, (x_left, y_jump), (x_right, y_duck), (255, 255, 255), -1)
        # 混合图层，产生透明感
        cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)

        # --- B. 绘制触发线 ---
        # JUMP 线 (上方)
        c = self.C_WARN if action == "JUMP" else self.C_GUIDE
        t = 4 if action == "JUMP" else 2
        cv2.line(img, (0, y_jump), (w, y_jump), c, t)
        if action == "JUMP":
            self._draw_text_with_outline(img, "JUMP!", (10, y_jump - 10), 0.8, self.C_ACCENT)

        # DUCK 线 (下方)
        c = self.C_WARN if action == "DUCK" else self.C_GUIDE
        t = 4 if action == "DUCK" else 2
        cv2.line(img, (0, y_duck), (w, y_duck), c, t)
        if action == "DUCK":
            self._draw_text_with_outline(img, "DUCK!", (10, y_duck + 25), 0.8, self.C_ACCENT)

        # 左右边界线
        cv2.line(img, (x_left, 0), (x_left, h), self.C_GUIDE, 2)
        cv2.line(img, (x_right, 0), (x_right, h), self.C_GUIDE, 2)

    def _draw_status_bar(self, img, action):
        h, w, _ = img.shape
        header_h = 60

        # 1. 顶部背景条 (天空蓝)
        cv2.rectangle(img, (0, 0), (w, header_h), self.C_BG_HEADER, -1)
        # 底部白色分割线
        cv2.line(img, (0, header_h), (w, header_h), (255, 255, 255), 3)

        # 2. LOGO (黄色字 + 深色描边)
        self._draw_text_with_outline(img, "AIR RUNNER", (20, 42), 1.0, self.C_ACCENT, 2)

        # 3. [ESC 提示] (紧跟 LOGO 右侧)
        # 计算 LOGO 宽度以确定提示文字的 X 坐标
        (logo_w, _), _ = cv2.getTextSize("AIR RUNNER", cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        hint_x = 20 + logo_w + 15

        # 绘制提示文字
        cv2.putText(img, "[ESC to EXIT]", (hint_x, 42), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, self.C_TEXT_MAIN, 1)

        # 4. 当前动作指示 
        if action != "NEUTRAL":
            # 准备文字
            text = action
            font_scale = 1.2
            thickness = 3
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

            # 居中位置
            cx = (w - tw) // 2

            # 绘制绿色圆角矩形背景 (模拟按钮)
            pad_x = 20
            pad_y = 10
            # 注意：OpenCV 画矩形是 左上角 -> 右下角
            # 文字基线是 y=50，所以矩形顶端大概在 15 左右
            cv2.rectangle(img, (cx - pad_x, 15), (cx + tw + pad_x, 15 + th + pad_y + 10), self.C_OK, -1)

            # 绘制文字
            self._draw_text_with_outline(img, text, (cx, 52), font_scale, self.C_TEXT_MAIN, thickness)

        # 5. FPS 显示 (右上角)
        fps_text = f"FPS: {int(self.fps)}"
        self._draw_text_with_outline(img, fps_text, (w - 130, 42), 0.6, self.C_OK, 2)

    def _draw_countdown(self, img, num):
        h, w, _ = img.shape

        # 全屏雾化遮罩
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (255, 255, 255), -1)
        cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)

        # 倒计时大字
        text = str(int(num))
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 6
        thick = 15

        # 计算居中坐标
        size = cv2.getTextSize(text, font, scale, thick)[0]
        cx, cy = (w - size[0]) // 2, (h + size[1]) // 2 - 20

        # 绘制数字
        self._draw_text_with_outline(img, text, (cx, cy), scale, self.C_ACCENT, 5)

        # 绘制副标题 "GET READY!"
        sub_text = "GET READY!"
        sub_scale = 1.5
        sub_thick = 3
        sub_size = cv2.getTextSize(sub_text, font, sub_scale, sub_thick)[0]
        sub_x = (w - sub_size[0]) // 2

        self._draw_text_with_outline(img, sub_text, (sub_x, cy + 80), sub_scale, self.C_WARN, sub_thick)