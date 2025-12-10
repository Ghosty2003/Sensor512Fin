# signal.py
class SignalController:
    def __init__(self, pixel):
        self.pixel = pixel

    def stop(self):
        self.pixel.fill((0, 0, 0))  # Turn off the light

    @staticmethod
    def direction_signal(food_dirs, enemy_dirs, controllers):
        """
        food_dirs:  List of directions with the most food (e.g., ["UP", "LEFT"])
        enemy_dirs: List of directions with the most enemies (e.g., ["LEFT", "RIGHT"])
        controllers: dict mapping direction -> SignalController object
        """

        # Turn off all lights
        for ctrl in controllers.values():
            ctrl.stop()

        # Iterate through each direction and set color
        for direction, ctrl in controllers.items():
            food_max = direction in food_dirs
            enemy_max = direction in enemy_dirs

            if food_max and enemy_max:
                ctrl.pixel.fill((255, 255, 0))  # Yellow light
                print(f"{direction}: Most food + enemies → Yellow")
            elif food_max:
                ctrl.pixel.fill((0, 255, 0))    # Green light
                print(f"{direction}: Most food → Green")
            elif enemy_max:
                ctrl.pixel.fill((255, 0, 0))    # Red light
                print(f"{direction}: Most enemies → Red")
            else:
                ctrl.pixel.fill((0, 0, 0))      # Light off
                print(f"{direction}: None → Off")
    
    def update_lights_by_lives(lives, controllers):
        """
        Light color based on remaining lives:
        >=5 white, <5 yellow, <3 red
        """

        if lives < 3:
            color = (255, 0, 0)   # Red
        elif lives < 5:
            color = (255, 255, 0) # Yellow
        else:
            color = (255, 255, 255)  # White

        for ctrl in controllers.values():
            ctrl.pixel.fill(color)

