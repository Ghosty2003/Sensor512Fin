import displayio
import random

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
        # 可选方向 = 除了 last_dir 的方向
        banned = OPPOSITE[last_dir]
        pool = [d for d in DIRECTIONS if d != banned]

        r = random.random()

        if r < 0.33:
            # 1 个方向
            return [random.choice(pool)]
        elif r < 0.7:
            # 2 个方向（从不包含 last_dir）
            return self.simple_sample(pool, 2)
        else:
            # 3 个方向（从不包含 last_dir）
            return self.simple_sample(pool, 3)

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

