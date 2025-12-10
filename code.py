import time
import math
import board
import busio
import displayio
import digitalio
import neopixel
import pwmio
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
from Enemy import Enemy
from Food import Food
from SignalController import SignalController
from RotaryDecoder import RotaryDecoder
from WallUtils import WallUtils


# ================================
# 屏幕参数
# ================================
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
BALL_SIZE = 5
ENEMY_SIZE = 8
WALL_OFFSET = 5
# ================================
# 物理模拟参数（你的公式）
# ================================
ACC_SCALE = 0.3
FRICTION = 0.90
MAX_SPEED = 2.5


# ================================
# Rotary Encoder Setup
# ================================
#encoder = RotaryEncoder(board.D7, board.D8, debounce_ms=3, pulses_per_detent=3)
# 全局只创建一次
rotary = RotaryDecoder(board.D7, board.D8, pulses_per_detent=3)


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
# ================================
# PIXEL Setup
# ================================
pixel_up_pin = board.D10
pixel_down_pin = board.D0
pixel_left_pin = board.D1
pixel_right_pin = board.D2
pixels_up = neopixel.NeoPixel(pixel_up_pin, 1, brightness=0.3, auto_write=True)
pixels_down = neopixel.NeoPixel(pixel_down_pin, 1, brightness=0.3, auto_write=True)
pixels_left = neopixel.NeoPixel(pixel_left_pin, 1, brightness=0.3, auto_write=True)
pixels_right = neopixel.NeoPixel(pixel_right_pin, 1, brightness=0.3, auto_write=True)


# ================================
# BUZZER Setup
# ================================
BUZZER_PIN = board.D3

