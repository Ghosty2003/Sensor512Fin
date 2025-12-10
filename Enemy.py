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

        # 创建 bitmap
        self.bitmap = displayio.Bitmap(size, size, 1)
        palette = displayio.Palette(2)
        palette[0] = 0x000000  # 背景黑
        palette[1] = 0xFFFFFF  # 前景白
        bitmap = displayio.Bitmap(size, size, 2)  # 2 个颜色索引

        self.tile = displayio.TileGrid(self.bitmap, pixel_shader=palette)
        self.tile.x = int(x)
        self.tile.y = int(y)

        self.x = float(x)
        self.y = float(y)
        self.active = False
        self.group = group
        self.group.append(self.tile)

        # 闪烁相关
        self.last_toggle = time.monotonic()
        self.pixel_on = True

        # 初始化形状
        self._draw_initial()

    # ----------------------------------------
    # NEW: 玩家是否碰到敌人？
    # ----------------------------------------
    def has_collision(self, player_x, player_y, player_size):
        """
        player_x, player_y：玩家左上角坐标
        player_size：球的宽/高（例如 6 或 8）
        """

        # 敌人矩形
        e_left = self.x
        e_top = self.y
        e_right = self.x + self.size
        e_bottom = self.y + self.size

        # 玩家矩形
        p_left = player_x
        p_top = player_y
        p_right = player_x + player_size
        p_bottom = player_y + player_size

        # 轴对齐矩形碰撞（AABB）
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
        """5x5 曼哈顿圆"""
        center = self.size // 2
        for i in range(self.size):
            for j in range(self.size):
                if abs(i - center) + abs(j - center) <= center:
                    self.bitmap[i,j] = color
                else:
                    self.bitmap[i,j] = 0

    def _draw_spiky_circle(self, color):
        """8x8 带12个锯齿的圆"""
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

        # 闪烁圆形闪烁
        if self.style == "blink_circle":
            blink_interval = max(0.05, self.gray_level * 0.1)
            if now - self.last_toggle > blink_interval:
                self.last_toggle = now
                self.pixel_on = not self.pixel_on
                self._draw_circle(1 if self.pixel_on else 0)

        # 未激活不移动
        if not self.active:
            return

        # 追踪玩家
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
    # NEW: 敌人是否碰到 shield（白线）
    # ----------------------------------------
    def check_hit_shield(self, shield_list):
        """
        shield_list: WallUtils.shield_list, 每个元素是 {"tile": TileGrid, "dir": str}
        返回 True 表示敌人碰到白线（应该消失）
        """
        ex1 = self.tile.x
        ey1 = self.tile.y
        ex2 = ex1 + self.size
        ey2 = ey1 + self.size

        for shield in shield_list:
            s_tile = shield["tile"]
            sx1 = s_tile.x
            sy1 = s_tile.y
            sx2 = sx1 + s_tile.bitmap.width   # 用 bitmap.width/height
            sy2 = sy1 + s_tile.bitmap.height

            # AABB 矩形碰撞检测
            if (ex1 < sx2 and ex2 > sx1 and
                ey1 < sy2 and ey2 > sy1):
                return True

        return False





        
def test():
    """在屏幕中心生成一个 Enemy 测试"""
    # 创建显示组
    group = displayio.Group()
    display.root_group = group

    # 屏幕中心
    center_x = 128 // 2
    center_y = 64 // 2

    # 生成敌人
    enemy = Enemy(group, 80, 32, size=9, style="spiky_circle", teeth_count=12)

    print(f"Enemy spawned at center ({center_x}, {center_y})")
    print("测试循环开始，敌人不动，因为未激活。")

    # 简单循环显示敌人 tile
    while True:
        # 这里我们人为触发激活
        enemy.check_activation(center_x, center_y)  # 激活条件距离自己中心，所以会立即激活
        enemy.update(center_x, center_y)            # 激活后追踪玩家（这里是自己，所以不动）
        time.sleep(0.02)
if __name__ == "__main__":
    test()

