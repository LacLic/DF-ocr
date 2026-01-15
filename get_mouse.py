# 遗留代码，不想用 pynput 可以用 pywin32 重新写一份

from pynput import mouse

positions = []


def on_click(x, y, button, pressed):
    """q
    每次按下左键时记录坐标
    """
    if pressed and button == mouse.Button.left:
        positions.append((x, y))
        print(f"采集到第 {len(positions)} 次位置: ({x}, {y})")

        if len(positions) >= 2:
            print("采集完成：")
            print("第 1 次:", positions[0])
            print("第 2 次:", positions[1])
            # 返回 False 停止监听
            return False


if __name__ == "__main__":
    print("请用鼠标左键点击两次以采集位置...")

    with mouse.Listener(on_click=on_click) as listener:
        listener.join()
