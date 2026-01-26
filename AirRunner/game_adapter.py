import pyautogui
import time

class GameAdapter:
    def __init__(self, cooldown=0.4):
        self.last_action_time = 0
        self.cooldown = cooldown
        
        # Mac 的按键映射
        self.key_map = {
            "JUMP": 'up',      # 上箭头
            "DUCK": 'down',    # 下箭头
            "LEFT": 'left',    # 左箭头
            "RIGHT": 'right',  # 右箭头
            "PAUSE": 'esc'
        }
        # 增加一点安全性，鼠标甩到屏幕角落会强制停止
        pyautogui.FAILSAFE = True 

    def execute(self, action):
        current_time = time.time()

        # 1. 过滤无效动作
        if action == "NEUTRAL" or action == "NO_HAND":
            return

        # 2. 冷却时间检查
        if current_time - self.last_action_time < self.cooldown:
            return

        # 3. 执行按键
        if action in self.key_map:
            key = self.key_map[action]
            print(f">>> [Mac操作] 按下: {key}")
            
            # 真的按下去！
            pyautogui.press(key)
            
            self.last_action_time = current_time