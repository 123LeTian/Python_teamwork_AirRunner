import customtkinter as ctk
import cv2
import sys
import os
import time
import webbrowser
import pyautogui 
from threading import Thread

# --- 导入模块 ---
from ui_drawer import CyberHUD
from controllers import HandController, BodyController
from game_adapter import GameAdapter

# =========================================
# 🎨 风格配置
# =========================================
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

THEME = {
    "bg_sky": "#4EC0F9",
    "bg_sidebar": "#F4F5F7",
    "card_bg": "#FFFFFF",
    "btn_green": "#5BC236",
    "btn_hover": "#45A025",
    "accent_ylw": "#FFC107",
    "text_dark": "#3D4852",
    "text_light": "#9AA5B1",
    "border": "#E0E6ED",
}

FONT_LOGO = ("Impact", 36)
FONT_H1 = ("Microsoft YaHei UI", 22, "bold")
FONT_H2 = ("Microsoft YaHei UI", 16, "bold")
FONT_BODY = ("Microsoft YaHei UI", 14)

GAME_URLS = {
    "地铁跑酷 (Subway Surfers)": "https://poki.com/en/g/subway-surfers",
    "神庙逃亡2 (Temple Run 2)": "https://poki.com/en/g/temple-run-2",
    "恐龙快跑 (Chrome Dino)": "https://chromedino.com/"
}


# =========================================
# 📊 结算报告弹窗
# =========================================
class ReportWindow(ctk.CTkToplevel):
    def __init__(self, parent, stats):
        super().__init__(parent)
        self.title("运动报告")
        self.geometry("400x500")
        self.configure(fg_color=THEME["bg_sky"])

        # 居中
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"400x500+{(screen_w - 400) // 2}+{(screen_h - 500) // 2}")
        self.attributes("-topmost", True)  # 置顶

        # 容器
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=20)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        ctk.CTkLabel(card, text="🎉 游戏结束! 🎉", font=("Microsoft YaHei UI", 24, "bold"),
                     text_color=THEME["btn_green"]).pack(pady=(30, 10))
        ctk.CTkLabel(card, text=f"坚持时长: {stats.get('TOTAL_TIME', 0)} 秒", font=FONT_BODY, text_color="gray").pack(
            pady=(0, 20))

        # 数据网格
        grid = ctk.CTkFrame(card, fg_color="#F7F9FC", corner_radius=15)
        grid.pack(fill="x", padx=30, pady=10)

        items = [
            ("⬆️ 跳跃", stats.get("JUMP", 0)),
            ("⬇️ 下蹲", stats.get("DUCK", 0)),
            ("⬅️ 左移", stats.get("LEFT", 0)),
            ("➡️ 右移", stats.get("RIGHT", 0))
        ]

        for i, (label, count) in enumerate(items):
            row = i // 2
            col = i % 2
            f = ctk.CTkFrame(grid, fg_color="transparent")
            f.grid(row=row, column=col, sticky="ew", padx=10, pady=10)
            ctk.CTkLabel(f, text=str(count), font=("Arial", 24, "bold"), text_color=THEME["text_dark"]).pack()
            ctk.CTkLabel(f, text=label, font=FONT_BODY, text_color="gray").pack()

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        # 总计
        total = sum([v for k, v in stats.items() if k != "TOTAL_TIME"])
        ctk.CTkLabel(card, text=f"🔥 总消耗动作: {total}", font=FONT_H2, text_color=THEME["accent_ylw"]).pack(pady=20)

        # 关闭按钮
        ctk.CTkButton(card, text="再来一局", font=FONT_H2, fg_color=THEME["btn_green"], hover_color=THEME["btn_hover"],
                      corner_radius=20, width=200, height=50, command=self.destroy).pack(side="bottom", pady=30)


