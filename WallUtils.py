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
        """Draw a single wall"""
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
        # If life_group does not exist, create it
        if not hasattr(self, "life_group"):
            self.life_group = displayio.Group()
            parent_group.append(self.life_group)

        # Clear old life icons
        while len(self.life_group) > 0:
            self.life_group.pop()

        # ❤️ 4x4 heart pixel pattern (1 = lit, 0 = background)
        heart_pattern = [
            [1, 0, 0, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [0, 1, 1, 0]
        ]

        for i in range(lives):
            bmp = displayio.Bitmap(4, 4, 2)
            pal = displayio.Palette(2)
            pal[0] = 0x000000  # Black (background)
            pal[1] = 0xFFFFFF  # White (heart)

            # Write heart pixels
            for y in range(4):
                for x in range(4):
                    bmp[x, y] = heart_pattern[y][x]

            tile = displayio.TileGrid(bmp, pixel_shader=pal)

            tile.x = SCREEN_WIDTH - 10 - i * 6
            tile.y = SCREEN_HEIGHT - 17
            self.life_group.append(tile)



    # ================================
    # Generate random directions
    # ================================
    def simple_sample(self, pool, k):
        pool_copy = list(pool)
        result = []
        for _ in range(k):
            idx = random.randrange(len(pool_copy))
            result.append(pool_copy.pop(idx))
        return result

    def generate_random_directions(self, last_dir):
        must_include = OPPOSITE[last_dir]  # Opposite direction must appear
        pool = [d for d in DIRECTIONS if d != must_include]  # Exclude the direction the player hit
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
    # Draw blocking walls
    # ================================
    def draw_block_walls(self, group, allowed_dirs):
        """Draw blocking walls based on allowed_dirs"""
        # Remove old walls
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
    # Draw white protective lines around player
    # ================================
    def update_shields_position(self, player_x, player_y):
        """Move existing shields based on player's current position"""
        if not hasattr(self, "shield_list"):
            return

        length = 20
        thickness = 2
        padding = 2  # Distance from player

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
        Each white line is 20px long, 2px thick, close to the player
        """

        if not hasattr(self, "shield_list"):
            self.shield_list = []

        # Remove old shields
        for s in self.shield_list:
            if s["tile"] in group:
                group.remove(s["tile"])
        self.shield_list.clear()

        length = 20
        thickness = 2
        padding = 2  # Close to the player
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
        """Draw score in the top-left corner"""
        if not hasattr(self, "score_group"):
            self.score_group = displayio.Group()
            parent_group.append(self.score_group)

        # Clear old content
        while len(self.score_group) > 0:
            self.score_group.pop()

        self.score = initial_score
        self.score_label = label.Label(
            terminalio.FONT,
            text=f"score: {self.score}",
            color=0xFFFFFF,
            anchored_position=(5, 5),  # Top-left corner
            anchor_point=(0, 0)
        )
        self.score_group.append(self.score_label)

    def update_score(self, new_score):
        """Update score display"""
        self.score = new_score
        self.score_label.text = f"score: {self.score}"
        
        
    def draw_countdown(self, parent_group, countdown_value):
        """Display countdown number at top-right, e.g.: countdown: 10"""
        if not hasattr(self, "countdown_group"):
            self.countdown_group = displayio.Group()
            parent_group.append(self.countdown_group)

        # Clear old content
        while len(self.countdown_group) > 0:
            self.countdown_group.pop()

        self.countdown = countdown_value
        self.countdown_label = label.Label(
            terminalio.FONT,
            text=f"{self.countdown}",
            color=0xFFFFFF,
            anchored_position=(SCREEN_WIDTH - 8, 8),  # Top-right corner
            anchor_point=(1, 0)  # Right aligned
        )
        self.countdown_group.append(self.countdown_label)

    def update_countdown(self, new_value):
        """Update countdown display"""
        self.countdown = new_value
        self.countdown_label.text = f"{self.countdown}"

