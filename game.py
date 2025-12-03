import time
import math
import board
import busio
import displayio
import digitalio
import random
import terminalio
from adafruit_display_text import label
import i2cdisplaybus
import adafruit_displayio_ssd1306
import adafruit_adxl34x
from filter import EMAFilterAccelerometer
from rotary_filter import RotaryHandler
from rotary_encoder import RotaryEncoder
from adafruit_debouncer import Debouncer
from WallUtils import WallUtils

# ================================
# 屏幕参数
# ================================
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
BALL_SIZE = 5
WALL_OFFSET = 5
# ================================
# 物理模拟参数（你的公式）
# ================================
ACC_SCALE = 0.3
FRICTION = 0.90
MAX_SPEED = 3


# ================================
# Rotary Encoder Setup
# ================================
encoder = RotaryEncoder(board.D7, board.D8, debounce_ms=3, pulses_per_detent=3)

# ================================
# 按钮（使用 D9）
# ================================
pin = digitalio.DigitalInOut(board.D9)
pin.direction = digitalio.Direction.INPUT
pin.pull = digitalio.Pull.UP   # 按下 = False
button = Debouncer(pin)

# ================================
# OLED Setup
# ================================
displayio.release_displays()
i2c = busio.I2C(board.SCL, board.SDA)
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)


def check_direction_collision(x, y):
    """根据球的位置，判断是否撞到 UP / DOWN / LEFT / RIGHT 边界"""
    if y <= WALL_OFFSET:
        return "UP"
    if y >= SCREEN_HEIGHT - BALL_SIZE-WALL_OFFSET:
        return "DOWN"
    if x <= WALL_OFFSET:
        return "LEFT"
    if x >= SCREEN_WIDTH - BALL_SIZE-WALL_OFFSET:
        return "RIGHT"
    return None

def enter_next_tile(hit_dir, x, y):
    """根据撞击方向，把球从对面传送出来"""

    if hit_dir == "UP":
        y = SCREEN_HEIGHT - BALL_SIZE - WALL_OFFSET - BALL_SIZE/2

    elif hit_dir == "DOWN":
        y = WALL_OFFSET + BALL_SIZE/2

    elif hit_dir == "LEFT":
        x = SCREEN_WIDTH - BALL_SIZE - WALL_OFFSET - BALL_SIZE/2

    elif hit_dir == "RIGHT":
        x = WALL_OFFSET + BALL_SIZE/2
    
    return x, y


# ================================
# 菜单界面显示
# ================================
def split_text_to_lines(text, max_chars_per_line=16):
    """将长文字拆分为多行，每行不超过 max_chars_per_line 个字符"""
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + ' ' + word) <= max_chars_per_line:
            if current_line:
                current_line += ' ' + word
            else:
                current_line = word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def display_lines(num_lines, options):
    """
    显示菜单/对话选择
    num_lines: int, 显示几行
    options: list, 每行显示的内容

    返回: 选中的行号 (0-based)
    """
    group = displayio.Group()

    option_labels = []
    # 用于累加垂直位置
    y_start = 22
    line_height = 12
    current_y = y_start
    

    for i, text in enumerate(options):
        # 分行处理
        lines = split_text_to_lines(text, max_chars_per_line=16)
        for j, line_text in enumerate(lines):
            lbl = label.Label(
                terminalio.FONT,
                text=line_text,
                anchored_position=(64, current_y),
                anchor_point=(0.5, 0.5)
            )
            option_labels.append(lbl)
            group.append(lbl)
            current_y += line_height
        
        if num_lines == 1 and i == 0:
            arrow_label = label.Label(
                terminalio.FONT,
                text="v",
                anchored_position=(110, current_y),  # 位置你可以调整
                anchor_point=(0.5, 0.5)
            )
            group.append(arrow_label)

            arrow_last_toggle = time.monotonic()
            arrow_visible = True
            ARROW_BLINK_INTERVAL = 0.5  # 0.5秒闪烁一次


    display.root_group = group

    def refresh():
        for idx, lbl in enumerate(option_labels):
            if idx == selection:
                lbl.text = "> " + options[idx] + " <"
            else:
                lbl.text = "  " + options[idx] + "  "
    
    # 单行逻辑：只等待按钮确认
    if num_lines == 1:
        while True:
            now = time.monotonic()
            if now - arrow_last_toggle > ARROW_BLINK_INTERVAL:
                arrow_last_toggle = now
                arrow_visible = not arrow_visible
                arrow_label.text = "v" if arrow_visible else ""
            button.update()
            if button.fell:
                return 0
            time.sleep(0.01)

    # 多行逻辑：使用 rotary_update 过滤旋转
    selection = 0
    refresh()  # 初始化显示

    rotary = RotaryHandler(encoder)

    while True:
        move = rotary.update()
        print(move)
        if move != 0:
            selection = (selection + move) % num_lines
            refresh()

        # 按钮确认
        button.update()
        if button.fell:
            time.sleep(0.2)  # debounce
            return selection

        time.sleep(0.01)




