import random
import displayio

class Food:
    def __init__(self, group, screen_width, screen_height, size=2, points=1):
        """
        group: displayio.Group，显示组
        screen_width, screen_height: 屏幕宽高，用于随机生成位置
        size: 豆子大小
        points: 吃掉后的加分
        """
        self.group = group
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.size = size
        self.points = points

        self.bitmap = displayio.Bitmap(size, size, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000  # 背景黑
        palette[1] = 0xFFFFFF      # 豆子颜色
        self.tile = displayio.TileGrid(self.bitmap, pixel_shader=palette)

        # 随机生成初始位置
        self.x = random.randint(0, screen_width - size)
        self.y = random.randint(0, screen_height - size)
        self.tile.x = self.x
        self.tile.y = self.y

        # 初始化豆子像素
        for i in range(size):
            for j in range(size):
                self.bitmap[i, j] = 1

        self.group.append(self.tile)
        self.eaten = False

    def check_collision(self, player_x, player_y, player_size):
        """
        检查玩家是否碰到豆子
        player_x, player_y: 玩家左上角坐标
        player_size: 玩家宽高（球的大小）
        """
        if self.eaten:
            return False

        f_left = self.x
        f_top = self.y
        f_right = self.x + self.size
        f_bottom = self.y + self.size

        p_left = player_x
        p_top = player_y
        p_right = player_x + player_size
        p_bottom = player_y + player_size

        if (f_left < p_right and f_right > p_left and
            f_top < p_bottom and f_bottom > p_top):
            self.eat()
            return True

        return False

    def eat(self):
        """被吃掉，移除显示"""
        if not self.eaten:
            if self.tile in self.group:
                self.group.remove(self.tile)
            self.eaten = True

    def respawn(self):
        """随机重生（可选）"""
        self.eaten = False
        self.x = random.randint(0, self.screen_width - self.size)
        self.y = random.randint(0, self.screen_height - self.size)
        self.tile.x = self.x
        self.tile.y = self.y
        if self.tile not in self.group:
            self.group.append(self.tile)