# =========================================
# 🎮 游戏循环
# =========================================
def run_game_loop(mode_type, settings, game_url):
    # 1. 打开浏览器
    if game_url:
        webbrowser.open(game_url)

    # 2. 获取摄像头索引
    cam_index = settings.get("camera_index", 0)

    # 3. 初始化摄像头
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(cam_index)

    if not cap.isOpened():
        print(f"Error: Camera {cam_index} not found")
        return None  # 返回 None 表示失败

    cap.set(3, 640)
    cap.set(4, 480)

    window_name = "AirRunner HUD"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # 窗口定位
    win_w, win_h = 640, 480
    cv2.resizeWindow(window_name, win_w, win_h)
    try:
        screen_w, screen_h = pyautogui.size()
        cv2.moveWindow(window_name, screen_w - win_w - 50, 50)
    except:
        cv2.moveWindow(window_name, 50, 50)

    if hasattr(cv2, "WND_PROP_TOPMOST"):
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    # 初始化模块
    hud = CyberHUD()
    adapter = GameAdapter() 

    if mode_type == "HAND":
        detector = HandController(settings=settings)
    else:
        detector = BodyController(settings=settings)

    start_time = time.time()
    countdown_dur = 4
    focus_acquired = False  # 标记是否已自动点击

    # --- 循环开始 ---
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        elapsed = time.time() - start_time
        remaining = countdown_dur - elapsed

        action = "NEUTRAL"
        data = None
        thresholds = detector.get_thresholds()

        if remaining > 0:
            # ===  自动获取焦点逻辑 ===
            # 在倒计时剩 1.5 秒时，模拟点击屏幕中心
            if remaining < 1.5 and not focus_acquired:
                try:
                    sw, sh = pyautogui.size()
                    # 保存当前鼠标位置
                    ox, oy = pyautogui.position()
                    # 点击屏幕中心
                    pyautogui.click(sw // 2, sh // 2)
                    # 恢复鼠标位置
                    pyautogui.moveTo(ox, oy)
                    print(">>> Auto-Focus: Clicked center screen")
                except Exception as e:
                    print(f"Auto-Focus failed: {e}")
                focus_acquired = True
            # ============================

            _, data = detector.process(frame)
            frame = hud.draw_interface(frame, "READY", data, thresholds, countdown=remaining)
        else:
            action, data = detector.process(frame)
            adapter.execute(action)
            frame = hud.draw_interface(frame, action, data, thresholds, countdown=0)

        cv2.imshow(window_name, frame)

        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break
        # ESC 退出
        if cv2.waitKey(5) & 0xFF == 27:
            break

    # 资源释放
    cap.release()
    cv2.destroyAllWindows()

    # 返回统计数据
    return adapter.get_stats()


# =========================================
# 🛹 主程序界面
# =========================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AirRunner - 跑酷助手")
        self.geometry("1000x700")
        self._center_window(1000, 700)
        self.configure(fg_color=THEME["bg_sky"])

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. 侧边栏
        self.sidebar = ctk.CTkFrame(self, fg_color=THEME["bg_sidebar"], width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self._init_sidebar()

        # 2. 内容区域
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        # 页面路由
        self.frames = {}
        for F in (PageHome, PageSettings, PageManual):
            page_name = F.__name__
            frame = F(parent=self.content_area, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("PageHome")

    def _center_window(self, w, h):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - w) // 2
        y = (screen_height - h) // 2
        self.geometry(f'{w}x{h}+{x}+{y}')

    def _init_sidebar(self):
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(40, 30))

        ctk.CTkLabel(logo_frame, text="AIR", font=FONT_LOGO, text_color=THEME["accent_ylw"]).pack()
        ctk.CTkLabel(logo_frame, text="RUNNER", font=FONT_LOGO, text_color=THEME["text_dark"]).pack(pady=(0, 10))

        def create_nav_btn(text, icon, target):
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}  {text}",
                font=FONT_H2,
                fg_color="transparent",
                text_color=THEME["text_dark"],
                hover_color="white",
                anchor="w",
                height=50,
                corner_radius=10,
                command=lambda: self.show_frame(target)
            )
            btn.pack(fill="x", padx=15, pady=8)
            return btn

        self.btn_home = create_nav_btn("开始游戏", "🎮", "PageHome")
        self.btn_set = create_nav_btn("设置选项", "⚙️", "PageSettings")
        self.btn_man = create_nav_btn("游戏说明", "📖", "PageManual")

        ctk.CTkLabel(self.sidebar, text="Ver 3.0 Pro", font=("Arial", 10), text_color="gray").pack(side="bottom",
                                                                                                   pady=20)

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        btns = {"PageHome": self.btn_home, "PageSettings": self.btn_set, "PageManual": self.btn_man}
        for name, btn in btns.items():
            if name == page_name:
                btn.configure(fg_color="white", text_color=THEME["btn_green"])
            else:
                btn.configure(fg_color="transparent", text_color=THEME["text_dark"])


