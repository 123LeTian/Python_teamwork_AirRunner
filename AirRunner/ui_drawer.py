import cv2
import numpy as np
import time

class CyberHUD:
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        # --- 配色方案 (BGR格式) ---
        self.COLOR_NEON_GREEN = (50, 255, 50)   # 正常/中立
        self.COLOR_ALERT_RED = (50, 50, 255)    # 触发动作
        self.COLOR_CYBER_BLUE = (255, 200, 0)   # UI 边框
        self.COLOR_DARK_MASK = (20, 20, 20)     # 半透明背景色
        self.COLOR_WHITE = (255, 255, 255)
        
        # 状态记录
        self.prev_time = time.time()
        self.fps = 0

    def _draw_transparent_rect(self, img, x, y, w, h, color, alpha=0.5):
        """ 绘制半透明矩形背景 (核心美化函数) """
        sub_img = img[y:y+h, x:x+w]
        white_rect = np.ones(sub_img.shape, dtype=np.uint8) * 0
        white_rect[:] = color
        
        # 混合图片实现透明效果
        res = cv2.addWeighted(sub_img, 1-alpha, white_rect, alpha, 1.0)
        img[y:y+h, x:x+w] = res

    def draw_interface(self, frame, action_text="NEUTRAL", hand_center=None, box_size=100):
        """
        主绘图函数：每一帧都调用这个
        :param frame: 当前视频帧
        :param action_text: 当前触发的动作 (如 "JUMP", "Running")
        :param hand_center: 手部中心坐标 (x, y)
        :param box_size: 中立区大小
        """
        h, w, _ = frame.shape
        center_x, center_y = w // 2, h // 2
        
        # --- 1. 计算 FPS (增加科技感) ---
        curr_time = time.time()
        self.fps = 1 / (curr_time - self.prev_time + 1e-5)
        self.prev_time = curr_time

        # --- 2. 绘制顶部状态栏 ---
        # 半透明黑条
        self._draw_transparent_rect(frame, 0, 0, w, 40, self.COLOR_DARK_MASK, alpha=0.6)
        # 左上角：系统名称
        cv2.putText(frame, "AIR-RUNNER SYSTEM v1.0", (15, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_CYBER_BLUE, 2)
        # 右上角：FPS显示
        cv2.putText(frame, f"FPS: {int(self.fps)}", (w - 120, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_NEON_GREEN, 2)

        # --- 3. 绘制中央核心区 (虚拟摇杆) ---
        # 根据是否触发动作改变颜色
        is_triggered = action_text != "NEUTRAL" and action_text != "RUNNING"
        box_color = self.COLOR_ALERT_RED if is_triggered else self.COLOR_NEON_GREEN
        thickness = 3 if is_triggered else 2

        # 绘制中心瞄准框 (四角设计，比普通矩形更帅)
        self._draw_corners(frame, center_x, center_y, box_size, box_color, thickness)
        
        # 如果正在触发动作，在屏幕中央显示大字
        if is_triggered:
            # 增加一个红色半透明遮罩，表示警告/高能
            self._draw_transparent_rect(frame, center_x-100, center_y-150, 200, 60, self.COLOR_ALERT_RED, 0.3)
            # 文字居中算法
            text_size = cv2.getTextSize(action_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
            text_x = center_x - text_size[0] // 2
            cv2.putText(frame, action_text, (text_x, center_y - 100), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, self.COLOR_WHITE, 3)

        # --- 4. 绘制手部光标 (如果有检测到手) ---
        if hand_center:
            hx, hy = hand_center
            # 画一个带光晕的瞄准点
            cv2.circle(frame, (hx, hy), 15, (255, 255, 255), 2) # 外圈
            cv2.circle(frame, (hx, hy), 5, box_color, -1)       # 内实心点
            # 画一条虚线连向中心 (视觉引导)
            cv2.line(frame, (center_x, center_y), (hx, hy), box_color, 1)

        # --- 5. 底部操作提示 ---
        self._draw_transparent_rect(frame, 0, h-40, w, 40, self.COLOR_DARK_MASK, alpha=0.6)
        cv2.putText(frame, "STATUS: SYSTEM ONLINE | MODE: HAND TRACKING", (15, h-12), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return frame

    def _draw_corners(self, img, cx, cy, size, color, thickness):
        """ 绘制科技感的四角边框，而不是傻傻的全封闭矩形 """
        r = size # 半径
        l = 30   # 角的长度
        
        # 左上角
        cv2.line(img, (cx-r, cy-r), (cx-r+l, cy-r), color, thickness)
        cv2.line(img, (cx-r, cy-r), (cx-r, cy-r+l), color, thickness)
        # 右上角
        cv2.line(img, (cx+r, cy-r), (cx+r-l, cy-r), color, thickness)
        cv2.line(img, (cx+r, cy-r), (cx+r, cy-r+l), color, thickness)
        # 左下角
        cv2.line(img, (cx-r, cy+r), (cx-r+l, cy+r), color, thickness)
        cv2.line(img, (cx-r, cy+r), (cx-r, cy+r-l), color, thickness)
        # 右下角
        cv2.line(img, (cx+r, cy+r), (cx+r-l, cy+r), color, thickness)
        cv2.line(img, (cx+r, cy+r), (cx+r, cy+r-l), color, thickness)
        
        # 中心十字准星 (淡淡的)
        cv2.line(img, (cx-10, cy), (cx+10, cy), color, 1)
        cv2.line(img, (cx, cy-10), (cx, cy+10), color, 1)