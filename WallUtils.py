import displayio
import random
from adafruit_display_text import label
import terminalio

SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64

DIRECTIONS = ["UP", "DOWN", "LEFT", "RIGHT"]
OPPOSITE = {
    "UP": "DOWN",
    "DOWN": "UP",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT"
}


class WallUtils:

    def __init__(self):
        self.walls_list = []
        self.shield_list = []

    def draw_wall(self, group, x, y, w, h, color=1):
        """画单个墙壁"""
        bitmap = displayio.Bitmap(w, h, 2)
        for i in range(w):
            for j in range(h):
                bitmap[i, j] = color
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette[1] = 0xFFFFFF
        tile = displayio.TileGrid(bitmap, pixel_shader=palette, x=x, y=y)
        group.append(tile)
        return tile
    
    def draw_lives(self, parent_group, lives):
        # 如果没有 life_group，则创建
        if not hasattr(self, "life_group"):
            self.life_group = displayio.Group()
            parent_group.append(self.life_group)

        # 清空生命图标组
        while len(self.life_group) > 0:
            self.life_group.pop()

        # ❤️ 4x4 心形像素图（1=亮色，0=背景）
        heart_pattern = [
            [1, 0, 0, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [0, 1, 1, 0]
        ]

        for i in range(lives):
            bmp = displayio.Bitmap(4, 4, 2)
            pal = displayio.Palette(2)
            pal[0] = 0x000000  # 黑色（背景）
            pal[1] = 0xFFFFFF  # 白色（心形）

            # 写入爱心像素
            for y in range(4):
                for x in range(4):
                    bmp[x, y] = heart_pattern[y][x]

            tile = displayio.TileGrid(bmp, pixel_shader=pal)

            tile.x = SCREEN_WIDTH - 10 - i * 6
            tile.y = SCREEN_HEIGHT - 17
            self.life_group.append(tile)



    # ================================
    # 生成随机方向
    # ================================
    def simple_sample(self, pool, k):
        pool_copy = list(pool)
        result = []
        for _ in range(k):
            idx = random.randrange(len(pool_copy))
            result.append(pool_copy.pop(idx))
        return result

    def generate_random_directions(self, last_dir):
        must_include = OPPOSITE[last_dir]  # 反方向必须出现
        pool = [d for d in DIRECTIONS if d != must_include]  # 排除玩家撞的方向本身
        r = random.random()
        
        if r < 0.33:
            dirs = []
        elif r < 0.7:
            dirs = self.simple_sample(pool, 1)
        else:
            dirs = self.simple_sample(pool, 2)

        dirs.append(must_include)
        return dirs

    # ================================
    # 画阻挡墙
    # ================================
    def draw_block_walls(self, group, allowed_dirs):
        """根据 allowed_dirs 绘制阻挡墙"""
        # 清除旧墙
        for wall in self.walls_list:
            if wall in group:
                group.remove(wall)
        self.walls_list.clear()

        blocked = [d for d in DIRECTIONS if d not in allowed_dirs]

        thickness = 3
        padding = 2

        tile_x = 0
        tile_y = 0
        tile_w = 128
        tile_h = 64

        walls = {
            "UP": (
                tile_x + padding,
                tile_y + padding,
                tile_w - padding * 2,
                thickness
            ),
            "DOWN": (
                tile_x + padding,
                tile_y + tile_h - padding - thickness,
                tile_w - padding * 2,
                thickness
            ),
            "LEFT": (
                tile_x + padding,
                tile_y + padding,
                thickness,
                tile_h - padding * 2
            ),
            "RIGHT": (
                tile_x + tile_w - padding - thickness,
                tile_y + padding,
                thickness,
                tile_h - padding * 2
            )
        }

        for d in blocked:
            x, y, w, h = walls[d]
            wall_obj = self.draw_wall(group, x, y, w, h)
            self.walls_list.append(wall_obj)
    # ================================
    # 绘制玩家周围白色防护线
    # ================================
    def update_shields_position(self, player_x, player_y):
        """根据玩家当前位置移动已有 shields"""
        if not hasattr(self, "shield_list"):
            return

        length = 20
        thickness = 2
        padding = 2  # 离玩家的距离

        for shield in self.shield_list:
            tile = shield["tile"]
            d = shield["dir"]
            if d == "UP":
                tile.x = int(player_x - length // 2)
                tile.y = int(player_y - length // 2 - padding)
            elif d == "DOWN":
                tile.x = int(player_x - length // 2)
                tile.y = int(player_y + length // 2 + padding)
            elif d == "LEFT":
                tile.x = int(player_x - length // 2 - padding)
                tile.y = int(player_y - length // 2)
            elif d == "RIGHT":
                tile.x = int(player_x + length // 2 + padding)
                tile.y = int(player_y - length // 2)

    def draw_player_shields(self, group, player_x, player_y, dirs):
        """
        dirs: ["UP", "LEFT", "RIGHT", "DOWN"]
        每条白线长 20px，厚度 2px，靠近玩家
        """

        if not hasattr(self, "shield_list"):
            self.shield_list = []

        # 删除旧 shields
        for s in self.shield_list:
            if s["tile"] in group:
                group.remove(s["tile"])
        self.shield_list.clear()

        length = 20
        thickness = 2
        padding = 2  # 靠近玩家
        px = int(player_x)
        py = int(player_y)

        offsets = {
            "UP":    (px - length // 2, py - length // 2 - padding, length, thickness),
            "DOWN":  (px - length // 2, py + length // 2 + padding, length, thickness),
            "LEFT":  (px - length // 2 - padding, py - length // 2, thickness, length),
            "RIGHT": (px + length // 2 + padding, py - length // 2, thickness, length)
        }

        for d in dirs:
            if d not in offsets:
                continue
            x, y, w, h = offsets[d]
            tile = self.draw_wall(group, int(x), int(y), int(w), int(h), color=1)
            self.shield_list.append({"tile": tile, "dir": d})
            
    def draw_score(self, parent_group, initial_score=0):
        """在左上角绘制分数"""
        if not hasattr(self, "score_group"):
            self.score_group = displayio.Group()
            parent_group.append(self.score_group)

        # 清空旧显示
        while len(self.score_group) > 0:
            self.score_group.pop()

        self.score = initial_score
        self.score_label = label.Label(
            terminalio.FONT,
            text=f"score: {self.score}",
            color=0xFFFFFF,
            anchored_position=(5, 5),  # 左上角
            anchor_point=(0, 0)
        )
        self.score_group.append(self.score_label)

    def update_score(self, new_score):
        """更新分数显示"""
        self.score = new_score
        self.score_label.text = f"score: {self.score}"
        
        
    def draw_countdown(self, parent_group, countdown_value):
        """在右上角显示倒计时数字，例如：countdown: 10"""
        if not hasattr(self, "countdown_group"):
            self.countdown_group = displayio.Group()
            parent_group.append(self.countdown_group)

        # 清空旧内容
        while len(self.countdown_group) > 0:
            self.countdown_group.pop()

        self.countdown = countdown_value
        self.countdown_label = label.Label(
            terminalio.FONT,
            text=f"countdown: {self.countdown}",
            color=0xFFFFFF,
            anchored_position=(SCREEN_WIDTH - 10, 10),  # 右上角
            anchor_point=(1, 0)  # 右对齐
        )
        self.countdown_group.append(self.countdown_label)

    def update_countdown(self, new_value):
        """更新倒计时显示"""
        self.countdown = new_value
        self.countdown_label.text = f"countdown: {self.countdown}"








