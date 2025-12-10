import board
import busio
import adafruit_adxl34x
import time

# filter.py
class EMAFilterAccelerometer:
    def __init__(self, accelerometer, alpha=0.2):
        """
        accelerometer: initialized adafruit_adxl34x.ADXL345 object
        """
        self.accelerometer = accelerometer
        self.alpha = alpha

        # Initialize filtered values
        x_raw, y_raw, z_raw = self.accelerometer.acceleration
        self.xFiltered = x_raw
        self.yFiltered = y_raw
        self.zFiltered = z_raw
        
        # Store previous acceleration values for shake detection
        self.prev_x = self.xFiltered
        self.prev_y = self.yFiltered
        self.prev_z = self.zFiltered
        

    def read_filtered(self):
        x_raw, y_raw, z_raw = self.accelerometer.acceleration
        self.xFiltered = self.alpha * x_raw + (1 - self.alpha) * self.xFiltered
        self.yFiltered = self.alpha * y_raw + (1 - self.alpha) * self.yFiltered
        self.zFiltered = self.alpha * z_raw + (1 - self.alpha) * self.zFiltered
        return self.xFiltered, self.yFiltered, self.zFiltered
    
    def detect_shake(self, threshold=1.0, x=None, y=None, z=None):
        """
        threshold: acceleration change threshold in m/s^2
        x, y, z: filtered values; if provided, skip re-reading
        """
        if x is None or y is None or z is None:
            x, y, z = self.read_filtered()
        
        dx = abs(x - self.prev_x)
        dy = abs(y - self.prev_y)
        dz = abs(z - self.prev_z)

        self.prev_x = x
        self.prev_y = y
        self.prev_z = z

        return dx > threshold or dy > threshold or dz > threshold



if __name__ == "__main__":
    # Initialize I2C and accelerometer
    i2c = busio.I2C(board.SCL, board.SDA)
    accelerometer = adafruit_adxl34x.ADXL345(i2c)

    # Initialize EMA filter
    ema_acc = EMAFilterAccelerometer(accelerometer, alpha=0.2)

    print("Starting EMA low-pass filtering with shake detection...\n")
    while True:
        x, y, z = ema_acc.read_filtered()
        shake = ema_acc.detect_shake(threshold=1.0, x=x, y=y, z=z)
        print(f"Filtered X:{x:.2f} Y:{y:.2f} Z:{z:.2f}  Shake:{shake}")
        time.sleep(0.05)

