import random
import displayio

class Food:
    def __init__(self, group, screen_width, screen_height, size=2, points=1):
        """
        group: displayio.Group, the display group
        screen_width, screen_height: screen dimensions, used for random placement
        size: size of the food
        points: score gained when eaten
        """
        self.group = group
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.size = size
        self.points = points

        self.bitmap = displayio.Bitmap(size, size, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000  # background black
        palette[1] = 0xFFFFFF  # food color
        self.tile = displayio.TileGrid(self.bitmap, pixel_shader=palette)

        # randomly generate initial position
        self.x = random.randint(0, screen_width - size)
        self.y = random.randint(0, screen_height - size)
        self.tile.x = self.x
        self.tile.y = self.y

        # initialize food pixels
        for i in range(size):
            for j in range(size):
                self.bitmap[i, j] = 1

        self.group.append(self.tile)
        self.eaten = False

    def check_collision(self, player_x, player_y, player_size):
        """
        Check if the player collides with the food.
        player_x, player_y: player's top-left coordinates
        player_size: player's width/height (size of the ball)
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
        """Mark as eaten and remove from display"""
        if not self.eaten:
            if self.tile in self.group:
                self.group.remove(self.tile)
            self.eaten = True

    def respawn(self):
        """Respawn randomly (optional)"""
        self.eaten = False
        self.x = random.randint(0, self.screen_width - self.size)
        self.y = random.randint(0, self.screen_height - self.size)
        self.tile.x = self.x
        self.tile.y = self.y
        if self.tile not in self.group:
            self.group.append(self.tile)

