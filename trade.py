import numpy as np
import time
from pathlib import Path
import tkinter as tk
import win32api
import win32con
import keyboard
import cv2
import pytesseract
import dxcam
import random


THRESHOLD = (7422 - 3672) * 4 # 推荐为柱子间距乘以四
MAX_COUNT = 1
BUY_POS = (2188, 1223)
DETAIL_POS = (890, 302)
# ======================
# 配置
# ======================
pytesseract.pytesseract.tesseract_cmd = 'tesseract 文件目录'

"""
第 1 次: (174, 1243)
第 2 次: (1809, 1272)
"""

SCREEN_REGION_DX = (174, 1242, 1810, 1272)
SCREEN_CHECK_REGION_DX = (174, 1242, 358, 1275)

UPDATE_INTERVAL = 1  # ms
buy_count = 0
stop = False

# 初始化 DXCAM 实例 (全局初始化以保持高性能)
camera = dxcam.create(output_idx=0, output_color="RGB")

# ======================
# Win32 辅助函数
# ======================
def win32_click(x, y):
    """使用 Win32 API 模拟鼠标点击"""
    # 移动鼠标
    win32api.SetCursorPos((x, y))
    # 模拟按下和抬起
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    time.sleep(0.01)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    
    
# def win32_smooth_move(x2, y2, steps=20):
#     """
#     使用贝塞尔曲线平滑移动鼠标到目标点
#     """
#     x1, y1 = win32api.GetCursorPos()
    
#     # 随机生成一个控制点，使路径产生弧度
#     cx = (x1 + x2) / 2 + random.randint(-50, 50)
#     cy = (y1 + y2) / 2 + random.randint(-50, 50)
    
#     for i in range(steps + 1):
#         t = i / steps
#         # 二阶贝塞尔公式
#         curr_x = int((1-t)**2 * x1 + 2*(1-t)*t * cx + t**2 * x2)
#         curr_y = int((1-t)**2 * y1 + 2*(1-t)*t * cy + t**2 * y2)
        
#         win32api.SetCursorPos((curr_x, curr_y))
#         # 模拟移动中的微小时间间隔
#         time.sleep(random.uniform(0.001, 0.005))
    
# def win32_click_humanized(x, y):
#     """
#     带有平滑移动、随机偏移和随机延迟的点击
#     """
#     # 1. 目标坐标加入微小随机偏移 (±3像素)
#     target_x = x + random.randint(-3, 3)
#     target_y = y + random.randint(-3, 3)
    
#     # 2. 平滑移动到目标点
#     win32_smooth_move(target_x, target_y, steps=random.randint(15, 25))
    
#     # 3. 模拟按下前的迟疑 (10-30ms)
#     time.sleep(random.uniform(0.01, 0.03))
    
#     # 4. 按下鼠标
#     win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)
    
#     # 5. 随机按下时长 (模拟手指按压时间 40ms - 120ms)
#     time.sleep(random.uniform(0.04, 0.12))
    
#     # 6. 抬起鼠标
#     win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
    
#     # 7. 点击后的随机冷却
#     time.sleep(random.uniform(0.05, 0.1))

def win32_press_esc():
    """使用 Win32 API 模拟按下 ESC 键"""
    win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
    time.sleep(0.01)
    win32api.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)

def screenshot(region):
    """使用 DXCAM 获取截图"""
    # grab 会返回一个 numpy array (RGB)
    frame = camera.grab(region=region)
    if frame is None:
        # 如果当前帧获取失败（例如屏幕无变化），尝试获取最后一帧
        return camera.get_latest_frame()
    return frame


import cv2
import os
from datetime import datetime
def save_debug_image(img, prefix="debug"):
    """
    保存 dxcam 获取的 numpy 数组为本地图片
    """
    if img is None:
        print("保存失败：图像为空")
        return
    
    # 1. 创建调试文件夹
    if not os.path.exists("debug_images"):
        os.makedirs("debug_images")
    
    # 2. 颜色转换 (RGB -> BGR)
    # 这一步非常重要，否则颜色会反过来
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    # 3. 生成文件名（带时间戳防止覆盖）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"debug_images/{prefix}_{timestamp}.png"
    
    # 4. 保存图片
    cv2.imwrite(filename, img_bgr)
    print(f"调试图片已保存至: {filename}")