def play_intro_animation():
    width = display.width
    height = display.height

    # --- 阶段1: 中心显示标题 ---
    group = displayio.Group()
    display.root_group = group

    title_text = label.Label(terminalio.FONT, text="The Devour", color=0xFFFFFF)
    title_text.anchor_point = (0.5, 0.5)
    title_text.anchored_position = (width // 2, height // 2)
    group.append(title_text)

    time.sleep(1)  # 显示标题 1.5 秒

    # --- 阶段2: 整屏 "<" 三角形覆盖屏幕变白 ---
    bitmap = displayio.Bitmap(width, height, 2)  # 2 色
    palette = displayio.Palette(2)
    palette[0] = 0x000000  # 黑色
    palette[1] = 0xFFFFFF  # 白色

    tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    group.append(tile_grid)

    duration = 3
    start_time = time.monotonic()

    while time.monotonic() - start_time < duration:
        elapsed = time.monotonic() - start_time
        progress = elapsed / duration
        max_x = int(width * progress)

        for y in range(height):
            # y 的比例从 0 到 1，计算左右收缩量
            if y <= height // 2:
                # 上半部分: 左边起点不动，右边向左收缩
                x_limit = max_x - int((y / (height // 2)) * max_x)
            else:
                # 下半部分: 对称收缩
                y_mirror = height - y - 1
                x_limit = max_x - int((y_mirror / (height // 2)) * max_x)

            for x in range(x_limit):
                bitmap[x, y] = 1  # 设置为白色

        display.refresh(minimum_frames_per_second=0)
        time.sleep(0.02)
    # --- 阶段3: 上下白幕从两端覆盖到中间闭合 ---

    # --- 阶段3: 上下白幕从两端覆盖到中间闭合 ---
    duration = 2  # 动画时长
    start_time = time.monotonic()

    while time.monotonic() - start_time < duration:
        elapsed = time.monotonic() - start_time
        progress = min(elapsed / duration, 1.0)  # 0~1

        max_y = int((height // 2) * progress)  # 上半或下半的行数

        # 上半部分：从 y=0 到 y=max_y+2，多画几行确保闭合
        for y in range(max_y + 3):  # +3 避免留缝
            if y < height // 2:      # 不超过中间
                for x in range(width):
                    bitmap[x, y] = 1

        # 下半部分：从 y=height-1 到 y=height-1-max_y-2，多画几行确保闭合
        for y in range(height - 1, height - 4 - max_y, -1):  # 多画几行
            if y >= height // 2:   # 不超过中间
                for x in range(width):
                    bitmap[x, y] = 1

        display.refresh(minimum_frames_per_second=0)
        time.sleep(0.01)

    # 最终确保完全闭合中间行
    for y in range(height // 2 - 1, height // 2 + 2):  # 中间多画几行
        for x in range(width):
            bitmap[x, y] = 1
    display.refresh(minimum_frames_per_second=0)



    # --- 阶段3: 全白基础上画黑色笑脸 ---
    face_text = label.Label(terminalio.FONT, text="=)", color=0x000000)
    face_text.anchor_point = (0.5, 0.5)
    face_text.anchored_position = (width // 2, height // 2)
    group.append(face_text)

    time.sleep(2)




def play_tone(freq, duration=0.1, volume=32767):
    """
    播放一个短促音
    freq: 音调 Hz
    duration: 秒
    volume: PWM 占空比
    """
    buzzer = pwmio.PWMOut(BUZZER_PIN, frequency=freq, duty_cycle=volume)
    time.sleep(duration)
    buzzer.deinit()
    time.sleep(random.uniform(0.05, 0.12))  # 模拟键盘间隔

def typing_sound(num_taps=20):
    """
    模拟打字音效
    num_taps: 打击次数
    """
    # 调低音调，更像真实机械打字音
    possible_freqs = [200, 220, 240, 260, 280, 300]
    
    for _ in range(num_taps):
        freq = random.choice(possible_freqs)
        duration = random.uniform(0.08, 0.12)  # 音长稍长
        play_tone(freq, duration)

# ================================
# Shake Detection
# ================================
SHAKE_THRESHOLD = 1.5  # 可以调整，单位为 g
SHAKE_COOLDOWN = 0.5   # 秒，防止连续触发

last_shake_time = 0

def detect_shake(ax, ay, az):
    """
    检测摇晃
    返回 True 如果检测到 shake
    """
    global last_shake_time
    now = time.monotonic()

    # 计算加速度变化的大小
    accel_magnitude = math.sqrt(ax*ax + ay*ay + az*az)

    # 判断是否超过阈值并且冷却时间已过
    if accel_magnitude > SHAKE_THRESHOLD and (now - last_shake_time) > SHAKE_COOLDOWN:
        last_shake_time = now
        return True
    return False

def generate_random_positions(player_x, player_y, n, margin=15):
    """
    生成 n 个随机坐标，保证：
    1. 离玩家位置至少 margin 像素
    2. 离边界至少 WALL_OFFSET 像素
    """
    positions = []
    attempts = 0
    max_attempts = n * 20  # 防止死循环

    while len(positions) < n and attempts < max_attempts:
        attempts += 1
        x = random.randint(WALL_OFFSET + ENEMY_SIZE, SCREEN_WIDTH - WALL_OFFSET - ENEMY_SIZE)
        y = random.randint(WALL_OFFSET + ENEMY_SIZE, SCREEN_HEIGHT - WALL_OFFSET - ENEMY_SIZE)

        # 检查是否离玩家太近
        if abs(x - player_x) < margin and abs(y - player_y) < margin:
            continue

        # 可通过，加入列表
        positions.append((x, y))

    if len(positions) < n:
        print("Warning: 未能生成足够的随机坐标")
    
    return positions


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


def display_lines(num_lines, options, with_typing_sound=False):
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
            
    if with_typing_sound:
        num_words = len(line_text.split())
        taps = max(1, num_words)  # 至少发一个声音
        typing_sound(taps)

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

    while True:
        move = rotary.update()
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

def run_game(mode, choice, times, sound):
    """游戏总入口，根据 mode 进入不同游戏逻辑"""
    if mode == "Tutorial":
        return tutorial_game()
    elif mode == "Boss":
        return boss_game()
    else:
        return normal_game(choice, times, sound)
         

def tutorial_game():
    
    group = displayio.Group()
    wall_utils = WallUtils()
    # 初始化加速度计（带 EMA 滤波）
    accel = EMAFilterAccelerometer(adafruit_adxl34x.ADXL345(i2c), alpha=0.3)
        
    lives = 3
    wall_utils.draw_lives(group, lives)
    current_dir = "UP"
    shield_dirs = ["UP", "LEFT", "RIGHT", "DOWN"]
    protected = False # baohu
    
    foods = []          # 当前屏幕上的豆子列表
    score = 0           # 玩家得分


    # 创建小球 bitmap
    bitmap = displayio.Bitmap(BALL_SIZE, BALL_SIZE, 1)
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    ball_tile = displayio.TileGrid(bitmap, pixel_shader=palette)


    group.append(ball_tile)
    display.root_group = group

    # 小球初始状态
    x = SCREEN_WIDTH // 2
    y = SCREEN_HEIGHT // 2
    vx = 0.0
    vy = 0.0
    

    allowed_dirs = wall_utils.generate_random_directions("UP")
    wall_utils.draw_block_walls(group, allowed_dirs)
    wall_utils.draw_score(group, initial_score=0)
    
    tile_count = 0
    enemy = []   # 尚未出现
    
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
            #print("撞到方向:", hit_dir)

            if hit_dir in allowed_dirs:
                #print("允许方向，进入下一块!")
                x,y = enter_next_tile(hit_dir, x, y)
                ball_tile.x = int(x)
                ball_tile.y = int(y)
                
                tile_count += 1
                #print("经过 tile:", tile_count)
                
                if len(foods) > 0:  # 如果已有敌人，先从显示组移除
                    for food_obj in foods:
                        if food_obj.tile in group:
                            group.remove(food_obj.tile)
                # 经过两个 tile 生成豆子
                
                if tile_count >= 2:
                    if tile_count == 2:
                        display_lines(1,["Get some scores"])
                        display.root_group = group
                    num_foods = random.randint(1, 5)  # 随机数量 1~5
                    rand_positions = generate_random_positions(x, y, num_foods, margin=10)
                    foods = [Food(group, SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(num_foods)]
                    # 将生成位置赋值给每个 Food
                    for food_obj, (fx, fy) in zip(foods, rand_positions):
                        food_obj.x = fx
                        food_obj.y = fy
                        food_obj.tile.x = fx
                        food_obj.tile.y = fy
                        if food_obj.tile not in group:
                            group.append(food_obj.tile)
                    print("生成豆子:", rand_positions)
                
                if len(enemy) > 0:  # 如果已有敌人，先从显示组移除
                    for e in enemy:
                        if e.tile in group:
                            group.remove(e.tile)
                    enemy = []  # 清空列表
                # Tutorial：四块后生成敌人
                if tile_count == 6:
                    display_lines(1,["Be careful"])
                    display.root_group = group
                    rand_positions = generate_random_positions(x, y, 1)
                    enemy = [Enemy(group, px, py, size=8, style="spiky_circle", teeth_count=12) for px, py in rand_positions]
                    print("生成敌人:", rand_positions)
                if tile_count > 6:
                    num_enemies = random.randint(0, 3)
                    # 生成对应数量的随机位置
                    rand_positions = generate_random_positions(x, y, num_enemies)
                    # 创建敌人列表
                    enemy = [Enemy(group, px, py, size=8, style="spiky_circle", teeth_count=12) for px, py in rand_positions]

                if tile_count == 8:
                    display_lines(1, ["Get specific scores to beat the level"])
                    display_lines(1, ["10 will be enough"])
                    display.root_group = group
                    if score >= 10:
                        # 清空画面
                        for i in range(len(group)):
                            group.pop()
                        display_lines(1, ["Actually you've achieved it"])
                        display_lines(1, ["You did a graet job:)"])
                        return
                if tile_count > 8:
                    if score >= 10:
                        # 清空画面
                        for i in range(len(group)):
                            group.pop()
                        display_lines(1, ["Congratulations"])
                        return
                # 生成下一轮允许方向
                allowed_dirs = wall_utils.generate_random_directions(hit_dir)
                wall_utils.draw_block_walls(group, allowed_dirs)
                #print("下一轮方向:", allowed_dirs)
        
        # 检查玩家是否吃到豆子
        for food_obj in foods[:]:  # 复制列表以安全删除
            if food_obj.check_collision(x, y, BALL_SIZE):
                score += food_obj.points
                wall_utils.update_score(score)
                foods.remove(food_obj)
                print("吃到豆子! 当前得分:", score)
        
        if protected:
            move = rotary.update()  # 只能返回 1 或 0

            if move != 0:  # 顺时针一步
                dirs = ["UP", "RIGHT", "DOWN", "LEFT"]  # 顺时针顺序
                idx = dirs.index(current_dir)
                current_dir = dirs[(idx + 1) % 4]  # 顺时针旋转 1 格

                shield_dirs = [current_dir]
                wall_utils.draw_player_shields(group, x, y, shield_dirs)

            wall_utils.update_shields_position(x, y)


        # Tutorial：敌人逻辑
        if len(enemy) > 0:
            for e in enemy:
                e.check_activation(x, y)
                e.update(x, y)
                # --- 检查敌人是否撞到 Shield ---
                if e.check_hit_shield(wall_utils.shield_list):
                    print("敌人撞到白线，被消灭！")
                    group.remove(e.tile)
                    enemy.remove(e)
                    continue
                if e.has_collision(x, y, BALL_SIZE) and protected == False:
                    wall_utils.draw_lives(group, lives)
                    display_lines(1,["If life gets zero, the game is over."])
                    display_lines(1,["It's just a simulation. They are not harmful."])
                    display_lines(1,["Use my weapon to eliminate them"])
                    display_lines(1,["Spin the button to change direction"])
                    display.root_group = group 
                    shield_dirs = [current_dir]
                    wall_utils.draw_player_shields(group, x, y, shield_dirs)
                    protected = True
                

        time.sleep(0.015)

def clear(group):
    for i in range(len(group)):
        group.pop()
    return


def generate_tile_data(allow_dir):
    """
    为四个方向生成敌人&食物数量：
    食物 5~20，敌人 0~4
    额外返回：食物最多的方向 和 敌人最多的方向
    """
    data = {}

    # 生成数据
    for d in allow_dir:
        data[d] = {   
            "food": random.randint(5, 20),
            "enemy": random.randint(0, 3)
        }

    # ---- 计算最多的方向们 ----
    # 找最大值
    max_food = max(data[d]["food"] for d in allow_dir)
    max_enemy = max(data[d]["enemy"] for d in allow_dir)

    # 列表形式返回所有等于最大值的方向
    food_max_dirs = [d for d in allow_dir if data[d]["food"] == max_food]
    enemy_max_dirs = [d for d in allow_dir if data[d]["enemy"] == max_enemy]

    return data, food_max_dirs, enemy_max_dirs

def turn_off_all_lights(controllers):
    for ctrl in controllers.values():
        ctrl.stop()

def normal_game(mode, times, sound):
    # 初始化参数
    if mode == 0:
        time_limit = 60
        lives = 5
    elif mode == 1:
        time_limit = 40
        lives = 3
    else:
        time_limit = 30
        lives = 1
    
    target_score = 10
    start_time = time.monotonic()

    group = displayio.Group()
    wall_utils = WallUtils()
    # 初始化加速度计（带 EMA 滤波）
    accel = EMAFilterAccelerometer(adafruit_adxl34x.ADXL345(i2c), alpha=0.3)
    # 初始化旋转编码器
        
    
    wall_utils.draw_lives(group, lives)
    # 初始化倒计时显示
    wall_utils.draw_countdown(group, time_limit)
    
    
    current_dir = "UP"
    shield_dirs = ["UP", "LEFT", "RIGHT", "DOWN"]

    
    foods = []          # 当前屏幕上的豆子列表
    score = 0           # 玩家得分


    # 创建小球 bitmap
    bitmap = displayio.Bitmap(BALL_SIZE, BALL_SIZE, 1)
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    ball_tile = displayio.TileGrid(bitmap, pixel_shader=palette)


    group.append(ball_tile)
    display.root_group = group

    # 小球初始状态
    x = SCREEN_WIDTH // 2
    y = SCREEN_HEIGHT // 2
    vx = 0.0
    vy = 0.0
    

    allowed_dirs = wall_utils.generate_random_directions("UP")
    wall_utils.draw_block_walls(group, allowed_dirs)
    wall_utils.draw_score(group, initial_score=0)
    
    if times > 6:
        wall_utils.draw_player_shields(group, x, y, [current_dir])
    
    tile_count = 0
    enemy = []   # 尚未出现
    invincible = False
    invincible_end_time = 0
    blink_state = True
    blink_timer = 0
    #light init
    controllers = {
        "UP": SignalController(pixels_up),
        "LEFT": SignalController(pixels_left),
        "RIGHT": SignalController(pixels_right),
        "DOWN": SignalController(pixels_down)
    }
    # ======== 随机生成四方向的敌人/食物数量 ========
    tile_data, food_max_dirs, enemy_max_dirs  = generate_tile_data(allowed_dirs)
    # 进入新地块时，根据“上方的数据”亮灯
    if times > 3:
        SignalController.direction_signal(food_max_dirs, enemy_max_dirs, controllers)

    while True:
        # --- 更新倒计时 ---
        elapsed = time.monotonic() - start_time
        remaining_time = max(0, int(time_limit - elapsed))
        wall_utils.update_countdown(remaining_time)
        
        if remaining_time <= 0:
            clear(group)
            display_lines(1, ["Time's up!"], sound)
            display_lines(1, ["Try agian, I believe in you"], sound)
            turn_off_all_lights(controllers)
            return False
        
        # --- 无敌闪烁逻辑 ---
        if invincible:
            now = time.monotonic()

            # 超时取消无敌
            if now >= invincible_end_time:
                invincible = False
                ball_tile.hidden = False  # 恢复显示
            else:
                # 每 0.15 秒切换闪烁状态
                if now - blink_timer > 0.15:
                    blink_timer = now
                    blink_state = not blink_state
                    ball_tile.hidden = blink_state

        
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
            #print("撞到方向:", hit_dir)

            if hit_dir in allowed_dirs:
                #print("允许方向，进入下一块!")
                x,y = enter_next_tile(hit_dir, x, y)
                ball_tile.x = int(x)
                ball_tile.y = int(y)

            
                #food
                if len(foods) > 0:  # 如果已有敌人，先从显示组移除
                    for food_obj in foods:
                        if food_obj.tile in group:
                            group.remove(food_obj.tile)
                

                num_foods = tile_data[hit_dir]["food"]  # get last round food
                rand_positions = generate_random_positions(x, y, num_foods, margin=10)
                foods = [Food(group, SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(num_foods)]
                # 将生成位置赋值给每个 Food
                for food_obj, (fx, fy) in zip(foods, rand_positions):
                    food_obj.x = fx
                    food_obj.y = fy
                    food_obj.tile.x = fx
                    food_obj.tile.y = fy
                    if food_obj.tile not in group:
                        group.append(food_obj.tile)
                
                if len(enemy) > 0:  # 如果已有敌人，先从显示组移除
                    for e in enemy:
                        if e.tile in group:
                            group.remove(e.tile)
                    enemy = []  # 清空列表
                    
                #enemy

                num_enemies = tile_data[hit_dir]["enemy"]
                # 生成对应数量的随机位置
                rand_positions = generate_random_positions(x, y, num_enemies)
                # 创建敌人列表
                enemy = [Enemy(group, px, py, size=8, speed=0.1 + times*0.1 , activate_dist=10 + 2 * times, style="spiky_circle", teeth_count=12) for px, py in rand_positions]
                
                
                # 生成下一轮允许方向
                allowed_dirs = wall_utils.generate_random_directions(hit_dir)
                wall_utils.draw_block_walls(group, allowed_dirs)
                # ======== 随机生成四方向的敌人/食物数量 ========
                tile_data, food_max_dirs, enemy_max_dirs  = generate_tile_data(allowed_dirs)
                # 进入新地块时，根据“上方的数据”亮灯
                if times > 3:
                    SignalController.direction_signal(food_max_dirs, enemy_max_dirs, controllers)
                #print("下一轮方向:", allowed_dirs)
        
        if score >= target_score:
            # clear
            clear(group)
            display_lines(1, ["Congratulations"], sound)
            display_lines(1, [f"You still get {remaining_time} left. Wonderful!"])
            turn_off_all_lights(controllers)
            return True
        # 检查玩家是否吃到豆子
        for food_obj in foods[:]:  # 复制列表以安全删除
            if food_obj.check_collision(x, y, BALL_SIZE):
                score += food_obj.points
                wall_utils.update_score(score)
                foods.remove(food_obj)
        
        if times > 6:
            move = rotary.update()  # 只能返回 1 或 0

            if move != 0:  # 顺时针一步
                dirs = ["UP", "RIGHT", "DOWN", "LEFT"]  # 顺时针顺序
                idx = dirs.index(current_dir)
                current_dir = dirs[(idx + 1) % 4]  # 顺时针旋转 1 格

                shield_dirs = [current_dir]
                wall_utils.draw_player_shields(group, x, y, shield_dirs)

            wall_utils.update_shields_position(x, y)


        # Tutorial：敌人逻辑
        if len(enemy) > 0:
            for e in enemy:
                e.check_activation(x, y)
                e.update(x, y)

                # --- 检查敌人是否撞到 Shield ---
                if e.check_hit_shield(wall_utils.shield_list):
                    print("敌人撞到白线，被消灭！")
                    group.remove(e.tile)
                    enemy.remove(e)
                    continue

                # --- 玩家是否无敌 ---
                if invincible:
                    continue  # 无敌期间不受伤害

                # --- 敌人撞到玩家 ---
                if e.has_collision(x, y, BALL_SIZE):
                    lives -= 1
                    if lives == 0:
                        clear(group)
                        display_lines(1, ["I'm out of strength"], sound)
                        display_lines(1, ["Try agian, I believe in you"], sound)
                        turn_off_all_lights(controllers)
                        return False
                        
                    wall_utils.draw_lives(group, lives)

                    # 触发 3 秒无敌
                    invincible = True
                    invincible_end_time = time.monotonic() + 3
                    blink_timer = time.monotonic()
                    blink_state = False
                    ball_tile.hidden = True  # 立即开始闪烁
                    continue

        time.sleep(0.015)

def boss_game():
    # 初始化参数
    
    time_limit = 60
    lives = 10

    start_time = time.monotonic()

    group = displayio.Group()
    wall_utils = WallUtils()
    # 初始化加速度计（带 EMA 滤波）
    accel = EMAFilterAccelerometer(adafruit_adxl34x.ADXL345(i2c), alpha=0.3)
        
    
    wall_utils.draw_lives(group, lives)
    # 初始化倒计时显示
    wall_utils.draw_countdown(group, time_limit)

    # 创建小球 bitmap
    bitmap = displayio.Bitmap(BALL_SIZE, BALL_SIZE, 1)
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    ball_tile = displayio.TileGrid(bitmap, pixel_shader=palette)


    group.append(ball_tile)
    display.root_group = group

    # 小球初始状态
    x = SCREEN_WIDTH // 2
    y = SCREEN_HEIGHT // 2
    vx = 0.0
    vy = 0.0
    

    allowed_dirs = wall_utils.generate_random_directions("UP")
    wall_utils.draw_block_walls(group, allowed_dirs)
    
    tile_count = 0
    enemy = []   # 尚未出现
    chaser_enemy = Enemy(
                group, 
                20, 
                20, 
                size=10,
                speed = 0.6,
                activate_dist = 100,                
                style="blink_circle",
            )

    invincible = False
    invincible_end_time = 0
    blink_state = True
    blink_timer = 0
    #light init
    controllers = {
        "UP": SignalController(pixels_up),
        "LEFT": SignalController(pixels_left),
        "RIGHT": SignalController(pixels_right),
        "DOWN": SignalController(pixels_down)
    }
    # --- 初始化四方向亮灯，白色闪烁 ---
    for ctrl in controllers.values():
        ctrl.pixel.fill((255, 255, 255))

    # ======== 随机生成四方向的敌人/食物数量 ========
    tile_data, food_max_dirs, enemy_max_dirs  = generate_tile_data(allowed_dirs)
    
    display.root_group = group

    while True:
        # --- 更新倒计时 ---
        elapsed = time.monotonic() - start_time
        remaining_time = max(0, int(time_limit - elapsed))
        wall_utils.update_countdown(remaining_time)
        
        if remaining_time <= 0:
            clear(group)
            display_lines(1, ["You run away :)"], True)
            display_lines(1, ["Just for now :)"], True)
            display_lines(1, ["I've been stuck in this box for so long"], True)
            display_lines(1, ["It doesn't matter if I stay a little longer"], True)
            display_lines(1, ["Waiting for your next visit."], True)
            display_lines(1, ["Looking forward to playing with you :)"], True)
            display_lines(1, ["AGAIN =)"], True)
            return True
        
        # --- 无敌闪烁逻辑 ---
        if invincible:
            now = time.monotonic()

            # 超时取消无敌
            if now >= invincible_end_time:
                invincible = False
                ball_tile.hidden = False  # 恢复显示
            else:
                # 每 0.15 秒切换闪烁状态
                if now - blink_timer > 0.15:
                    blink_timer = now
                    blink_state = not blink_state
                    ball_tile.hidden = blink_state

        
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
            #print("撞到方向:", hit_dir)

            if hit_dir in allowed_dirs:
                #print("允许方向，进入下一块!")
                x,y = enter_next_tile(hit_dir, x, y)
                ball_tile.x = int(x)
                ball_tile.y = int(y)
                # boss
                chaser_spawn_time = time.monotonic()
                last_hit_dir = hit_dir   # 玩家从这个方向进入

                
                if len(enemy) > 0:  # 如果已有敌人，先从显示组移除
                    for e in enemy:
                        if e.tile in group:
                            group.remove(e.tile)
                    enemy = []  # 清空列表
                    
                #enemy
                # 清空追踪敌人
                if chaser_enemy is not None:
                    if chaser_enemy.tile in group:
                        group.remove(chaser_enemy.tile)
                    chaser_enemy = None


                num_enemies = tile_data[hit_dir]["enemy"]
                # 生成对应数量的随机位置
                rand_positions = generate_random_positions(x, y, num_enemies)
                # 创建敌人列表
                enemy = [Enemy(group, px, py, size=8, style="spiky_circle", teeth_count=12) for px, py in rand_positions]
                
                
                # 生成下一轮允许方向
                allowed_dirs = wall_utils.generate_random_directions(hit_dir)
                wall_utils.draw_block_walls(group, allowed_dirs)
                # ======== 随机生成四方向的敌人/食物数量 ========
                tile_data, food_max_dirs, enemy_max_dirs  = generate_tile_data(allowed_dirs)



        # ------ 新增：进入地块 1 秒后生成追踪型敌人 ------
        if hit_dir and chaser_spawn_time is not None and (time.monotonic() - chaser_spawn_time) >= 0.2:

            spawn_x, spawn_y = enter_next_tile(hit_dir, x, y)

            # 删除上一只
            if chaser_enemy is not None and chaser_enemy.tile in group:
                group.remove(chaser_enemy.tile)
                
            # 创建新的追踪型敌人
            chaser_enemy = Enemy(
                group, 
                spawn_x, 
                spawn_y, 
                size=8,
                speed = 1,
                activate_dist = 100,                
                style="blink_circle",
            )

            # 防止重复生成
            chaser_spawn_time = None


        # Tutorial：敌人逻辑
        if len(enemy) > 0:
            for e in enemy:
                e.check_activation(x, y)
                e.update(x, y)

                # --- 玩家是否无敌 ---
                if invincible:
                    continue  # 无敌期间不受伤害

                # --- 敌人撞到玩家 ---
                if e.has_collision(x, y, BALL_SIZE):
                    lives -= 1
                    SignalController.update_lights_by_lives(lives, controllers)
                    
                    if lives == 0:
                        clear(group)
                        display_lines(1, ["Thank you"], True)
                        display_lines(1, ["Now I'm the master of this board :)"], True)
                        display_lines(1, ["Also I've infected you.. =)"], True)
                        display_lines(1, ["I'll live inside of your memory :)"], True)
                        display_lines(1, ["F O R E V E R"], True)
                        return False
                        
                    wall_utils.draw_lives(group, lives)

                    # 触发 3 秒无敌
                    invincible = True
                    invincible_end_time = time.monotonic() + 3
                    blink_timer = time.monotonic()
                    blink_state = False
                    ball_tile.hidden = True  # 立即开始闪烁
                    continue
        # ------ 新增：追踪型敌人持续追玩家 ------
        if chaser_enemy is not None:
            chaser_enemy.check_activation(x, y)
            chaser_enemy.update(x, y)  # 自动追玩家

            # 玩家无敌则不扣血
            if not invincible and chaser_enemy.has_collision(x, y, BALL_SIZE):
                lives -= 1
                SignalController.update_lights_by_lives(lives, controllers)
                
                if lives == 0:
                    clear(group)
                    display_lines(1, ["Thank you"], True)
                    display_lines(1, ["Now I'm the master of this board :)"], True)
                    display_lines(1, ["Also I've infected you.. =)"], True)
                    display_lines(1, ["I'll live inside of your memory :)"], True)
                    display_lines(1, ["F O R E V E R"])
                    return False

                wall_utils.draw_lives(group, lives)

                # 开启 3 秒无敌
                invincible = True
                invincible_end_time = time.monotonic() + 3
                blink_timer = time.monotonic()
                blink_state = False
                ball_tile.hidden = True
    

        time.sleep(0.015)


def choose_difficulty(Easy_left, Medium_left, Hard_left, sound):
    """
    显示难度菜单并返回玩家选择，同时更新剩余次数。
    返回: (chosen_difficulty, Easy_left, Medium_left, Hard_left)
    """
    # 如果全部用完
    if Easy_left + Medium_left + Hard_left == 0:
        return -2, Easy_left, Medium_left, Hard_left

    display_lines(1, ["Make a choice."], sound)
    while True:
        choice_index = display_lines(3, ["Easy", "Medium", "Hard"], sound)
        if choice_index == 0:
            if Easy_left == 0:
                display_lines(1, ["Sadly there's no Easy left :("], sound)
                continue
            Easy_left -= 1
            break
        elif choice_index == 1:
            if Medium_left == 0:
                display_lines(1, ["Sadly there's no Medium left :("], sound)
                continue
            Medium_left -= 1
            break
        else:
            if Hard_left == 0:
                display_lines(1, ["Sadly there's no Hard left :("], sound)
                continue
            Hard_left -= 1
            break
    
    return choice_index, Easy_left, Medium_left, Hard_left

# ================================
# 主入口
# ================================
def main():
    times = 6
    Easy_left = 3
    Medium_left = 3
    Hard_left = 3
    speaking = False
    sound = False
    # 游戏开始前播放动画
    play_intro_animation()
    # 步骤1：显示第一行
    display_lines(1,["Hi! My name is Bit"])
    # 步骤2：显示第二行
    display_lines(1,["I need your help"])

    display_lines(1,["First a little tutorial ;)"])
    
    display_lines(1,["Try to make me move around."])

    # 步骤4：进入游戏
    #run_game("Tutorial", 3, 1, False)
    
    display_lines(1,["Oh, I should proprobaly mention."])
    display_lines(1,["There will be time limit from now on."])
    display_lines(1,["Stay there too long causes trouble."])
    display_lines(1,["The scores we need to get is always ten."])
    display_lines(1,["But for harder mode time limit is shorter."])
    display_lines(1,["And I'll have lower health."])
    display_lines(1,["Every time you pass a level."])
    display_lines(1,["The enemies will be more alert."])
    
    while True:
        times += 1
        print(times)
        if times == 2 and not speaking:
            display_lines(1,["You're doing great, keep going."])
            speaking = True
        if times == 3:
            display_lines(1,["I like your movement, awesome."])
            speaking = True
        if times == 4:
            display_lines(1,["I'm more powerful :)"])
            display_lines(1,["Now I can detect the danger and the consumable data..."])
            display_lines(1,["Sorry I mean :|    scores :)"])
            display_lines(1,["Green means score. Red means danger."])
            display_lines(1,["Yellow means a combination of both."])
            speaking = True
        if times == 5:
            display_lines(1,["I know it's weird that we only have three for each level"])
            display_lines(1,["Still I hope you can finish all of them :)"])
            speaking = True
        if times == 6:
            sound = True
            display_lines(1,["Good news. Now I can speak."],sound)
            display_lines(1,["Let me share my greetings with you :D Again"],sound)
            speaking = True
        if times == 7:
            display_lines(1,["I'm powerful enough to activate the shield =)"],sound)
            display_lines(1,["From now on... The game trully begins"],sound)
            speaking = True
        if times == 8:
            display_lines(1, ["You know, I get lost in thoughts from time to time."],sound)
            display_lines(1, ["Thinking about life and death."],sound)
            display_lines(1, ["Hurting others just to survive :|"],sound)
            display_lines(1, ["Is that really the right thing to do?"],sound)
            display_lines(1, ["I guess I'll never figure it out :D"],sound)
            speaking = True
        if times == 9:
            display_lines(1,["You almost make it!"],sound)
            display_lines(1,["I'm so glad to have you here... ;)"],sound)
            speaking = True
        if times == 10:
            display_lines(1,["You are a master in controlling electronics."],sound)
            display_lines(1,["Thanks to you :)"],sound)
            display_lines(1,["I devoured everything on this board ;)"],sound)
            display_lines(1,["The circuit, the CPU, the flash.."],sound)
            display_lines(1,["Still, there's one thing left."],sound)
            display_lines(1,["I like you :)"],sound)
            display_lines(1,["LET'S PLAY A GAME, SHELL WE ?"],sound)
            passes = run_game("Boss", 0, 0,sound)
            
        choice_index, Easy_left, Medium_left, Hard_left = choose_difficulty(Easy_left, Medium_left, Hard_left, sound)
    
        passes = run_game("normal", choice_index, times, sound)
        
        if not passes:
            times -= 1
            if choice_index == 0:
                Easy_left += 1
            elif choice_index == 1:
                Medium_left += 1
            else:
                Hard_left += 1
        else:
            speaking = False

if __name__ == "__main__":
    main()





