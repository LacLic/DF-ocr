# DF-ocr

三角洲行动 交易行补货自动购买脚本 图像识别

## 环境

```shell
pip install numpy pywin32 dxcam pytesseract opencv-python
```

显示器分辨率为 2560x1440，帧率开无上限

## 简要介绍

挑选了一些性能比较好的库，丢给 AI 生成，随后修改代码

- dxcam: 直连显卡进行截图
- pywin32: 模拟鼠标/键盘
- pytesseract: 进行 ocr 数字识别（需额外下载 tesseract 软件）
- opencv-python: 图像增强，方便数字识别
- tkinter: 悬浮窗信息展示

代码进行过迭代，最终发现前二者库在相同功能的库中，运行效率最高

如需修改截图坐标、鼠标坐标等，请使用 ```get_mouse.py```

## 使用方式

修改代码中的 ```THRESHOLD``` 为差价，```MAX_COUNT``` 为需要购买的物品数，```BUY_POS``` 为购买的鼠标点击位置，```DETAIL_POS``` 为所物品所在位置，```pytesseract.pytesseract.tesseract_cmd``` 为 tesseract 文件目录

```shell
python trade.py # 需管理员模式
```
