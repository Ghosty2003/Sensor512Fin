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
        

    def read_filtered(self):
        x_raw, y_raw, z_raw = self.accelerometer.acceleration
        self.xFiltered = self.alpha * x_raw + (1 - self.alpha) * self.xFiltered
        self.yFiltered = self.alpha * y_raw + (1 - self.alpha) * self.yFiltered
        self.zFiltered = self.alpha * z_raw + (1 - self.alpha) * self.zFiltered
        return self.xFiltered, self.yFiltered, self.zFiltered



if __name__ == "__main__":
    # 测试代码
    ema_acc = EMAFilterAccelerometer(alpha=0.2)
    print("Starting EMA low-pass filtering...\n")
    while True:
        x, y, z = ema_acc.read_filtered()
        print(f"Filtered X:{x:.2f} Y:{y:.2f} Z:{z:.2f}")
        time.sleep(0.05)