def run_ocr(img):
    """
    调用 ocr 脚本, 读取图片并返回识别结果
    优化策略: 灰度化 -> 放大 -> 二值化 -> 限制字符集
    """
    if img is None or img.size == 0:
        return "None"

    # 1. 转为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # 2. 放大图像 (Scale) - 屏幕文字通常较小，放大 2-3 倍能显著提高识别率
    scale_percent = 200 # 放大 200%
    width = int(gray.shape[1] * scale_percent / 100)
    height = int(gray.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized = cv2.resize(gray, dim, interpolation=cv2.INTER_CUBIC)

    # 3. 二值化 (Thresholding) - 区分黑白
    # 假设文字是亮色背景是暗色，或者反之。OTSU 算法会自动寻找最佳阈值
    # 如果背景很复杂，可能需要手动调节阈值，例如 cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY)
    _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 调试：如果有问题，取消下面注释查看处理后的图片
    # cv2.imshow("Debug OCR", thresh)
    # cv2.waitKey(1)

    # 4. 配置 Tesseract
    # --psm 6: 假设是一个统一的文本块 (适合多行数字)
    # digits: 限制只能识别数字 (但我们需要逗号，所以用白名单)
    # tessedit_char_whitelist: 只允许数字和逗号
    config = r'--psm 6 -c tessedit_char_whitelist=0123456789,'

    try:
        text = pytesseract.image_to_string(thresh, config=config)
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {e}")
        return "None"
    
def check_monotonousity(lst):
    return len(lst) >= 1 and all(x < y for x, y in zip(lst, lst[1:]))

class FloatingWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.attributes("-topmost", True)
        self.overrideredirect(True)  # 无边框
        self.geometry("+50+50")      # 屏幕位置
        self.label = tk.Label(self, text="", font=("Arial", 18), bg="yellow")
        self.label.pack()
        self.update_label()
        self.history = []
        self.buy = 0
        self.time = None
        

    def update_label(self):
        global buy_count
        text = f"按 q 键停止循环..., 目标差价 {THRESHOLD}, 剩余 {MAX_COUNT - buy_count} 次"
        try:
            time.sleep(0.15)
            img = camera.grab(region=SCREEN_REGION_DX)
            # save_debug_image(img, "frame")
            if img is not None:
                found = run_ocr(img)
                found = found.replace(",", "")
                lst = found.split(" ")
            else:
                lst = ["None"]
            if len(lst) == 8 and lst[0] != "None":
                win32_press_esc()
                time.sleep(0.05)
                win32_click(DETAIL_POS[0], DETAIL_POS[1])
                num_list = list(map(int, lst))
                assert (len(num_list) == 8)
                self.history.append(num_list)
                if len(self.history) > 10:
                    self.history.pop(0)
                if len(self.history) >= 4:
                    prev_list = self.history[-4]
                    if prev_list[0] - num_list[0] >= THRESHOLD and check_monotonousity(prev_list) and check_monotonousity(num_list):
                        time.sleep(0.3)
                        check_img = camera.grab(region=SCREEN_CHECK_REGION_DX)
                        check_found = run_ocr(check_img)
                        check_found = check_found.replace(",", "")
                        check_num = int(check_found)
                        if check_num == num_list[0]:
                            # win32api.SetCursorPos((BUY_POS[0], BUY_POS[1]))
                            win32_click(BUY_POS[0], BUY_POS[1])
                            buy_count += 1
                            print(f"BUY IT!")
                            buy_img = camera.grab()
                            save_debug_image(buy_img, "buy_confirmation")
                            with open('log.txt', 'a', encoding='utf-8') as f:
                                f.write(f"Success: {self.history}\n")
                            self.history.clear()
                        else:
                            self.history.pop(-1)
                text += f"\n{str(num_list)}"
            else:
                text += "\nNot found. Checking..."
                if self.time is None:
                    self.time = time.time()
                current_pos = win32api.GetCursorPos()
                elapsed_time = time.time() - self.time
                
                dx = abs(current_pos[0] - DETAIL_POS[0])
                dy = abs(current_pos[1] - DETAIL_POS[1])
                dx2 = abs(current_pos[0] - BUY_POS[0])
                dy2 = abs(current_pos[1] - BUY_POS[1])
                
                if (dx + dy == 0 or dx2 + dy2 == 0) and elapsed_time > 1:
                    win32_click(DETAIL_POS[0], DETAIL_POS[1])
                    self.time = None
        except Exception as e:
            with open('log.txt', 'a', encoding='utf-8') as f:
                f.write(f"Error: {str(e)}\n")
            text += f"\nError: {str(e)}"
            
            
        # 定时下一次更新
        self.label.config(text=text)
        global stop
        if stop:
            print("Stopping loop...")
            quit(0)
        elif buy_count >= MAX_COUNT:
            print("Max buy count reached, stopping...")
            quit(0)
        else:
            self.after(UPDATE_INTERVAL, self.update_label)



def on_key_event(e):
    if e.name == 'q':
        global stop
        stop = True

if __name__ == "__main__":
    # while True:
    keyboard.on_press(on_key_event)
    win = FloatingWindow()
    win.mainloop()
