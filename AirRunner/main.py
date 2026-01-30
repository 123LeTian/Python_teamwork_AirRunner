import customtkinter as ctk
import cv2
import sys
import time
import webbrowser
import pyautogui
import numpy as np
from threading import Thread

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False
    print("Warning: matplotlib not found. Charts will be disabled.")

from ui_drawer import CyberHUD
from controllers import HandController, BodyController
from game_adapter import GameAdapter
from utils import ConfigManager, AudioManager, HistoryManager

# 风格配置
#=========================================
# 加载用户配置
USER_CONFIG = ConfigManager.load()
ctk.set_appearance_mode(USER_CONFIG.get("theme_mode", "Light"))
ctk.set_default_color_theme("blue")

THEME = {
    "bg_sky": ("#4EC0F9", "#1a1a1a"),
    "bg_sidebar": ("#F4F5F7", "#2b2b2b"),
    "card_bg": ("#FFFFFF", "#383838"),
    "frame_bg": ("#F7F9FC", "#424242"),
    "btn_green": ("#5BC236", "#2e7d32"),
    "btn_hover": ("#45A025", "#1b5e20"),
    "btn_red": ("#FF5252", "#c62828"),
    "accent_ylw": ("#FFC107", "#f57f17"),
    "text_dark": ("#3D4852", "#FFFFFF"),
    "text_light": ("#9AA5B1", "#B0BEC5"),
    "card_header_blue": ("#E3F2FD", "#1565C0"),
    "card_header_green": ("#E8F5E9", "#2E7D32"),
    "textbox_bg": ("#F9FAFB", "#505050"),
}

CV_COLOR_YELLOW = (7, 193, 255)
CV_COLOR_BLUE = (249, 192, 78)
CV_COLOR_GREEN = (54, 194, 91)
CV_COLOR_WHITE = (255, 255, 255)
CV_COLOR_DARK = (61, 72, 82)
CV_COLOR_RED = (82, 82, 255)

FONT_LOGO = ("Impact", 36)
FONT_H1 = ("Microsoft YaHei UI", 22, "bold")
FONT_H2 = ("Microsoft YaHei UI", 16, "bold")
FONT_BODY = ("Microsoft YaHei UI", 14)

GAME_URLS = {
    "地铁跑酷 (Subway Surfers)": "https://poki.com/en/g/subway-surfers",
    "神庙逃亡2 (Temple Run 2)": "https://poki.com/en/g/temple-run-2",
    "恐龙快跑 (Chrome Dino)": "https://chromedino.com/"
}


# 智能校准
# =========================================
def draw_centered_text(img, text, y, font_scale, color, thickness=2, outline=True):
    h, w, _ = img.shape
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = (w - text_w) // 2
    if outline:
        cv2.putText(img, text, (x, y), font, font_scale, CV_COLOR_DARK, thickness + 3)
    cv2.putText(img, text, (x, y), font, font_scale, color, thickness)


