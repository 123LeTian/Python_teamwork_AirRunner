# AirRunner

AirRunner 使用摄像头手势或动作转换为键盘输入，支持网页跑酷类游戏。
提供桌面手势模式与面部鼻尖模式。
通过将游戏交互与肢体伸展相结合，让用户在工作、学习间隙自然轻松地活动颈椎与手腕，缓解长期伏案带来的肌肉僵硬，同时收获游戏的乐趣。

## 功能特点
- 手势模式：单手“虚拟摇杆”控制上下左右。
- 面部模式：鼻尖位置映射为跳/蹲/左/右。
- HUD 叠加显示 FPS 与动作反馈。
- 键位映射支持方向键/ WASD（Windows 优先 pydirectinput）。

## 运行环境
- Python 3.9+
- 摄像头
- 依赖：mediapipe、opencv-python、customtkinter
- 输入后端：
  - Windows：pydirectinput（优先），pyautogui（其次）
  - macOS/Linux：pyautogui

## 安装依赖
```bash
pip install mediapipe opencv-python customtkinter pyautogui pydirectinput
```

## 运行
```bash
python main.py
```

## 操作说明
- ESC：退出程序（需先点击摄像头窗口）。

## 模式说明
### 手势模式
- 手移出中心安全区触发上下左右。
- 握拳触发 PAUSE（发送 ESC）。

### 面部（鼻尖）模式
- 鼻尖位置相对中心区（0.4~0.6）触发跳/蹲/左/右。

## 注意事项
- 启动后需点击浏览器窗口以获取键盘焦点。
- 摄像头窗口置顶显示，便于观察。
- 阈值与冷却时间在 `controllers.py`、`game_adapter.py` 中调整。

## 测试脚本
- `hand_algo.py`：手势模式本地测试（主程序不使用）。
- `body_algo.py`：面部模式本地测试（主程序不使用）。

## 文件说明
- `main.py`：启动器 UI 与主循环。
- `controllers.py`：手势/面部识别逻辑。
- `game_adapter.py`：动作到按键映射与输入后端。
- `ui_drawer.py`：HUD绘制。