# =========================================
# 🏠 页面 1: 游戏大厅
# =========================================
class PageHome(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(pady=(10, 20), fill="x")
        ctk.CTkLabel(title_frame, text="准备好奔跑了吗？", font=("Microsoft YaHei UI", 28, "bold"),
                     text_color="white").pack(anchor="w")

        # 游戏选择
        game_bar = ctk.CTkFrame(self, fg_color=THEME["card_bg"], corner_radius=15, height=80)
        game_bar.pack(fill="x", pady=10)
        game_bar.pack_propagate(False)

        ctk.CTkLabel(game_bar, text="当前目标:", font=FONT_H2, text_color=THEME["text_dark"]).pack(side="left", padx=20)

        self.combo_game = ctk.CTkComboBox(
            game_bar,
            values=list(GAME_URLS.keys()),
            width=300, height=40,
            font=FONT_BODY,
            dropdown_font=FONT_BODY,
            corner_radius=20,
            fg_color="#F0F2F5",
            border_width=0,
            text_color=THEME["text_dark"],
            button_color=THEME["accent_ylw"]
        )
        self.combo_game.pack(side="left", padx=10)
        self.combo_game.set("地铁跑酷 (Subway Surfers)")

        # 卡片容器
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, pady=20)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        self._create_card(grid, 0, "🖐 手势模式", "虚拟摇杆体验\n单手控制", "#E3F2FD", lambda: self.start_game("HAND"))
        self._create_card(grid, 1, "😊 面部模式", "面部识别控制\n跳跃下蹲", "#E8F5E9", lambda: self.start_game("BODY"))

    def _create_card(self, parent, col, title, desc, bg_color, cmd):
        card = ctk.CTkFrame(parent, fg_color=THEME["card_bg"], corner_radius=20)
        card.grid(row=0, column=col, padx=15, sticky="nsew")

        header = ctk.CTkFrame(card, fg_color=bg_color, height=100, corner_radius=20)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text=title, font=("Microsoft YaHei UI", 24, "bold"), text_color=THEME["text_dark"]).place(
            relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text=desc, font=FONT_BODY, text_color=THEME["text_light"], justify="center").pack(pady=20)

        ctk.CTkButton(
            card, text="GO!",
            font=("Arial Rounded MT Bold", 24),
            fg_color=THEME["btn_green"], hover_color=THEME["btn_hover"],
            corner_radius=25, height=60, width=160,
            command=cmd
        ).pack(side="bottom", pady=40)

    def start_game(self, mode):
        # 获取当前设置
        settings_page = self.controller.frames["PageSettings"]
        settings = settings_page.get_settings()
        game_url = GAME_URLS[self.combo_game.get()]

        self.controller.withdraw()  # 隐藏主窗口

        # 运行游戏循环 (阻塞式)
        try:
            stats = run_game_loop(mode, settings, game_url)
        except Exception as e:
            print(f"Loop Error: {e}")
            stats = None
        finally:
            self.controller.deiconify()  # 恢复主窗口

            # 如果有数据，显示结算报告
            if stats:
                ReportWindow(self.controller, stats)


