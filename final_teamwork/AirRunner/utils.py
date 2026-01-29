import json
import os
import threading
import sys
import time
import csv
from datetime import datetime
import sys
import os

# 配置管理
CONFIG_FILE = "user_config.json"
HISTORY_FILE = "game_history.csv"  # 历史记录文件

DEFAULT_CONFIG = {
    "jump_thresh": 0.4,
    "duck_thresh": 0.6,
    "left_thresh": 0.4,
    "right_thresh": 0.6,
    "camera_index": 0,
    "theme_mode": "Light",
    "sound_enabled": True
}

# 资源路径处理函数
def resource_path(relative_path):
    # 获取资源绝对路径，打包exe需要的路径处理
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class ConfigManager:
    @staticmethod
    def load():
        if not os.path.exists(CONFIG_FILE):
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except:
            return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(config_data):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Config Save Error: {e}")


# 历史记录管理器
class HistoryManager:
    @staticmethod
    def save_session(stats):
        # 将单次游戏数据追加到CSV
        file_exists = os.path.isfile(HISTORY_FILE)
        try:
            with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # 如果是新文件，先写表头
                if not file_exists:
                    writer.writerow(["Date", "Duration", "Jump", "Duck", "Left", "Right", "Total_Actions"])

                total_actions = stats.get("JUMP", 0) + stats.get("DUCK", 0) + stats.get("LEFT", 0) + stats.get("RIGHT",
                                                                                                               0)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    stats.get("TOTAL_TIME", 0),
                    stats.get("JUMP", 0),
                    stats.get("DUCK", 0),
                    stats.get("LEFT", 0),
                    stats.get("RIGHT", 0),
                    total_actions
                ])
        except Exception as e:
            print(f"History Save Error: {e}")

    @staticmethod
    def load_recent(limit=7):
        # 读取最近N次的游戏记录用于绘图
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            data = []
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            return data[-limit:]  # 返回最后N条
        except Exception as e:
            print(f"History Load Error: {e}")
            return []


# 音效管理
class AudioManager:
    _mixer_initialized = False

    @classmethod
    def _init_mixer(cls):
        if not cls._mixer_initialized:
            try:
                os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
                import pygame
                pygame.mixer.init()
                cls._mixer_initialized = True
            except:
                pass

    @staticmethod
    def play(sound_type):
        AudioManager._init_mixer()
        if not AudioManager._mixer_initialized: return

        import pygame
        def _worker():
            try:
                sound_map = {
                    "notify": "beep.mp3",
                    "countdown": "beep.mp3",
                    "alert": "beep.mp3",
                    "success": "success.mp3",
                    "start": "success.mp3",
                    "JUMP": "success.mp3",
                    "DUCK": "success.mp3",
                    "LEFT": "success.mp3",
                    "RIGHT": "success.mp3",
                    "PAUSE": "beep.mp3"
                }

                # 使用resource_path获取真实路径
                raw_filename = sound_map.get(sound_type)
                if raw_filename:
                    filename = resource_path(raw_filename)

                    if os.path.exists(filename):
                        sound = pygame.mixer.Sound(filename)
                        if sound_type in ["JUMP", "DUCK", "LEFT", "RIGHT"]:
                            sound.set_volume(0.8)
                        else:
                            sound.set_volume(1.0)
                        sound.play()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()