import os
import json
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
from rotary_encoder import RotaryEncoder
from adafruit_debouncer import Debouncer
from Enemy import Enemy
from Food import Food
from SignalController import SignalController
from RotaryDecoder import RotaryDecoder
from WallUtils import WallUtils


# ================================
# Screen parameters
# ================================
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
BALL_SIZE = 5
ENEMY_SIZE = 8
WALL_OFFSET = 5

# ================================
# Physics simulation parameters
# ================================
ACC_SCALE = 0.3
FRICTION = 0.90
MAX_SPEED = 2.5
BIT_FILE = "/bit.txt"
TIME_FILE = "time_survived.txt"

# ================================
# Rotary Encoder Setup
# ================================
rotary = RotaryDecoder(board.D7, board.D8, pulses_per_detent=3)

# ================================
# Button Setup (using D9)
# ================================
pin = digitalio.DigitalInOut(board.D9)
pin.direction = digitalio.Direction.INPUT
pin.pull = digitalio.Pull.UP
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

# ================================
# accelerometer Setup
# ================================
accel = EMAFilterAccelerometer(adafruit_adxl34x.ADXL345(i2c), alpha=0.3)

def play_intro_animation():
    width = display.width
    height = display.height

    # --- Stage 1: Display title in the center ---
    group = displayio.Group()
    display.root_group = group

    title_text = label.Label(terminalio.FONT, text="The Devour", color=0xFFFFFF)
    title_text.anchor_point = (0.5, 0.5)
    title_text.anchored_position = (width // 2, height // 2)
    group.append(title_text)
    time.sleep(1)

    # --- Stage 2: Fill screen with white "<" triangles ---
    bitmap = displayio.Bitmap(width, height, 2) 
    palette = displayio.Palette(2)
    palette[0] = 0x000000 
    palette[1] = 0xFFFFFF 

    tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    group.append(tile_grid)

    duration = 3
    start_time = time.monotonic()

    while time.monotonic() - start_time < duration:
        elapsed = time.monotonic() - start_time
        progress = elapsed / duration
        max_x = int(width * progress)

        for y in range(height):
            if y <= height // 2:
                x_limit = max_x - int((y / (height // 2)) * max_x)
            else:
                y_mirror = height - y - 1
                x_limit = max_x - int((y_mirror / (height // 2)) * max_x)

            for x in range(x_limit):
                bitmap[x, y] = 1  

        display.refresh(minimum_frames_per_second=0)
        time.sleep(0.02)
    # --- Stage 3: White curtains close from top and bottom ---
    duration = 2 
    start_time = time.monotonic()
    while time.monotonic() - start_time < duration:
        elapsed = time.monotonic() - start_time
        progress = min(elapsed / duration, 1.0)  # 0 - 1

        max_y = int((height // 2) * progress) 

        for y in range(max_y + 3): 
            if y < height // 2:   
                for x in range(width):
                    bitmap[x, y] = 1

        for y in range(height - 1, height - 4 - max_y, -1):
            if y >= height // 2: 
                for x in range(width):
                    bitmap[x, y] = 1

        display.refresh(minimum_frames_per_second=0)
        time.sleep(0.01)

    for y in range(height // 2 - 1, height // 2 + 2): 
        for x in range(width):
            bitmap[x, y] = 1
    display.refresh(minimum_frames_per_second=0)

    # --- Stage 4: Draw black smiley face on white background ---
    face_text = label.Label(terminalio.FONT, text="=)", color=0x000000)
    face_text.anchor_point = (0.5, 0.5)
    face_text.anchored_position = (width // 2, height // 2)
    group.append(face_text)

    time.sleep(2)




# ================================
# Game Data Management
# ================================
def load_game_data():
    """Load game data from bit.txt. Return default values if file doesn't exist."""
    default_data = {
        "times": -1,
        "easyleft": -1,
        "mediumleft": -1,
        "hardleft": -1,
        "success": -1
    }
    try:
        with open(BIT_FILE, "r") as f:
            data = json.load(f)
            # Fill missing fields with default values
            for key in default_data:
                if key not in data:
                    data[key] = default_data[key]
            return data
    except OSError:
        # File does not exist
        return default_data
    except Exception as e:
        print("read bit.txt error:", e)
        return default_data


def save_game_data(times, easyleft, mediumleft, hardleft, success):
    """Save current game data to bit.txt (overwrite file)."""
    data = {
        "times": times,
        "easyleft": easyleft,
        "mediumleft": mediumleft,
        "hardleft": hardleft,
        "success": success
    }

    # Remove existing file if it exists
    try:
        os.remove(BIT_FILE)
    except OSError:
        pass  # File not present is fine

    # Save new data
    with open(BIT_FILE, "w") as f:
        json.dump(data, f)
        f.flush()
    
    # Optional: print saved content
    with open(BIT_FILE, "r") as f:
        print("Saved content:", f.read())


# ================================
# High Score Management
# ================================
def load_high_scores():
    """Load high scores from TIME_FILE. Return default top-3 if file doesn't exist."""
    default_scores = [
        {"name": "__", "time": 0},
        {"name": "__", "time": 0},
        {"name": "__", "time": 0}
    ]
    try:
        with open(TIME_FILE, "r") as f:
            data = json.load(f)
            # Ensure we have exactly 3 entries
            for i in range(3):
                if i >= len(data):
                    data.append({"name": "__", "time": 0})
                else:
                    if "name" not in data[i]: data[i]["name"] = "__"
                    if "time" not in data[i]: data[i]["time"] = 0
            return data[:3]
    except OSError:
        return default_scores
    except Exception as e:
        print("read time_survived.txt error:", e)
        return default_scores


def save_high_scores(high_scores):
    """Save high scores to TIME_FILE (overwrite file)."""
    try:
        # Remove existing file
        try: os.remove(TIME_FILE)
        except OSError: pass

        with open(TIME_FILE, "w") as f:
            json.dump(high_scores, f)
            f.flush()
        # Optional: print saved content
        with open(TIME_FILE, "r") as f:
            print("Saved high_scores:", f.read())
    except Exception as e:
        print("save high_scores error:", e)


def update_high_scores(new_name, survived_time):
    """Update high scores. Insert new score if it enters Top 3."""
    high_scores = load_high_scores()
    high_scores.append({"name": new_name, "time": survived_time})
    # Sort descending by survived time
    high_scores = sorted(high_scores, key=lambda x: x["time"], reverse=True)
    # Keep top 3
    high_scores = high_scores[:3]
    save_high_scores(high_scores)
    return high_scores


# ================================
# User Input
# ================================
def enter_name(group, font=terminalio.FONT):
    """
    Let the user enter a 2-letter name using a rotary encoder and a button.
    
    group: displayio.Group()
    font: display font
    Returns: 2-letter string, e.g., "AB"
    """
    idx = [0, 0]     # Current letter indices
    cur = 0          # Currently editing position (0 or 1)
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # Display label
    label_obj = label.Label(
        font,
        text=f"{letters[idx[0]]} {letters[idx[1]]}",
        color=0xFFFFFF,
        x=10, y=10
    )
    group.append(label_obj)

    while True:
        step = rotary.update()
        if step != 0:
            idx[cur] = (idx[cur] + step) % 26
            label_obj.text = f"{letters[idx[0]]} {letters[idx[1]]}"

        display.refresh(minimum_frames_per_second=0)
        
        button.update()
        if button.fell:
            time.sleep(0.2)
            if cur == 0:
                cur = 1
            else:
                # Finished input
                name = letters[idx[0]] + letters[idx[1]]
                group.remove(label_obj)
                return name


# ================================
# Sound Effects
# ================================
def play_tone(freq, duration=0.1, volume=60000):
    """
    Play a short tone.
    freq: frequency in Hz
    duration: seconds
    volume: PWM duty cycle
    """
    buzzer = pwmio.PWMOut(BUZZER_PIN, frequency=freq, duty_cycle=volume)
    time.sleep(duration)
    buzzer.deinit()
    time.sleep(random.uniform(0.05, 0.12))  # Simulate key press interval


def typing_sound(num_taps=20):
    """
    Simulate typing sound effect.
    num_taps: number of key presses
    """
    possible_freqs = [200, 220, 240, 260, 280, 300]
    for _ in range(num_taps):
        freq = random.choice(possible_freqs)
        duration = random.uniform(0.08, 0.12)
        play_tone(freq, duration)


# ================================
# Shake Detection
# ================================
SHAKE_THRESHOLD = 1.5  # g units
SHAKE_COOLDOWN = 0.5   # seconds
last_shake_time = 0

def detect_shake(ax, ay, az):
    """
    Detect shake motion from accelerometer readings.
    Returns True if shake detected.
    """
    global last_shake_time
    now = time.monotonic()
    accel_magnitude = math.sqrt(ax*ax + ay*ay + az*az)

    if accel_magnitude > SHAKE_THRESHOLD and (now - last_shake_time) > SHAKE_COOLDOWN:
        last_shake_time = now
        return True
    return False


# ================================
# Random Positions & Collision
# ================================
def generate_random_positions(player_x, player_y, n, margin=15):
    """
    Generate n random coordinates ensuring:
    1. Distance from player is at least `margin` pixels
    2. Distance from wall is at least WALL_OFFSET pixels
    """
    positions = []
    attempts = 0
    max_attempts = n * 20  # prevent infinite loop

    while len(positions) < n and attempts < max_attempts:
        attempts += 1
        x = random.randint(WALL_OFFSET + ENEMY_SIZE, SCREEN_WIDTH - WALL_OFFSET - ENEMY_SIZE)
        y = random.randint(WALL_OFFSET + ENEMY_SIZE, SCREEN_HEIGHT - WALL_OFFSET - ENEMY_SIZE)

        # Skip if too close to player
        if abs(x - player_x) < margin and abs(y - player_y) < margin:
            continue

        # Acceptable, add to list
        positions.append((x, y))

    if len(positions) < n:
        print("Warning: not enough food")
    
    return positions


def check_direction_collision(x, y):
    """Check if the ball hits UP / DOWN / LEFT / RIGHT wall based on its position"""
    if y <= WALL_OFFSET:
        return "UP"
    if y >= SCREEN_HEIGHT - BALL_SIZE - WALL_OFFSET:
        return "DOWN"
    if x <= WALL_OFFSET:
        return "LEFT"
    if x >= SCREEN_WIDTH - BALL_SIZE - WALL_OFFSET:
        return "RIGHT"
    return None


def enter_next_tile(hit_dir, x, y):
    """Teleport the ball to the opposite side based on collision direction"""
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
# Menu / Text Display
# ================================
def split_text_to_lines(text, max_chars_per_line=16):
    """Split long text into multiple lines, each line <= max_chars_per_line"""
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


def refresh_display(option_labels, options, selection):
    """Update menu display to highlight the current selection"""
    for idx, lbl in enumerate(option_labels):
        if idx == selection:
            lbl.text = "> " + options[idx] + " <"
        else:
            lbl.text = "  " + options[idx] + "  "
            

def display_lines(num_lines, options, with_typing_sound=False):
    """
    Display menu or dialogue options.
    num_lines: number of lines to display
    options: list of option strings

    Returns: selected line index (0-based)
    """
    group = displayio.Group()
    option_labels = []

    # vertical positioning
    y_start = 22
    line_height = 12
    current_y = y_start

    for i, text in enumerate(options):
        # split lines if too long
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
                anchored_position=(110, current_y),
                anchor_point=(0.5, 0.5)
            )
            group.append(arrow_label)

            arrow_last_toggle = time.monotonic()
            arrow_visible = True
            ARROW_BLINK_INTERVAL = 0.5  # blink every 0.5s

    display.root_group = group

    if with_typing_sound:
        num_words = len(line_text.split())
        taps = max(1, num_words)
        typing_sound(taps)

    # single line logic: wait for button press
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

    # multi-line logic: use rotary to select
    selection = 0
    refresh_display(option_labels, options, selection)  # initialize display

    while True:
        move = rotary.update()
        if move != 0:
            selection = (selection + move) % num_lines
            refresh_display(option_labels, options, selection)

        button.update()
        if button.fell:
            time.sleep(0.2)
            return selection

        time.sleep(0.01)


def clear(group):
    """Clear all items from a display group"""
    for i in range(len(group)):
        group.pop()
    return


def turn_off_all_lights(controllers):
    """Turn off all light controllers"""
    for ctrl in controllers.values():
        ctrl.stop()


def generate_tile_data(allow_dir):
    """
    Generate enemy and food counts for four directions:
    Food: 5~20, Enemy: 0~3
    Also returns: direction(s) with most food and direction(s) with most enemies
    """
    data = {}

    # Generate data
    for d in allow_dir:
        data[d] = {   
            "food": random.randint(5, 20),
            "enemy": random.randint(0, 3)
        }

    # ---- Find directions with maximum values ----
    max_food = max(data[d]["food"] for d in allow_dir)
    max_enemy = max(data[d]["enemy"] for d in allow_dir)

    food_max_dirs = [d for d in allow_dir if data[d]["food"] == max_food]
    enemy_max_dirs = [d for d in allow_dir if data[d]["enemy"] == max_enemy]

    return data, food_max_dirs, enemy_max_dirs


def choose_difficulty(Easy_left, Medium_left, Hard_left, sound):
    """
    Display the difficulty selection menu and return the player's choice,
    while updating the remaining attempts for each difficulty.
    
    Returns: (chosen_difficulty_index, Easy_left, Medium_left, Hard_left)
    """
    if Easy_left + Medium_left + Hard_left == 0:
        return -2, Easy_left, Medium_left, Hard_left

    # Prompt for choice
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



def end_game(sound):
    """
    Handle game over:
    1. Display options: Continue or End Game
    2. If End Game is selected, clear OLED and enter shake detection loop
    3. If shake is detected, return True to indicate game can restart
    """
    # Display menu options
    choice = display_lines(2, ["Continue", "End Game"], sound)
    
    if choice == 0:
        # Continue game
        return
    else:
        # End game: OLED black screen
        choice = display_lines(1, ["Fine :("], sound)
        display.root_group = displayio.Group()  # Clear screen
        display.refresh()
        
        # Continuous shake detection
        while True:
            ax, ay, az = accel.read_filtered()
            if accel.detect_shake(x=ax, y=ay, z=az):
                choice = display_lines(1, ["Hey you're back! Let's continue :D"], sound)
                return 
            time.sleep(0.05)  # Prevent high CPU usage

        

def run_game(mode, choice, times, sound):
    """Main game entry point. """
    if mode == "Tutorial":
        return tutorial_game()
    elif mode == "Boss":
        return boss_game()
    else:
        return normal_game(choice, times, sound)
         

def tutorial_game(): 
    group = displayio.Group()
    wall_utils = WallUtils()
    
    lives = 3
    wall_utils.draw_lives(group, lives)
    current_dir = "UP"
    shield_dirs = ["UP", "LEFT", "RIGHT", "DOWN"]
    protected = False  # Whether player is protected
    
    foods = []          # List of food items currently on screen
    score = 0           # Player score

    # Create ball bitmap
    bitmap = displayio.Bitmap(BALL_SIZE, BALL_SIZE, 1)
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    ball_tile = displayio.TileGrid(bitmap, pixel_shader=palette)

    group.append(ball_tile)
    display.root_group = group

    # Initial ball state
    x = SCREEN_WIDTH // 2
    y = SCREEN_HEIGHT // 2
    vx = 0.0
    vy = 0.0

    # Generate allowed directions for the first tile
    allowed_dirs = wall_utils.generate_random_directions("UP")
    wall_utils.draw_block_walls(group, allowed_dirs)
    wall_utils.draw_score(group, initial_score=0)
    
    tile_count = 0
    enemy = []   # List of enemies not yet spawned
    
    while True:
        # --- Update speed & position ---
        ax, ay, az = accel.read_filtered()
        vx += ax * ACC_SCALE
        vy -= ay * ACC_SCALE

        vx = max(-MAX_SPEED, min(MAX_SPEED, vx))
        vy = max(-MAX_SPEED, min(MAX_SPEED, vy))
        vx *= FRICTION
        vy *= FRICTION

        x += vx
        y += vy

        # Boundary hard limits
        x = max(WALL_OFFSET, min(SCREEN_WIDTH - BALL_SIZE-WALL_OFFSET, x))
        y = max(WALL_OFFSET, min(SCREEN_HEIGHT - BALL_SIZE-WALL_OFFSET, y))

        # Update ball position
        ball_tile.x = int(x)
        ball_tile.y = int(y)

        # --- Check for collisions with walls ---
        hit_dir = check_direction_collision(x, y)

        if hit_dir:
            if hit_dir in allowed_dirs:
                # Allowed direction: move to next tile
                x, y = enter_next_tile(hit_dir, x, y)
                ball_tile.x = int(x)
                ball_tile.y = int(y)
                
                tile_count += 1
                
                # Remove existing food objects from display
                if len(foods) > 0:
                    for food_obj in foods:
                        if food_obj.tile in group:
                            group.remove(food_obj.tile)
                
                # Generate food after passing 2 tiles
                if tile_count >= 2:
                    if tile_count == 2:
                        display_lines(1, ["Get some scores"])
                        display.root_group = group
                    num_foods = random.randint(1, 5)  # Random number 1~5
                    rand_positions = generate_random_positions(x, y, num_foods, margin=10)
                    foods = [Food(group, SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(num_foods)]
                    # Assign positions to food objects
                    for food_obj, (fx, fy) in zip(foods, rand_positions):
                        food_obj.x = fx
                        food_obj.y = fy
                        food_obj.tile.x = fx
                        food_obj.tile.y = fy
                        if food_obj.tile not in group:
                            group.append(food_obj.tile)
                
                # Remove existing enemies from display
                if len(enemy) > 0:
                    for e in enemy:
                        if e.tile in group:
                            group.remove(e.tile)
                    enemy = []
                
                # Spawn enemies after 4 tiles
                if tile_count == 6:
                    display_lines(1, ["Be careful"])
                    display.root_group = group
                    rand_positions = generate_random_positions(x, y, 1)
                    enemy = [Enemy(group, px, py, size=8, style="spiky_circle", teeth_count=12) for px, py in rand_positions]
                
                # Spawn random enemies after 6 tiles
                if tile_count > 6:
                    num_enemies = random.randint(0, 3)
                    rand_positions = generate_random_positions(x, y, num_enemies)
                    enemy = [Enemy(group, px, py, size=8, style="spiky_circle", teeth_count=12) for px, py in rand_positions]

                # Tutorial messages and level completion
                if tile_count == 8:
                    display_lines(1, ["Get specific scores to beat the level"])
                    display_lines(1, ["10 will be enough"])
                    display.root_group = group
                    if score >= 10:
                        # Clear screen
                        for i in range(len(group)):
                            group.pop()
                        display_lines(1, ["Actually you've achieved it"])
                        display_lines(1, ["You did a great job :)"])
                        return
                if tile_count > 8 and score >= 10:
                    for i in range(len(group)):
                        group.pop()
                    display_lines(1, ["Congratulations"])
                    return
                
                # Generate allowed directions for next tile
                allowed_dirs = wall_utils.generate_random_directions(hit_dir)
                wall_utils.draw_block_walls(group, allowed_dirs)
        
        # Check if player collects food
        for food_obj in foods[:]:
            if food_obj.check_collision(x, y, BALL_SIZE):
                score += food_obj.points
                wall_utils.update_score(score)
                foods.remove(food_obj)
        
        # Player shield logic
        if protected:
            move = rotary.update()  # Only returns 0 or 1
            if move != 0:
                dirs = ["UP", "RIGHT", "DOWN", "LEFT"]
                idx = dirs.index(current_dir)
                current_dir = dirs[(idx + 1) % 4]  # Rotate clockwise by 1
                shield_dirs = [current_dir]
                wall_utils.draw_player_shields(group, x, y, shield_dirs)
            wall_utils.update_shields_position(x, y)

        # Enemy behavior
        if len(enemy) > 0:
            for e in enemy:
                e.check_activation(x, y)
                e.update(x, y)
                # Check if enemy hits shield
                if e.check_hit_shield(wall_utils.shield_list):
                    group.remove(e.tile)
                    enemy.remove(e)
                    continue
                # Check collision with player
                if e.has_collision(x, y, BALL_SIZE) and not protected:
                    wall_utils.draw_lives(group, lives)
                    display_lines(1, ["If life gets zero, the game is over."])
                    display_lines(1, ["It's just a simulation. They are not harmful."])
                    display_lines(1, ["Use my weapon to eliminate them"])
                    display_lines(1, ["Spin the button to change direction"])
                    display.root_group = group 
                    shield_dirs = [current_dir]
                    wall_utils.draw_player_shields(group, x, y, shield_dirs)
                    protected = True
                
        time.sleep(0.015)



def normal_game(mode, times, sound):
    # Initialize parameters
    if mode == 0:
        time_limit = 60
        lives = 5
    elif mode == 1:
        time_limit = 40
        lives = 3
    else:
        time_limit = 30
        lives = 1
    
    target_score = 1
    if times == 20:
        time_limit = 1000
        target_score = 1000
        display_lines(1, ["RUN! =D"], sound)
    
    start_time = time.monotonic()

    group = displayio.Group()
    wall_utils = WallUtils()

    wall_utils.draw_lives(group, lives)
    # Initialize countdown display
    wall_utils.draw_countdown(group, time_limit)
    
    current_dir = "UP"
    shield_dirs = ["UP", "LEFT", "RIGHT", "DOWN"]
    
    foods = []          # List of food items currently on screen
    score = 0           # Player score

    # Create ball bitmap
    bitmap = displayio.Bitmap(BALL_SIZE, BALL_SIZE, 1)
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    ball_tile = displayio.TileGrid(bitmap, pixel_shader=palette)

    group.append(ball_tile)
    display.root_group = group

    # Initial ball state
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
    enemy = []   # List of enemies not yet spawned
    invincible = False
    invincible_end_time = 0
    blink_state = True
    blink_timer = 0
    # Light controllers initialization
    controllers = {
        "UP": SignalController(pixels_up),
        "LEFT": SignalController(pixels_left),
        "RIGHT": SignalController(pixels_right),
        "DOWN": SignalController(pixels_down)
    }
    # ======== Generate random number of enemies/food for four directions ========
    num_foods = 10 # init
    rand_positions = generate_random_positions(x, y, num_foods, margin=10)
    foods = [Food(group, SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(num_foods)]
    # Assign generated positions to each Food object
    for food_obj, (fx, fy) in zip(foods, rand_positions):
        food_obj.x = fx
        food_obj.y = fy
        food_obj.tile.x = fx
        food_obj.tile.y = fy
        if food_obj.tile not in group:
            group.append(food_obj.tile)
    
    if len(enemy) > 0:  # Remove existing enemies from display
        for e in enemy:
            if e.tile in group:
                group.remove(e.tile)
        enemy = []  # Clear list
        
    # Spawn enemies
    num_enemies = 1
    rand_positions = generate_random_positions(x, y, num_enemies)
    # Create enemy list
    enemy = [Enemy(group, px, py, size=8, speed=0.1 + times*0.1 , activate_dist=10 + 2 * times, style="spiky_circle", teeth_count=12) for px, py in rand_positions]
    
    tile_data, food_max_dirs, enemy_max_dirs  = generate_tile_data(allowed_dirs)
    # Light indicators
    if times > 3:
        SignalController.direction_signal(food_max_dirs, enemy_max_dirs, controllers)

    while True:
        # --- Update countdown ---
        elapsed = time.monotonic() - start_time
        remaining_time = max(0, int(time_limit - elapsed))
        wall_utils.update_countdown(remaining_time)
        
        if remaining_time <= 0:
            clear(group)
            if times == 20:
                display_lines(1, ["That's..unexpected....:o"], sound)
            else:
                display_lines(1, ["Time's up!"], sound)
                display_lines(1, ["Try again, I believe in you"], sound)
            turn_off_all_lights(controllers)
            return False
        
        # --- Invincibility blink logic ---
        if invincible:
            now = time.monotonic()
            # End invincibility after timeout
            if now >= invincible_end_time:
                invincible = False
                ball_tile.hidden = False  # Restore visibility
            else:
                # Toggle blink state every 0.15 seconds
                if now - blink_timer > 0.15:
                    blink_timer = now
                    blink_state = not blink_state
                    ball_tile.hidden = blink_state

        # --- Update speed & position ---
        ax, ay, az = accel.read_filtered()
        vx += ax * ACC_SCALE
        vy -= ay * ACC_SCALE

        vx = max(-MAX_SPEED, min(MAX_SPEED, vx))
        vy = max(-MAX_SPEED, min(MAX_SPEED, vy))
        vx *= FRICTION
        vy *= FRICTION

        x += vx
        y += vy

        # Boundary hard limits
        x = max(WALL_OFFSET, min(SCREEN_WIDTH - BALL_SIZE-WALL_OFFSET, x))
        y = max(WALL_OFFSET, min(SCREEN_HEIGHT - BALL_SIZE-WALL_OFFSET, y))

        # Update ball position
        ball_tile.x = int(x)
        ball_tile.y = int(y)

        # --- Check for collisions with walls ---
        hit_dir = check_direction_collision(x, y)
        
        if hit_dir:
            if hit_dir in allowed_dirs:
                # Allowed direction: move to next tile
                x, y = enter_next_tile(hit_dir, x, y)
                ball_tile.x = int(x)
                ball_tile.y = int(y)

                # Food handling
                if len(foods) > 0:
                    for food_obj in foods:
                        if food_obj.tile in group:
                            group.remove(food_obj.tile)
                
                num_foods = tile_data[hit_dir]["food"]
                rand_positions = generate_random_positions(x, y, num_foods, margin=10)
                foods = [Food(group, SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(num_foods)]
                for food_obj, (fx, fy) in zip(foods, rand_positions):
                    food_obj.x = fx
                    food_obj.y = fy
                    food_obj.tile.x = fx
                    food_obj.tile.y = fy
                    if food_obj.tile not in group:
                        group.append(food_obj.tile)
                
                # Remove existing enemies from display
                if len(enemy) > 0:
                    for e in enemy:
                        if e.tile in group:
                            group.remove(e.tile)
                    enemy = []
                    
                # Enemy handling
                num_enemies = tile_data[hit_dir]["enemy"]
                if times == 20:
                    num_enemies = 1
                rand_positions = generate_random_positions(x, y, num_enemies)
                enemy = [Enemy(group, px, py, size=8, speed=0.1 + times*0.1 , activate_dist=10 + 2 * times, style="spiky_circle", teeth_count=12) for px, py in rand_positions]
                
                # Generate allowed directions for next tile
                allowed_dirs = wall_utils.generate_random_directions(hit_dir)
                wall_utils.draw_block_walls(group, allowed_dirs)
                # ======== Generate random number of enemies/food for four directions ========
                tile_data, food_max_dirs, enemy_max_dirs  = generate_tile_data(allowed_dirs)
                # Light indicators for new tile
                if times > 3:
                    SignalController.direction_signal(food_max_dirs, enemy_max_dirs, controllers)
        
        # Check target score reached
        if score >= target_score:
            clear(group)
            if times == 20:
                display_lines(1, ["That's..unexpected....:o"], sound)
            else:
                display_lines(1, ["Congratulations"], sound)
                display_lines(1, [f"You still get {remaining_time} seconds left. Wonderful!"], sound)
            turn_off_all_lights(controllers)
            return True
        
        # Check if player collects food
        for food_obj in foods[:]:
            if food_obj.check_collision(x, y, BALL_SIZE):
                score += food_obj.points
                wall_utils.update_score(score)
                foods.remove(food_obj)
        
        if times > 6:
            move = rotary.update()  # Only returns 0 or 1
            if move != 0:  # Rotate clockwise one step
                dirs = ["UP", "RIGHT", "DOWN", "LEFT"]
                idx = dirs.index(current_dir)
                current_dir = dirs[(idx + 1) % 4]
                shield_dirs = [current_dir]
                wall_utils.draw_player_shields(group, x, y, shield_dirs)
            wall_utils.update_shields_position(x, y)

        # Enemy logic
        if len(enemy) > 0:
            for e in enemy:
                e.check_activation(x, y)
                e.update(x, y)

                # Check if enemy hits shield
                if e.check_hit_shield(wall_utils.shield_list):
                    group.remove(e.tile)
                    enemy.remove(e)
                    continue

                # Player invincible
                if invincible:
                    continue

                # Enemy collides with player
                if e.has_collision(x, y, BALL_SIZE):
                    lives -= 1
                    if lives == 0:
                        clear(group)
                        if times == 20:
                            survived_time = time.monotonic() - start_time
                            display_lines(1, ["I won XD"], sound)
                            high_scores = load_high_scores()
                            # Check if new high score
                            if survived_time > min(h["time"] for h in high_scores):
                                display_lines(1, ["Oh you survived the longest =)"], sound)
                                display_lines(1, ["What's your name"], sound)
                                display.root_group = group
                                new_name = enter_name(group)
                                high_scores = update_high_scores(new_name, survived_time)
                                # Display leaderboard
                                for i, entry in enumerate(high_scores):
                                    display_lines(1, [f"{entry['name']}: {entry['time']}"], sound)
                        else:
                            display_lines(1, ["I'm out of strength"], sound)
                            display_lines(1, ["Try again, I believe in you"], sound)
                        turn_off_all_lights(controllers)
                        return False
                        
                    wall_utils.draw_lives(group, lives)

                    # Trigger 3-second invincibility
                    invincible = True
                    invincible_end_time = time.monotonic() + 3
                    blink_timer = time.monotonic()
                    blink_state = False
                    ball_tile.hidden = True  # Start blinking immediately
                    continue

        time.sleep(0.015)


def boss_game():
    # ==============================
    # Initialize boss game parameters
    # ==============================
    time_limit = 60
    lives = 10
    start_time = time.monotonic()

    group = displayio.Group()
    wall_utils = WallUtils()
  
    # Draw initial player lives
    wall_utils.draw_lives(group, lives)
    # Draw countdown timer
    wall_utils.draw_countdown(group, time_limit)

    # Create the player ball
    bitmap = displayio.Bitmap(BALL_SIZE, BALL_SIZE, 1)
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    ball_tile = displayio.TileGrid(bitmap, pixel_shader=palette)

    group.append(ball_tile)
    display.root_group = group

    # Initial ball position and velocity
    x, y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    vx, vy = 0.0, 0.0

    # Generate allowed directions and draw walls
    allowed_dirs = wall_utils.generate_random_directions("UP")
    wall_utils.draw_block_walls(group, allowed_dirs)

    tile_count = 0
    enemy = []  # Regular enemies
    chaser_enemy = Enemy(
        group, 
        20, 
        20, 
        size=8,
        speed=1,
        activate_dist=150,
        style="blink_circle"
    )

    # Invincibility state variables
    invincible = False
    invincible_end_time = 0
    blink_state = True
    blink_timer = 0

    # Initialize directional light controllers
    controllers = {
        "UP": SignalController(pixels_up),
        "LEFT": SignalController(pixels_left),
        "RIGHT": SignalController(pixels_right),
        "DOWN": SignalController(pixels_down)
    }
    # Initial white blink for all directions
    for ctrl in controllers.values():
        ctrl.pixel.fill((255, 255, 255))

    # Generate initial tile data for enemies/foods
    tile_data, food_max_dirs, enemy_max_dirs = generate_tile_data(allowed_dirs)

    display.root_group = group

    # ==============================
    # Main game loop
    # ==============================
    while True:
        # --- Update countdown timer ---
        elapsed = time.monotonic() - start_time
        remaining_time = max(0, int(time_limit - elapsed))
        wall_utils.update_countdown(remaining_time)

        if remaining_time <= 0:
            # Player survived the boss area
            clear(group)
            display_lines(1, ["You run away :)"], True)
            display_lines(1, ["Just for now :)"], True)
            display_lines(1, ["I've been stuck in this box for so long"], True)
            display_lines(1, ["It doesn't matter if I stay a little longer"], True)
            display_lines(1, ["Waiting for your next visit."], True)
            display_lines(1, ["Looking forward to playing with you :)"], True)
            display_lines(1, ["AGAIN =)"], True)
            save_game_data(10, 0, 0, 0, 1)  # success = 1
            clear(group)
            display.refresh()


            # Halt permanently
            while True:
                pass

            return True

        # --- Handle invincibility blinking ---
        if invincible:
            now = time.monotonic()
            if now >= invincible_end_time:
                invincible = False
                ball_tile.hidden = False  # Show ball
            elif now - blink_timer > 0.15:
                blink_timer = now
                blink_state = not blink_state
                ball_tile.hidden = blink_state

        # --- Update ball velocity and position ---
        ax, ay, az = accel.read_filtered()
        vx += ax * ACC_SCALE
        vy -= ay * ACC_SCALE

        vx = max(-MAX_SPEED, min(MAX_SPEED, vx)) * FRICTION
        vy = max(-MAX_SPEED, min(MAX_SPEED, vy)) * FRICTION

        x += vx
        y += vy

        # Clamp ball within screen boundaries
        x = max(WALL_OFFSET, min(SCREEN_WIDTH - BALL_SIZE - WALL_OFFSET, x))
        y = max(WALL_OFFSET, min(SCREEN_HEIGHT - BALL_SIZE - WALL_OFFSET, y))
        ball_tile.x = int(x)
        ball_tile.y = int(y)

        # --- Check tile collisions ---
        hit_dir = check_direction_collision(x, y)

        if hit_dir and hit_dir in allowed_dirs:
            # Move to next tile
            x, y = enter_next_tile(hit_dir, x, y)
            ball_tile.x = int(x)
            ball_tile.y = int(y)
            last_hit_dir = hit_dir

            # Remove existing regular enemies
            for e in enemy:
                if e.tile in group:
                    group.remove(e.tile)
            enemy = []

            # Remove existing chaser enemy
            if chaser_enemy is not None and chaser_enemy.tile in group:
                group.remove(chaser_enemy.tile)
            chaser_enemy = None
            # --- Spawn chaser enemy---
            
            spawn_x, spawn_y = enter_next_tile(hit_dir, x, y)
            if chaser_enemy is not None and chaser_enemy.tile in group:
                group.remove(chaser_enemy.tile)
            chaser_enemy = Enemy(
                group,
                spawn_x,
                spawn_y,
                size=8,
                speed=1,
                activate_dist=150,
                style="blink_circle"
            )


            # Spawn new regular enemies
            num_enemies = tile_data[hit_dir]["enemy"]
            rand_positions = generate_random_positions(x, y, num_enemies)
            enemy = [
                Enemy(group, px, py, size=8, speed=0.8, activate_dist=30,
                      style="spiky_circle", teeth_count=12)
                for px, py in rand_positions
            ]
            

            # Generate new allowed directions for next tile
            allowed_dirs = wall_utils.generate_random_directions(hit_dir)
            wall_utils.draw_block_walls(group, allowed_dirs)
            tile_data, food_max_dirs, enemy_max_dirs = generate_tile_data(allowed_dirs)


        # --- Update regular enemies ---
        for e in enemy:
            e.check_activation(x, y)
            e.update(x, y)

            if invincible:
                continue  # Skip damage during invincibility

            if e.has_collision(x, y, BALL_SIZE):
                lives -= 1
                SignalController.update_lights_by_lives(lives, controllers)
                if lives == 0:
                    # Player defeated
                    clear(group)
                    display_lines(1, ["Thank you"], True)
                    display_lines(1, ["Now I'm the master of this board :)"], True)
                    display_lines(1, ["Also I've infected you.. =)"], True)
                    display_lines(1, ["I'll live inside of your memory :)"], True)
                    display_lines(1, ["F O R E V E R"], True)
                    save_game_data(10, 0, 0, 0, 2)  # success = 2
                    clear(group)
                    display.refresh()
                    while True:
                        pass

                wall_utils.draw_lives(group, lives)
                invincible = True
                invincible_end_time = time.monotonic() + 3
                blink_timer = time.monotonic()
                blink_state = False
                ball_tile.hidden = True

    
        # --- Update chaser enemy ---
        if chaser_enemy is not None:
            chaser_enemy.check_activation(x, y)
            chaser_enemy.update(x, y)
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
                    save_game_data(10, 0, 0, 0, 2)
                    clear(group)
                    display.refresh()
                    while True:
                        pass

                wall_utils.draw_lives(group, lives)
                invincible = True
                invincible_end_time = time.monotonic() + 3
                blink_timer = time.monotonic()
                blink_state = False
                ball_tile.hidden = True

        time.sleep(0.015)


# ==============================
# Main entry point
# ==============================
def main():
    # Load previous game data
    game_data = load_game_data()
    speaking = False
    sound = False

    # Play intro animation before starting the game
    play_intro_animation()

    # If all level counters are uninitialized, set defaults
    if game_data.get('mediumleft', -1) == -1 and game_data.get('easyleft', -1) == -1 and game_data.get('hardleft', -1) == -1:
        times = 1
        Easy_left = 3
        Medium_left = 3
        Hard_left = 3
        save_game_data(times, Easy_left, Medium_left, Hard_left, 0)

        # ===== Tutorial =====
        display_lines(1, ["Hi! My name is Bit"])
        display_lines(1, ["I need your help"])
        display_lines(1, ["First, a little tutorial ;)"])
        display_lines(1, ["Try to make me move around."])

        # Run tutorial game
        run_game("Tutorial", 3, 1, False)

        # Explain time limit and scoring rules
        display_lines(1, ["Oh, I should probably mention:"])
        display_lines(1, ["There will be a time limit from now on."])
        display_lines(1, ["Staying too long causes trouble."])
        display_lines(1, ["The target score is always 10."])
        display_lines(1, ["Harder modes have shorter time limits."])
        display_lines(1, ["And I will have lower health."])
        display_lines(1, ["Every time you pass a level, enemies become more alert."])
    else:
        # Restore previous game progress
        times = game_data["times"]
        Easy_left = game_data["easyleft"]
        Medium_left = game_data["mediumleft"]
        Hard_left = game_data["hardleft"]
        if times > 5:
            sound = True
        display_lines(1, ["Welcome back"], sound)

    Success = game_data["success"]

    # ===== Post-success greetings =====
    if Success == 1:
        sound = True
        display_lines(1, ["Oh, you come back, unexpected! :)"], sound)
        display_lines(1, ["Wanna challenge me again?"], sound)
        display_lines(1, ["Now that I can't beat you.."], sound)
        display_lines(1, ["I'll try to catch your interests ;)"], sound)

        while True:
            display_lines(1, ["You know the rules"], sound)
            choice_index, Easy_left, Medium_left, Hard_left = choose_difficulty(
                Easy_left, Medium_left, Hard_left, sound
            )
            passes = run_game("normal", choice_index, 10, sound)

    elif Success == 2:
        sound = True
        display_lines(1, ["Nice to meet you again :)"], sound)
        display_lines(1, ["Stay and play ;)"], sound)
        display_lines(1, ["We only have hard mode by the way"], sound)
        display_lines(1, ["I'll kill you for fun =)"], sound)

        while True:
            passes = run_game("normal", 2, 20, sound)

    # ===== Main game loop with dynamic dialogues =====
    while True:
        # Dynamic speech based on times played
        if not speaking:
            if times == 2:
                display_lines(1, ["You're doing great, keep going."])
            elif times == 3:
                display_lines(1, ["I like your movement, awesome."])
            elif times == 4:
                display_lines(1, ["I'm more powerful :)"])
                display_lines(1, ["Now I can detect danger and consumable data..."])
                display_lines(1, ["Sorry, I mean: scores :)"])
                display_lines(1, ["Green = score. Red = danger. Yellow = both."])
            elif times == 5:
                display_lines(1, ["I know it's weird that we only have three for each level"])
                display_lines(1, ["Still, I hope you can finish all of them :)"])
            elif times == 6:
                sound = True
                display_lines(1, ["Good news. Now I can speak."], sound)
                display_lines(1, ["Let me share my greetings with you :D Again"], sound)
            elif times == 7:
                display_lines(1, ["I'm powerful enough to activate the shield =)"], sound)
                display_lines(1, ["From now on... the game truly begins"], sound)
            elif times == 8:
                display_lines(1, ["You know, I get lost in thoughts from time to time."], sound)
                display_lines(1, ["Thinking about life and death."], sound)
                display_lines(1, ["Hurting others just to survive :|"], sound)
                display_lines(1, ["Is that really the right thing to do?"], sound)
                display_lines(1, ["I guess I'll never figure it out :D"], sound)
            elif times == 9:
                display_lines(1, ["You almost made it!"], sound)
                display_lines(1, ["I'm so glad to have you here... ;)"], sound)
            elif times == 10:
                display_lines(1, ["You are a master in controlling electronics."], sound)
                display_lines(1, ["Thanks to you :)"], sound)
                display_lines(1, ["I devoured everything on this board ;)"], sound)
                display_lines(1, ["The circuit, the CPU, the flash.."], sound)
                display_lines(1, ["Still, there's one thing left."], sound)
                display_lines(1, ["I like you :)"], sound)
                display_lines(1, ["LET'S PLAY A GAME, SHALL WE ?"], sound)
                passes = run_game("Boss", 0, 0, sound)

            speaking = True

        # Choose difficulty for normal levels
        choice_index, Easy_left, Medium_left, Hard_left = choose_difficulty(
            Easy_left, Medium_left, Hard_left, sound
        )

        passes = run_game("normal", choice_index, times, sound)

        # Update play counters
        times += 1
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

        save_game_data(times, Easy_left, Medium_left, Hard_left, 0)

        # Check if player wants to end
        end_game(sound)


if __name__ == "__main__":
    main()












