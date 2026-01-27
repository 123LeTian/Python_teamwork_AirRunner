import sys
import time


def _load_input_backend():
    if sys.platform.startswith("win"):
        try:
            import pydirectinput as input_lib
            return input_lib, "pydirectinput"
        except Exception:
            import pyautogui as input_lib
            return input_lib, "pyautogui"

    import pyautogui as input_lib
    return input_lib, "pyautogui"


class GameAdapter:
    KEY_MAPS = {
        "arrows": {
            "JUMP": "up",
            "DUCK": "down",
            "LEFT": "left",
            "RIGHT": "right",
            "PAUSE": "esc",
        },
        "wasd": {
            "JUMP": "w",
            "DUCK": "s",
            "LEFT": "a",
            "RIGHT": "d",
            "PAUSE": "esc",
        },
    }

    def __init__(self, cooldown=0.15, profile="arrows"):  # 默认使用方向键映射，可更改为wasd映射
        self.last_action_time = 0
        self.cooldown = cooldown
        self.last_action = "NEUTRAL"
        self.input_lib, self.backend = _load_input_backend()
        self.set_profile(profile)
        #增加一点安全性，鼠标甩到屏幕角落会强制停止
        if hasattr(self.input_lib, "FAILSAFE"):
            self.input_lib.FAILSAFE = True 

    def set_profile(self, profile):
        if profile not in self.KEY_MAPS:
            raise ValueError(f"Unknown key profile: {profile}")
        self.key_map = self.KEY_MAPS[profile]

    def press_key(self, key):
        self.input_lib.press(key)

    def execute(self, action):
        current_time = time.time()

        # 1.过滤无效动作
        if action == "NEUTRAL" or action == "NO_HAND":
            self.last_action = "NEUTRAL"
            return

        #必须回到中立后才允许下一次触发
        if self.last_action != "NEUTRAL":
            return

        # 2.冷却时间检查
        if current_time - self.last_action_time < self.cooldown:
            return

        # 3.执行按键
        if action in self.key_map:
            key = self.key_map[action]
            print(f">>> [{self.backend}] press: {key}")
            
            #真的按下去！
            self.input_lib.press(key)
            
            self.last_action_time = current_time
            self.last_action = action
