import sys
import time
import threading


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

    def __init__(self, cooldown=0.15, profile="arrows"):
        self.last_action_time = 0
        self.cooldown = cooldown
        self.last_action = "NEUTRAL"
        self.input_lib, self.backend = _load_input_backend()
        self.set_profile(profile)

        # 统计数据字典
        self.stats = {
            "JUMP": 0,
            "DUCK": 0,
            "LEFT": 0,
            "RIGHT": 0,
            "TOTAL_TIME": 0
        }
        self.start_time = time.time()

        # 针对 pyautogui 移除默认延迟
        if self.backend == "pyautogui":
            self.input_lib.PAUSE = 0

        # 安全设定
        if hasattr(self.input_lib, "FAILSAFE"):
            self.input_lib.FAILSAFE = True

    def set_profile(self, profile):
        if profile not in self.KEY_MAPS:
            raise ValueError(f"Unknown key profile: {profile}")
        self.key_map = self.KEY_MAPS[profile]

    def _press_worker(self, key):
        try:
            self.input_lib.press(key)
        except Exception as e:
            print(f"Key press error: {e}")

    def execute(self, action):
        current_time = time.time()

        # 1. 过滤
        if action == "NEUTRAL" or action == "NO_HAND":
            self.last_action = "NEUTRAL"
            return

        # 必须回到中立
        if self.last_action != "NEUTRAL":
            return

        # 2. 冷却
        if current_time - self.last_action_time < self.cooldown:
            return

        # 3. 执行
        if action in self.key_map:
            key = self.key_map[action]
            # print(f">>> [{self.backend}] Async Press: {key}")

            # 启动守护线程按键
            t = threading.Thread(target=self._press_worker, args=(key,))
            t.daemon = True
            t.start()

            # 记录统计数据
            if action in self.stats:
                self.stats[action] += 1

            self.last_action_time = current_time
            self.last_action = action

    # 获取统计结果
    def get_stats(self):
        duration = int(time.time() - self.start_time)
        self.stats["TOTAL_TIME"] = duration
        return self.stats