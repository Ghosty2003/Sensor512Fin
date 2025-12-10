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
import random

class Enemy:
    def __init__(self, group, x, y, size=9, speed=0.4, activate_dist=20,
                 gray_level=0.5, style="blink_circle", teeth_count=12):
        self.size = size
        self.speed = speed
        self.activate_dist = activate_dist
        self.gray_level = gray_level
        self.style = style
        self.teeth_count = teeth_count

        # Create bitmap
        self.bitmap = displayio.Bitmap(size, size, 1)
        palette = displayio.Palette(2)
        palette[0] = 0x000000  # background black
        palette[1] = 0xFFFFFF  # foreground white
        bitmap = displayio.Bitmap(size, size, 2)  # 2 color indices

        self.tile = displayio.TileGrid(self.bitmap, pixel_shader=palette)
        self.tile.x = int(x)
        self.tile.y = int(y)

        self.x = float(x)
        self.y = float(y)
        self.active = False
        self.group = group
        self.group.append(self.tile)

        # Blinking control
        self.last_toggle = time.monotonic()
        self.pixel_on = True

        # Initialize shape
        self._draw_initial()

    # ----------------------------------------
    # NEW: Check if enemy collides with player
    # ----------------------------------------
    def has_collision(self, player_x, player_y, player_size):
        """
        player_x, player_y: player's top-left corner
        player_size: player's width/height (e.g., 6 or 8)
        """

        # Enemy rectangle
        e_left = self.x
        e_top = self.y
        e_right = self.x + self.size
        e_bottom = self.y + self.size

        # Player rectangle
        p_left = player_x
        p_top = player_y
        p_right = player_x + player_size
        p_bottom = player_y + player_size

        # Axis-aligned bounding box collision (AABB)
        if (e_left < p_right and
            e_right > p_left and
            e_top < p_bottom and
            e_bottom > p_top):
            return True

        return False
    
    
    def _draw_initial(self):
        if self.style == "blink_circle":
            self._draw_circle(1)
        elif self.style == "spiky_circle":
            self._draw_spiky_circle(1)

    def _draw_circle(self, color):
        """5x5 Manhattan circle"""
        center = self.size // 2
        for i in range(self.size):
            for j in range(self.size):
                if abs(i - center) + abs(j - center) <= center:
                    self.bitmap[i,j] = color
                else:
                    self.bitmap[i,j] = 0

    def _draw_spiky_circle(self, color):
        """8x8 circle with 12 spikes"""
        center = (self.size - 1) / 2
        radius = center
        for i in range(self.size):
            for j in range(self.size):
                dx = i - center
                dy = j - center
                angle = math.atan2(dy, dx)
                dist = (dx*dx + dy*dy) ** 0.5
                spike_radius = radius * (0.7 + 0.3 * math.sin(angle * self.teeth_count))
                self.bitmap[i,j] = color if dist <= spike_radius else 0

    def check_activation(self, player_x, player_y):
        if self.active:
            return
        if abs(self.x - player_x) < self.activate_dist and abs(self.y - player_y) < self.activate_dist:
            self.active = True
            print("Enemy activated!")

    def update(self, player_x, player_y):
        now = time.monotonic()

        # Blinking circle animation
        if self.style == "blink_circle":
            blink_interval = max(0.05, self.gray_level * 0.1)
            if now - self.last_toggle > blink_interval:
                self.last_toggle = now
                self.pixel_on = not self.pixel_on
                self._draw_circle(1 if self.pixel_on else 0)

        # Not activated → don't move
        if not self.active:
            return

        # Track player
        if self.x < player_x:
            self.x += self.speed
        elif self.x > player_x:
            self.x -= self.speed

        if self.y < player_y:
            self.y += self.speed
        elif self.y > player_y:
            self.y -= self.speed

        self.tile.x = int(self.x)
        self.tile.y = int(self.y)
    
    # ----------------------------------------
    # NEW: Check if enemy hits the shield (white line)
    # ----------------------------------------
    def check_hit_shield(self, shield_list):
        """
        shield_list: WallUtils.shield_list, each element is {"tile": TileGrid, "dir": str}
        Returns True if enemy touches the shield (should disappear)
        """
        ex1 = self.tile.x
        ey1 = self.tile.y
        ex2 = ex1 + self.size
        ey2 = ey1 + self.size

        for shield in shield_list:
            s_tile = shield["tile"]
            sx1 = s_tile.x
            sy1 = s_tile.y
            sx2 = sx1 + s_tile.bitmap.width   # use bitmap.width/height
            sy2 = sy1 + s_tile.bitmap.height

            # AABB rectangle collision
            if (ex1 < sx2 and ex2 > sx1 and
                ey1 < sy2 and ey2 > sy1):
                return True

        return False





        
def test():
    """Spawn an Enemy at the screen center for testing"""
    # Create display group
    group = displayio.Group()
    display.root_group = group

    # Screen center
    center_x = 128 // 2
    center_y = 64 // 2

    # Spawn enemy
    enemy = Enemy(group, 80, 32, size=9, style="spiky_circle", teeth_count=12)

    print(f"Enemy spawned at center ({center_x}, {center_y})")
    print("Test loop begins; enemy will not move until activated.")

    # Simple test loop
    while True:
        # Manually activate for test
        enemy.check_activation(center_x, center_y)  # Will activate immediately due to proximity
        enemy.update(center_x, center_y)            # Tracking player (same point) → stays still
        time.sleep(0.02)

if __name__ == "__main__":
    test()