# =========================================
# ⚙️ 页面 2: 设置
# =========================================
class PageSettings(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")

        panel = ctk.CTkFrame(self, fg_color=THEME["card_bg"], corner_radius=20)
        panel.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(panel, text="⚙️ 系统设置", font=FONT_H1, text_color=THEME["text_dark"]).pack(pady=20)

        # 1. 摄像头选择区
        cam_frame = ctk.CTkFrame(panel, fg_color="#F7F9FC", corner_radius=15)
        cam_frame.pack(fill="x", padx=40, pady=10)
        ctk.CTkLabel(cam_frame, text="📸 视频输入设备", font=FONT_H2, text_color=THEME["text_dark"]).pack(anchor="w",
                                                                                                         padx=20,
                                                                                                         pady=(15, 5))

        self.camera_combo = ctk.CTkComboBox(
            cam_frame,
            values=["Camera 0 (默认)", "Camera 1 (外接)", "Camera 2"],
            width=250, font=FONT_BODY, dropdown_font=FONT_BODY
        )
        self.camera_combo.set("Camera 0 (默认)")
        self.camera_combo.pack(padx=20, pady=10, anchor="w")

        # 2. 灵敏度滑块
        self.sliders = {}
        self._add_slider_group(panel, "垂直方向 (跳跃/下蹲)", [
            ("跳跃触发 (上)", "jump", 0.4, 0.1, 0.5),
            ("下蹲触发 (下)", "duck", 0.6, 0.5, 0.9)
        ])
        self._add_slider_group(panel, "水平方向 (左移/右移)", [
            ("左移触发", "left", 0.4, 0.1, 0.5),
            ("右移触发", "right", 0.6, 0.5, 0.9)
        ])

    def _add_slider_group(self, parent, group_title, items):
        group = ctk.CTkFrame(parent, fg_color="#F7F9FC", corner_radius=15)
        group.pack(fill="x", padx=40, pady=10)

        ctk.CTkLabel(group, text=group_title, font=FONT_H2, text_color=THEME["text_dark"]).pack(anchor="w", padx=20,
                                                                                                pady=(15, 5))

        for label, key, default, min_v, max_v in items:
            row = ctk.CTkFrame(group, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(row, text=label, width=120, anchor="w", font=FONT_BODY, text_color="gray").pack(side="left")
            val_lbl = ctk.CTkLabel(row, text=f"{default}", width=40, font=("Arial", 14, "bold"),
                                   text_color=THEME["btn_green"])
            val_lbl.pack(side="right")

            slider = ctk.CTkSlider(
                row, from_=min_v, to=max_v, number_of_steps=20,
                button_color=THEME["btn_green"], progress_color=THEME["btn_green"],
                height=20, corner_radius=10,
                command=lambda v, l=val_lbl: l.configure(text=f"{round(v, 2)}")
            )
            slider.set(default)
            slider.pack(side="right", fill="x", expand=True, padx=20)
            self.sliders[key] = slider

    def get_settings(self):
        # 解析摄像头索引 (例如 "Camera 1 (外接)" -> 1)
        cam_str = self.camera_combo.get()
        try:
            cam_idx = int(cam_str.split(" ")[1])
        except:
            cam_idx = 0

        settings = {k: round(v.get(), 2) for k, v in self.sliders.items()}
        settings["camera_index"] = cam_idx
        return settings


# =========================================
# 📖 页面 3: 游戏说明 
# =========================================
class PageManual(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        paper = ctk.CTkFrame(self, fg_color="white", corner_radius=20)
        paper.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(paper, text="📖 新手指南", font=FONT_H1, text_color=THEME["text_dark"]).pack(pady=(30, 10))
        text_box = ctk.CTkTextbox(paper, font=FONT_BODY, fg_color="#F9FAFB", text_color="#505050", corner_radius=15)
        text_box.pack(fill="both", expand=True, padx=30, pady=20)

        manual_text = """
👋 欢迎来到 AirRunner！

【1. 准备工作】
--------------------------------------------
• 确保摄像头光线充足。
• 如果是外接摄像头，请先去“设置”页面选择对应设备。
• 游戏启动时，请稍微后退，露出上半身（体感模式）或单手（手势模式）。

【2. 自动辅助功能】
--------------------------------------------
• 本程序会在倒计时结束前，自动点击屏幕中心一次，确保游戏能接收按键。
• 请不要在倒计时期间频繁移动鼠标。

【3. 模式介绍】
--------------------------------------------
🖐 手势模式 (Hand Mode)
   • 类似虚拟摇杆：手在画面中心不动。
   • 手向上/下/左/右移动 = 控制方向。
   • ✊ 握拳 = 暂停 (ESC)。

😊 面部模式 (Face Mode)
   • 鼻尖上下移动 = 跳跃/下滑。
   • 鼻尖左右移动 = 左右移动。

祝你打破纪录！🏆
        """
        text_box.insert("0.0", manual_text)
        text_box.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()