def run_calibration_wizard(camera_index=0):
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened(): return None

    detector = BodyController()
    win_name = "Smart Calibration"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 640, 480)

    steps = [
        {"id": "NEUTRAL", "title": "STEP 1: NEUTRAL", "desc": "Sit Still & Look Forward", "dur": 3},
        {"id": "JUMP", "title": "STEP 2: JUMP POSE", "desc": "Stand Up OR Move Head UP", "dur": 3},
        {"id": "DUCK", "title": "STEP 3: DUCK POSE", "desc": "Squat Down OR Move Head DOWN", "dur": 3},
        {"id": "LEFT", "title": "STEP 4: LEAN LEFT", "desc": "Lean Body/Head LEFT", "dur": 3},
        {"id": "RIGHT", "title": "STEP 5: LEAN RIGHT", "desc": "Lean Body/Head RIGHT", "dur": 3}
    ]

    collected_data = {k["id"]: [] for k in steps}
    current_step_idx = 0
    state = 0  # 0:Prepare, 1:Record
    timer_start = time.time()
    elapsed = 0
    last_beep = 0
    AudioManager.play("notify")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        _, body_data = detector.process(frame)
        step_info = steps[current_step_idx]

        if body_data:
            elapsed = time.time() - timer_start
        else:
            timer_start = time.time() - elapsed

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), CV_COLOR_WHITE, -1)
        cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)
        cv2.line(frame, (0, 120), (w, 120), CV_COLOR_BLUE, 4)
        draw_centered_text(frame, step_info["title"], 50, 1.2, CV_COLOR_BLUE, 3, outline=False)
        draw_centered_text(frame, step_info["desc"], 95, 0.7, CV_COLOR_DARK, 2, outline=False)

        if body_data:
            cx, cy = body_data
            cv2.circle(frame, (cx, cy), 15, CV_COLOR_YELLOW, -1)
            cv2.circle(frame, (cx, cy), 15, CV_COLOR_DARK, 2)
            if state == 0:
                left = 3.0 - elapsed
                if left > 0:
                    draw_centered_text(frame, f"Wait: {int(left) + 1}", h // 2, 2.0, CV_COLOR_YELLOW, 5)
                    if int(left) != last_beep:
                        AudioManager.play("notify")
                        last_beep = int(left)
                else:
                    state = 1
                    timer_start = time.time()
                    elapsed = 0
                    AudioManager.play("start")
            elif state == 1:
                collected_data[step_info["id"]].append(body_data)
                prog = min(elapsed / step_info["dur"], 1.0)
                cv2.rectangle(frame, (0, h - 30), (int(w * prog), h), CV_COLOR_GREEN, -1)
                draw_centered_text(frame, "Recording...", h // 2 + 50, 1, CV_COLOR_GREEN, 2)
                if elapsed >= step_info["dur"]:
                    current_step_idx += 1
                    AudioManager.play("success")
                    if current_step_idx >= len(steps): break
                    state = 0;
                    timer_start = time.time();
                    elapsed = 0;
                    last_beep = 0
        else:
            warn_overlay = frame.copy()
            cv2.rectangle(warn_overlay, (0, 0), (w, h), (0, 0, 255), -1)
            cv2.addWeighted(warn_overlay, 0.2, frame, 0.8, 0, frame)
            draw_centered_text(frame, "USER NOT DETECTED", h // 2 - 20, 1.2, CV_COLOR_RED, 3)
            draw_centered_text(frame, "Please show your face", h // 2 + 30, 0.8, CV_COLOR_WHITE, 2)

        cv2.imshow(win_name, frame)
        if cv2.waitKey(1) == 27:
            cap.release();
            cv2.destroyAllWindows();
            return None

    cap.release();
    cv2.destroyAllWindows()
    try:
        neutral_y = np.mean([p[1] for p in collected_data["NEUTRAL"]]) / h
        jump_y = np.min([p[1] for p in collected_data["JUMP"]]) / h
        duck_y = np.max([p[1] for p in collected_data["DUCK"]]) / h
        neutral_x = np.mean([p[0] for p in collected_data["NEUTRAL"]]) / w
        left_x = np.min([p[0] for p in collected_data["LEFT"]]) / w
        right_x = np.max([p[0] for p in collected_data["RIGHT"]]) / w
        return {
            "jump_thresh": round(min((neutral_y + jump_y) / 2, neutral_y - 0.05), 2),
            "duck_thresh": round(max((neutral_y + duck_y) / 2, neutral_y + 0.05), 2),
            "left_thresh": round(min((neutral_x + left_x) / 2, neutral_x - 0.05), 2),
            "right_thresh": round(max((neutral_x + right_x) / 2, neutral_x + 0.05), 2)
        }
    except:
        return None


# 游戏主循环
# =========================================
def run_game_loop(mode_type, settings, game_url):
    if game_url: webbrowser.open(game_url)
    cam_index = settings.get("camera_index", 0)
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW if sys.platform.startswith("win") else 0)
    if not cap.isOpened(): return "ERROR_CAM"

    cap.set(3, 640);
    cap.set(4, 480)
    window_name = "AirRunner HUD"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 640, 480)
    try:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    except:
        pass

    hud = CyberHUD()
    adapter = GameAdapter()
    detector = HandController(settings=settings) if mode_type == "HAND" else BodyController(settings=settings)

    start_time = time.time()

    last_user_seen = time.time()
    is_auto_paused = False

    countdown_dur = 4
    last_cd_int = 5
    focus_acquired = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)

        if np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)) < 40:
            frame = hud.draw_warning(frame, "Too Dark! Check Light")
            cv2.imshow(window_name, frame)
            if cv2.waitKey(5) & 0xFF == 27: break
            continue

        elapsed = time.time() - start_time
        remaining = countdown_dur - elapsed
        thresholds = detector.get_thresholds()

        if remaining > 0:
            # 倒计时逻辑
            if int(remaining) != last_cd_int:
                AudioManager.play("countdown")
                last_cd_int = int(remaining)
            if remaining < 1.5 and not focus_acquired:
                try:
                    w, h = pyautogui.size()
                    pyautogui.click(w // 2, h // 2)
                except:
                    pass
                focus_acquired = True

            _, data = detector.process(frame)
            frame = hud.draw_interface(frame, "READY", data, thresholds, countdown=remaining)
            last_user_seen = time.time()
        else:
            # 游戏逻辑
            if last_cd_int != -1:
                AudioManager.play("start")
                last_cd_int = -1

            raw_action, data = detector.process(frame)

            # 自动暂停逻辑
            if data is not None:
                last_user_seen = time.time()
                if is_auto_paused:
                    is_auto_paused = False  # 用户回来了
            else:
                if time.time() - last_user_seen > 2.0:
                    is_auto_paused = True  # 2秒没检测到人，自动暂停

            if is_auto_paused:
                if time.time() - last_user_seen < 2.2:  # 触发一次ESC
                    adapter.execute("PAUSE")
                frame = hud.draw_auto_pause(frame)
                action = "PAUSE"
            else:
                action = raw_action
                adapter.execute(action)
                frame = hud.draw_interface(frame, action, data, thresholds, countdown=0)

        cv2.imshow(window_name, frame)
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1: break
        if cv2.waitKey(5) & 0xFF == 27: break

    cap.release();
    cv2.destroyAllWindows()
    return adapter.get_stats()


# 结算报告
# =========================================
class ReportWindow(ctk.CTkToplevel):
    def __init__(self, parent, stats):
        super().__init__(parent)
        self.title("运动报告")
        self.geometry("500x700")  # 稍微加高一点以容纳图表
        self.configure(fg_color=THEME["bg_sky"])
        self.attributes("-topmost", True)

        # 保存数据
        HistoryManager.save_session(stats)

        # 创建滚动容器
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # 结果卡片
        card = ctk.CTkFrame(scroll, fg_color=THEME["card_bg"], corner_radius=20)
        card.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(card, text="🎉 游戏结束! 🎉", font=("Microsoft YaHei UI", 24, "bold"),
                     text_color=THEME["btn_green"]).pack(pady=(30, 10))
        ctk.CTkLabel(card, text=f"坚持时长: {stats.get('TOTAL_TIME', 0)} 秒", font=FONT_BODY,
                     text_color=THEME["text_light"]).pack(pady=(0, 20))

        grid = ctk.CTkFrame(card, fg_color=THEME["frame_bg"], corner_radius=15)
        grid.pack(fill="x", padx=30, pady=10)

        items = [
            ("⬆️ 跳跃", stats.get("JUMP", 0)), ("⬇️ 下蹲", stats.get("DUCK", 0)),
            ("⬅️ 左移", stats.get("LEFT", 0)), ("➡️ 右移", stats.get("RIGHT", 0))
        ]

        for i, (label, count) in enumerate(items):
            f = ctk.CTkFrame(grid, fg_color="transparent")
            f.grid(row=i // 2, column=i % 2, sticky="ew", padx=10, pady=10)
            ctk.CTkLabel(f, text=str(count), font=("Arial", 24, "bold"), text_color=THEME["text_dark"]).pack()
            ctk.CTkLabel(f, text=label, font=FONT_BODY, text_color=THEME["text_light"]).pack()

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        # 估算热量
        total_jumps = stats.get("JUMP", 0)
        total_ducks = stats.get("DUCK", 0)
        # 假设每次跳跃消耗0.5千卡，下蹲消耗0.3千卡，侧身消耗0.1千卡
        calories = (total_jumps * 0.5) + (total_ducks * 0.3) + ((stats.get("LEFT", 0) + stats.get("RIGHT", 0)) * 0.1)

        # 在界面上展示
        ctk.CTkLabel(card, text=f"🔥 消耗热量: {round(calories, 2)} kcal", font=("Arial", 16, "bold"),
                     text_color="#FF5252").pack(pady=(0, 10))

        # 历史趋势图表
        if HAS_PLOT:
            chart_frame = ctk.CTkFrame(scroll, fg_color=THEME["card_bg"], corner_radius=20)
            chart_frame.pack(fill="x", padx=10, pady=10)
            ctk.CTkLabel(chart_frame, text="📈 近期活跃度 (动作总数)", font=FONT_H2, text_color=THEME["text_dark"]).pack(
                pady=10)
            self._draw_chart(chart_frame)

        ctk.CTkButton(self, text="关闭", font=FONT_H2, fg_color=THEME["btn_green"], height=50, corner_radius=20,
                      command=self.destroy).pack(side="bottom", pady=20)

    def _draw_chart(self, parent):
        # 获取数据
        history = HistoryManager.load_recent(7)
        if not history:
            ctk.CTkLabel(parent, text="暂无历史数据", text_color=THEME["text_light"]).pack(pady=20)
            return

        dates = [f"G{i + 1}" for i in range(len(history))]
        scores = [int(h["Total_Actions"]) for h in history]

        # Matplotlib绘图
        fig = Figure(figsize=(5, 3), dpi=100)

        # 适配深色/浅色模式
        bg_color = '#FFFFFF'
        text_color = 'black'
        if ctk.get_appearance_mode() == "Dark":
            bg_color = '#383838'
            text_color = 'white'

        fig.patch.set_facecolor(bg_color)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg_color)

        bars = ax.bar(dates, scores, color='#5BC236', width=0.5)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(text_color)
        ax.spines['bottom'].set_color(text_color)
        ax.tick_params(axis='x', colors=text_color)
        ax.tick_params(axis='y', colors=text_color)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)


