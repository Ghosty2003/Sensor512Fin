# signal.py
class SignalController:
    def __init__(self, pixel):
        self.pixel = pixel

    def stop(self):
        self.pixel.fill((0, 0, 0))  # 关灯

    @staticmethod
    def direction_signal(food_dirs, enemy_dirs, controllers):
        """
        food_dirs:  食物最多的方向列表（如 ["UP", "LEFT"]）
        enemy_dirs: 敌人最多的方向列表（如 ["LEFT", "RIGHT"]）
        controllers: dict 方向 -> SignalController 对象
        """

        # 停掉所有灯光
        for ctrl in controllers.values():
            ctrl.stop()

        # 遍历每个方向，设置颜色
        for direction, ctrl in controllers.items():
            food_max = direction in food_dirs
            enemy_max = direction in enemy_dirs

            if food_max and enemy_max:
                ctrl.pixel.fill((255, 255, 0))  # 黄灯
                print(f"{direction}: 食物+敌人最多 → 黄灯")
            elif food_max:
                ctrl.pixel.fill((0, 255, 0))    # 绿灯
                print(f"{direction}: 食物最多 → 绿灯")
            elif enemy_max:
                ctrl.pixel.fill((255, 0, 0))    # 红灯
                print(f"{direction}: 敌人最多 → 红灯")
            else:
                ctrl.pixel.fill((0, 0, 0))      # 灭灯
                print(f"{direction}: 无 → 灭灯")
    
    def update_lights_by_lives(lives, controllers):
        """
        根据生命值亮灯：>=5 白色, <5 黄色, <3 红色
        """

        if lives < 3:
            color = (255, 0, 0)   # 红
        elif lives < 5:
            color = (255, 255, 0) # 黄
        else:
            color = (255, 255, 255)  # 白

        for ctrl in controllers.values():
            ctrl.pixel.fill(color)