# ================================
# 游戏主循环（使用你提供的物理公式）
# ================================
def run_game():
    # 初始化加速度计（带 EMA 滤波）
    accel = EMAFilterAccelerometer(adafruit_adxl34x.ADXL345(i2c), alpha=0.3)

    # 创建小球 bitmap
    bitmap = displayio.Bitmap(BALL_SIZE, BALL_SIZE, 1)
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    ball_tile = displayio.TileGrid(bitmap, pixel_shader=palette)

    group = displayio.Group()
    group.append(ball_tile)
    display.root_group = group

    # 小球初始状态
    x = SCREEN_WIDTH // 2
    y = SCREEN_HEIGHT // 2
    vx = 0.0
    vy = 0.0
    
    wall_utils = WallUtils()
    allowed_dirs = wall_utils.generate_random_directions("UP")
    wall_utils.draw_block_walls(group, allowed_dirs)
    
    while True:
        # --- 你的速度 & 位置更新逻辑 ---
        ax, ay, az = accel.read_filtered()
        vx += ax * ACC_SCALE
        vy -= ay * ACC_SCALE

        vx = max(-MAX_SPEED, min(MAX_SPEED, vx))
        vy = max(-MAX_SPEED, min(MAX_SPEED, vy))
        vx *= FRICTION
        vy *= FRICTION

        x += vx
        y += vy

        # 边界硬限制
        x = max(WALL_OFFSET, min(SCREEN_WIDTH - BALL_SIZE-WALL_OFFSET, x))
        y = max(WALL_OFFSET, min(SCREEN_HEIGHT - BALL_SIZE-WALL_OFFSET, y))

        # 更新球位置
        ball_tile.x = int(x)
        ball_tile.y = int(y)

        # --- 检测方向是否撞击 ---
        hit_dir = check_direction_collision(x, y)

        if hit_dir:
            print("撞到方向:", hit_dir)

            if hit_dir in allowed_dirs:
                print("允许方向，进入下一块!")
                x,y = enter_next_tile(hit_dir, x, y)
                ball_tile.x = int(x)
                ball_tile.y = int(y)

                # 生成下一轮允许方向
                allowed_dirs = wall_utils.generate_random_directions(hit_dir)
                wall_utils.draw_block_walls(group, allowed_dirs)
                print("下一轮方向:", allowed_dirs)
                

        time.sleep(0.015)


# ================================
# 主入口
# ================================
def main():
        # 步骤1：显示第一行
    display_lines(1,["Hi! My name is Bit"])
    # 步骤2：显示第二行
    display_lines(1,["I need your help"])
    
    display_lines(1,["Imagine a journey, what will it look like"])

    # 步骤3：选择难度
    difficulty = display_lines(3, ["Easy", "Medium", "Hard"])
    print("选中的难度:", difficulty)
    
    display_lines(1,["First a little tutorial ;)"])
    
    display_lines(1,["Try to make me move around"])

    # 步骤4：进入游戏
    run_game()

if __name__ == "__main__":
    main()