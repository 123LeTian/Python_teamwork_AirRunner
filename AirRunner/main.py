import customtkinter as ctk
import cv2
import sys
import os
import webbrowser 

# --- 导入队友的代码模块 ---
from ui_drawer import CyberHUD
from controllers import HandController, BodyController
from game_adapter import GameAdapter

# --- 全局设置 ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue") 

# --- 游戏链接配置 (你可以随时在这里加新游戏) ---
GAME_URLS = {
    "地铁跑酷 (Subway Surfers)": "https://poki.com/en/g/subway-surfers",
    "神庙逃亡2 (Temple Run 2)": "https://poki.com/en/g/temple-run-2",
    "恐龙快跑 (Chrome Dino)": "https://chromedino.com/"
}

# =========================================
# 🎮 核心游戏循环
# =========================================
def run_game_loop(mode_type):
    print(f">>> 正在启动 {mode_type} 模式...")
    
    # Mac 修复：强制使用默认后端
    cap = cv2.VideoCapture(0)
    
    hud = CyberHUD()
    adapter = GameAdapter()
    
    if mode_type == "HAND":
        detector = HandController(detection_confidence=0.7)
    else:
        detector = BodyController(detection_confidence=0.7)

    print(">>> 摄像头已启动，请务必点击一下浏览器窗口以激活游戏！")
    print(">>> 按 ESC 键退出程序")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头")
            break

        frame = cv2.flip(frame, 1)

        # 1. 算法识别
        action, _, data = detector.process(frame, draw=False)

        # 2. 执行操作
        adapter.execute(action)

        # 3. 绘制 UI
        frame = hud.draw_interface(frame, action_text=action, hand_center=data)

        # 4. 显示画面
        # 为了方便演示，我们把窗口稍微缩小一点，放在左上角
        cv2.imshow('AirRunner - Camera View', frame)

        # 按 ESC 退出
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    cv2.waitKey(1)
    os._exit(0)


# =========================================
# 🖥️ 启动器界面 (带游戏选择功能)
# =========================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.selected_mode = None 
        self.target_url = None # 用来存选中的游戏网址

        self.title("AirRunner - 体感游戏中心")
        self.geometry("960x640") # 稍微变大一点
        self.resizable(True, True)
        self._center_window(960, 640)

        # --- 布局配置 ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. 左侧侧边栏
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # LOGO
        ctk.CTkLabel(self.sidebar, text="AIR RUNNER", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=20, pady=(40, 10))
        ctk.CTkLabel(self.sidebar, text="v2.0 Game Center", text_color="gray").grid(row=1, column=0, padx=20, pady=10)

        # 2. 右侧主内容区
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew")

        # --- 标题 ---
        ctk.CTkLabel(self.main_area, text="请配置游戏环境", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(40, 20))

        # --- ⭐ 新增：游戏选择下拉框 ---
        self.game_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.game_frame.pack(pady=10)
        
        ctk.CTkLabel(self.game_frame, text="第一步：选择要玩的游戏", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=40, pady=(0, 5))
        
        # 下拉菜单
        self.game_selector = ctk.CTkComboBox(
            self.game_frame, 
            values=list(GAME_URLS.keys()), # 自动读取游戏列表
            width=400,
            height=40,
            font=ctk.CTkFont(size=16)
        )
        self.game_selector.set("地铁跑酷 (Subway Surfers)") # 默认选这个
        self.game_selector.pack(padx=40)


        # --- 模式选择 ---
        ctk.CTkLabel(self.main_area, text="第二步：选择控制模式", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=85, pady=(30, 5))

        # 手势卡片
        self.card_hand = ctk.CTkFrame(self.main_area, height=120, fg_color=("#3B8ED0", "#1F6AA5"))
        self.card_hand.pack(fill="x", padx=80, pady=10)
        ctk.CTkLabel(self.card_hand, text="🖐 桌面手势模式", font=ctk.CTkFont(size=20, weight="bold"), text_color="white").pack(anchor="w", padx=20, pady=(15, 0))
        self.btn_hand = ctk.CTkButton(self.card_hand, text="启动 >", fg_color="white", text_color="#1F6AA5", width=100,
                                      command=self.select_hand_mode)
        self.btn_hand.pack(anchor="e", padx=20, pady=10)

        # 全身卡片
        self.card_body = ctk.CTkFrame(self.main_area, height=120, fg_color=("#2CC985", "#2FA572"))
        self.card_body.pack(fill="x", padx=80, pady=10)
        ctk.CTkLabel(self.card_body, text="🏃 全身运动模式", font=ctk.CTkFont(size=20, weight="bold"), text_color="white").pack(anchor="w", padx=20, pady=(15, 0))
        self.btn_body = ctk.CTkButton(self.card_body, text="启动 >", fg_color="white", text_color="#2FA572", width=100,
                                      command=self.select_body_mode)
        self.btn_body.pack(anchor="e", padx=20, pady=10)

    def _center_window(self, w, h):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - w) // 2
        y = (screen_height - h) // 2
        self.geometry(f'{w}x{h}+{x}+{y}')

    def get_selected_game_url(self):
        # 获取下拉框当前选中的文字
        game_name = self.game_selector.get()
        return GAME_URLS.get(game_name)

    def select_hand_mode(self):
        self.selected_mode = "HAND"
        self.target_url = self.get_selected_game_url()
        self.quit()

    def select_body_mode(self):
        self.selected_mode = "BODY"
        self.target_url = self.get_selected_game_url()
        self.quit()

if __name__ == "__main__":
    app = App()
    app.mainloop()
    
    # --- 界面关闭后执行 ---
    if app.selected_mode:
        # 1. 自动打开浏览器
        if app.target_url:
            print(f">>> 正在打开游戏网页: {app.target_url}")
            webbrowser.open(app.target_url)
        
        # 2. 启动摄像头
        run_game_loop(app.selected_mode)