# 启动页面
# =========================================
class SplashScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=THEME["bg_sky"])
        self.controller = controller

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(center, text="AIR", font=("Impact", 60), text_color=THEME["accent_ylw"]).pack()
        ctk.CTkLabel(center, text="RUNNER", font=("Impact", 60), text_color="white").pack()

        self.status_lbl = ctk.CTkLabel(center, text="正在初始化摄像头...", font=FONT_BODY, text_color="white")
        self.status_lbl.pack(pady=20)

        self.progress = ctk.CTkProgressBar(center, width=300, progress_color=THEME["accent_ylw"])
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.after(500, self.check_system)

    def check_system(self):
        self.progress.set(0.3)
        try:
            cam_idx = self.controller.global_settings.get("camera_index", 0)
            cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW if sys.platform.startswith("win") else 0)
            if cap.isOpened():
                self.progress.set(1.0)
                self.status_lbl.configure(text="系统就绪!")
                cap.release()
                self.after(800, lambda: self.controller.show_frame("PageHome"))
            else:
                self.status_lbl.configure(text="❌ 未检测到摄像头", text_color=THEME["btn_red"])
        except:
            self.status_lbl.configure(text="❌ 系统错误", text_color=THEME["btn_red"])


# PageHome
# =========================================
class PageHome(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(pady=(10, 20), fill="x")
        ctk.CTkLabel(title_frame, text="准备好奔跑了吗？", font=("Microsoft YaHei UI", 28, "bold"),
                     text_color=THEME["text_dark"]).pack(anchor="w")

        game_bar = ctk.CTkFrame(self, fg_color=THEME["card_bg"], corner_radius=15, height=80)
        game_bar.pack(fill="x", pady=10)
        game_bar.pack_propagate(False)
        ctk.CTkLabel(game_bar, text="当前目标:", font=FONT_H2, text_color=THEME["text_dark"]).pack(side="left", padx=20)
        self.combo_game = ctk.CTkComboBox(game_bar, values=list(GAME_URLS.keys()), width=300, height=40, font=FONT_BODY,
                                          corner_radius=20)
        self.combo_game.pack(side="left", padx=10)
        self.combo_game.set("地铁跑酷 (Subway Surfers)")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, pady=20)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        self._create_card(grid, 0, "🖐 手势模式", "虚拟摇杆体验\n单手控制", THEME["card_header_blue"],
                          lambda: self.start_game("HAND"))
        self._create_card(grid, 1, "😊 面部模式", "面部识别控制\n跳跃下蹲", THEME["card_header_green"],
                          lambda: self.start_game("BODY"))

    def _create_card(self, parent, col, title, desc, bg_color, cmd):
        card = ctk.CTkFrame(parent, fg_color=THEME["card_bg"], corner_radius=20)
        card.grid(row=0, column=col, padx=15, sticky="nsew")
        header = ctk.CTkFrame(card, fg_color=bg_color, height=100, corner_radius=20)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text=title, font=("Microsoft YaHei UI", 24, "bold"), text_color="#3D4852").place(
            relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(card, text=desc, font=FONT_BODY, text_color=THEME["text_light"], justify="center").pack(pady=20)
        ctk.CTkButton(card, text="GO!", font=("Arial Rounded MT Bold", 24), fg_color=THEME["btn_green"],
                      hover_color=THEME["btn_hover"], corner_radius=25, height=60, width=160, command=cmd).pack(
            side="bottom", pady=40)

    def start_game(self, mode):
        settings = self.controller.global_settings
        game_url = GAME_URLS[self.combo_game.get()]
        self.controller.withdraw()
        try:
            stats = run_game_loop(mode, settings, game_url)
            if stats == "ERROR_CAM":
                ctk.CTkInputDialog(text="无法打开摄像头！\n请检查连接。", title="错误")
        except Exception as e:
            print(f"Loop Error: {e}")
            stats = None
        finally:
            self.controller.deiconify()
            if stats and stats != "ERROR_CAM":
                ReportWindow(self.controller, stats)


# PageSettings
# ========================================
class PageSettings(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        panel = ctk.CTkFrame(self, fg_color=THEME["card_bg"], corner_radius=20)
        panel.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=20)
        ctk.CTkLabel(header, text="⚙️ 系统设置", font=FONT_H1, text_color=THEME["text_dark"]).pack(side="left")

        self.theme_btn = ctk.CTkButton(header, text="切换主题 🌓", width=100, command=self.toggle_theme)
        self.theme_btn.pack(side="right")

        cam_frame = ctk.CTkFrame(panel, fg_color=THEME["frame_bg"], corner_radius=15)
        cam_frame.pack(fill="x", padx=40, pady=10)

        ctk.CTkLabel(cam_frame, text="📸 视频输入设备", font=FONT_H2, text_color=THEME["text_dark"]).pack(anchor="w",
                                                                                                         padx=20,
                                                                                                         pady=(15, 5))

        self.camera_combo = ctk.CTkComboBox(
            cam_frame,
            values=["Camera 0 (默认)", "Camera 1 (外接)", "Camera 2"],
            width=250, font=FONT_BODY, dropdown_font=FONT_BODY,
            command=self.on_camera_change
        )
        self.camera_combo.set("Camera 0 (默认)")
        self.camera_combo.pack(padx=20, pady=10, anchor="w")

        calib_frame = ctk.CTkFrame(panel, fg_color=THEME["card_header_blue"], corner_radius=15)
        calib_frame.pack(fill="x", padx=40, pady=10)
        ctk.CTkLabel(calib_frame, text="🧠 智能校准向导 (推荐)", font=FONT_H2, text_color="#3D4852").pack(
            side="left",
            padx=20,
            pady=20)
        ctk.CTkLabel(calib_frame, text="自动检测坐姿范围，定制灵敏度", font=FONT_BODY, text_color="#546E7A").pack(
            side="left", padx=10)

        ctk.CTkButton(calib_frame, text="开始校准", font=FONT_H2, fg_color=THEME["accent_ylw"], text_color="black",
                      hover_color=THEME["accent_ylw"], width=120, command=self.start_calibration_wizard).pack(
            side="right",
            padx=20)

        self.sliders = {}

        self._add_slider_group(panel, "垂直灵敏度 (数值微调)", [
            ("跳跃 (Jump)", "jump_thresh", 0.4, 0.1, 0.5),
            ("下蹲 (Duck)", "duck_thresh", 0.6, 0.5, 0.9)
        ])

        self._add_slider_group(panel, "水平灵敏度 (左右判定)", [
            ("左移阈值 (Left <)", "left_thresh", 0.4, 0.2, 0.45),
            ("右移阈值 (Right >)", "right_thresh", 0.6, 0.55, 0.8)
        ])

    def _add_slider_group(self, parent, group_title, items):
        group = ctk.CTkFrame(parent, fg_color=THEME["frame_bg"], corner_radius=15)
        group.pack(fill="x", padx=40, pady=10)
        ctk.CTkLabel(group, text=group_title, font=FONT_H2, text_color=THEME["text_dark"]).pack(anchor="w", padx=20,
                                                                                                pady=(15, 5))

        for label, key, default, min_v, max_v in items:
            row = ctk.CTkFrame(group, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(row, text=label, width=150, anchor="w", font=FONT_BODY, text_color=THEME["text_light"]).pack(
                side="left")

            val_lbl = ctk.CTkLabel(row, text=f"{default}", width=40, font=("Arial", 14, "bold"),
                                   text_color=THEME["btn_green"])
            val_lbl.pack(side="right")

            slider = ctk.CTkSlider(
                row, from_=min_v, to=max_v, number_of_steps=20,
                button_color=THEME["btn_green"], progress_color=THEME["btn_green"],
                command=lambda v, k=key, l=val_lbl: self.on_slider_change(k, v, l)
            )
            slider.set(default)
            slider.pack(side="right", fill="x", expand=True, padx=20)
            self.sliders[key] = slider

    def on_camera_change(self, choice):
        try:
            idx = int(choice.split(" ")[1])
        except:
            idx = 0
        self.controller.update_settings({"camera_index": idx})

    def on_slider_change(self, key, value, label_widget):
        label_widget.configure(text=f"{round(value, 2)}")
        self.controller.update_settings({key: round(value, 2)})

    def toggle_theme(self):
        curr = ctk.get_appearance_mode()
        new_mode = "Dark" if curr == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        self.controller.update_settings({"theme_mode": new_mode})

    def refresh(self):
        g_set = self.controller.global_settings
        for key, slider in self.sliders.items():
            if key in g_set:
                slider.set(g_set[key])
        curr_cam = g_set.get("camera_index", 0)
        self.camera_combo.set(f"Camera {curr_cam} (当前)")

    def start_calibration_wizard(self):
        self.controller.withdraw()
        cam_idx = self.controller.global_settings.get("camera_index", 0)
        new_settings = run_calibration_wizard(cam_idx)
        self.controller.deiconify()

        if new_settings:
            self.controller.update_settings(new_settings)
            self.refresh()
            ctk.CTkInputDialog(text="Calibration Success!\nSettings Updated.", title="Success")



# PageManual
# =========================================
class PageManual(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        paper = ctk.CTkFrame(self, fg_color=THEME["card_bg"], corner_radius=20)
        paper.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(paper, text="📖 新手指南", font=FONT_H1, text_color=THEME["text_dark"]).pack(pady=(30, 10))

        text_box = ctk.CTkTextbox(paper, font=FONT_BODY, fg_color=THEME["textbox_bg"], text_color=THEME["text_dark"],
                                  corner_radius=15)
        text_box.pack(fill="both", expand=True, padx=30, pady=20)
        manual_text = """
🏃 欢迎使用 AirRunner 智能体感系统！

本系统通过摄像头捕捉你的动作，模拟键盘按键来玩跑酷游戏。为了获得最佳体验，请阅读以下指南：

━━━━━━━━━━━━━━━━━━━━
🕹️ 核心模式介绍
━━━━━━━━━━━━━━━━━━━━

1️⃣ 😊 面部模式 (Body Mode) - 推荐！
   原理：捕捉你的“鼻尖”作为控制核心。
   • ⬆️ 跳跃 (Jump)： 抬头 或 向上挺身
   • ⬇️ 下滑 (Duck)： 低头 或 向下蹲
   • ⬅️ 左移 (Left)： 身体/头部 向左倾
   • ➡️ 右移 (Right)： 身体/头部 向右倾
   💡 技巧： 就像你在亲自跑酷一样，动作幅度不用太大，节奏感最重要！

2️⃣ 🖐 手势模式 (Hand Mode)
   原理：屏幕中心有一个隐形的“虚拟摇杆”。
   • 🕹️ 移动： 将手掌移出屏幕中心的“安全区”即可触发方向。
   • ⏸️ 暂停： ✊ 握紧拳头保持 1 秒，触发 ESC 键暂停。
   💡 技巧： 手掌正对摄像头，保持在画面内。

━━━━━━━━━━━━━━━━━━━━
⚙️ 最佳体验设置
━━━━━━━━━━━━━━━━━━━━

✅ 第一步：智能校准 (非常重要)
   系统现已支持全方位校准！
   请进入 [智能设置] -> [开始校准]，跟随屏幕完成：
   中立 -> 跳跃 -> 下蹲 -> 左倾 -> 右倾。
   (如果未检测到人像，倒计时会自动暂停)

✅ 第二步：光线环境
   ❌ 避免背光（窗户在身后）。
   ❌ 避免环境太暗。
   💡 保证面部/手部光线充足且均匀。

━━━━━━━━━━━━━━━━━━━━
❓ 常见问题 FAQ
━━━━━━━━━━━━━━━━━━━━

Q：为什么做了动作游戏没反应？
A：网页游戏需要“焦点”。虽然系统会自动点击，但如果没反应，请尝试手动用鼠标点一下游戏画面中心。

Q：动作触发太灵敏/太迟钝？
A：请重新进行 [智能校准]，或者在设置里手动微调“垂直/水平灵敏度”滑块。

Q：如何退出？
A：点击摄像头预览窗口，按下键盘 [ESC] 键即可退出并查看运动报告。

祝你打破纪录！🏆
                """
        text_box.insert("0.0", manual_text)
        text_box.configure(state="disabled")


# 主程序界面
# =========================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AirRunner - 智能体感跑酷")
        self.geometry("1000x700")
        self._center_window(1000, 700)
        self.configure(fg_color=THEME["bg_sky"])

        self.global_settings = USER_CONFIG.copy()

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, fg_color=THEME["bg_sidebar"], width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self._init_sidebar()

        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        self.frames = {}
        for F in (SplashScreen, PageHome, PageSettings, PageManual):
            page_name = F.__name__
            frame = F(parent=self.content_area, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("SplashScreen")

    def _center_window(self, w, h):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{(screen_width - w) // 2}+{(screen_height - h) // 2}')

    def _init_sidebar(self):
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(40, 30))
        ctk.CTkLabel(logo_frame, text="AIR", font=FONT_LOGO, text_color=THEME["accent_ylw"]).pack()
        ctk.CTkLabel(logo_frame, text="RUNNER", font=FONT_LOGO, text_color=THEME["text_dark"]).pack(pady=(0, 10))

        self.nav_btns = {}

        def create_nav_btn(text, icon, target):
            btn = ctk.CTkButton(
                self.sidebar, text=f"{icon}  {text}", font=FONT_H2,
                fg_color="transparent", text_color=THEME["text_dark"], hover_color=THEME["frame_bg"],
                anchor="w", height=50, corner_radius=10,
                command=lambda: self.show_frame(target)
            )
            btn.pack(fill="x", padx=15, pady=8)
            self.nav_btns[target] = btn

        create_nav_btn("开始游戏", "🎮", "PageHome")
        create_nav_btn("智能设置", "⚙️", "PageSettings")
        create_nav_btn("帮助文档", "📖", "PageManual")

        ctk.CTkLabel(self.sidebar, text="Ver 3.3 Final", font=("Arial", 10), text_color=THEME["text_light"]).pack(
            side="bottom",
            pady=20)

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "refresh"):
            frame.refresh()

        for name, btn in self.nav_btns.items():
            if name == page_name:
                btn.configure(fg_color=THEME["card_bg"], text_color=THEME["btn_green"])
            else:
                btn.configure(fg_color="transparent", text_color=THEME["text_dark"])

        if page_name == "SplashScreen":
            self.sidebar.grid_remove()
        else:
            self.sidebar.grid()

    def update_settings(self, new_settings):
        self.global_settings.update(new_settings)
        ConfigManager.save(self.global_settings)


if __name__ == "__main__":
    app = App()
    app.mainloop()