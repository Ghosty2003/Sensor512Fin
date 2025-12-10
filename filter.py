import board
import busio
import adafruit_adxl34x
import time

# filter.py
class EMAFilterAccelerometer:
    def __init__(self, accelerometer, alpha=0.2):
        """
        accelerometer: 已初始化的 adafruit_adxl34x.ADXL345 对象
        """
        self.accelerometer = accelerometer
        self.alpha = alpha

        # 初始化过滤值
        x_raw, y_raw, z_raw = self.accelerometer.acceleration
        self.xFiltered = x_raw
        self.yFiltered = y_raw
        self.zFiltered = z_raw
        
        # 保存上一次的加速度值用于检测 shake
        self.prev_x = x_raw
        self.prev_y = y_raw
        self.prev_z = z_raw
        

    def read_filtered(self):
        x_raw, y_raw, z_raw = self.accelerometer.acceleration
        self.xFiltered = self.alpha * x_raw + (1 - self.alpha) * self.xFiltered
        self.yFiltered = self.alpha * y_raw + (1 - self.alpha) * self.yFiltered
        self.zFiltered = self.alpha * z_raw + (1 - self.alpha) * self.zFiltered
        return self.xFiltered, self.yFiltered, self.zFiltered
    
    def detect_shake(self, threshold=1.0, x=None, y=None, z=None):
        """
        threshold: 加速度变化阈值，单位 m/s^2
        x,y,z: 已读取的滤波值，如果提供则不用再读取
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
    # 初始化 I2C 和加速度计
    i2c = busio.I2C(board.SCL, board.SDA)
    accelerometer = adafruit_adxl34x.ADXL345(i2c)

    # 初始化 EMA 滤波器
    ema_acc = EMAFilterAccelerometer(accelerometer, alpha=0.2)

    print("Starting EMA low-pass filtering with shake detection...\n")
    while True:
        x, y, z = ema_acc.read_filtered()
        shake = ema_acc.detect_shake(threshold=1.0, x=x, y=y, z=z)
        print(f"Filtered X:{x:.2f} Y:{y:.2f} Z:{z:.2f}  Shake:{shake}")
        time.sleep(0.05)


