import math

# 系统参数
CONCENTRATION = 100  # U/ml，胰岛素浓度
SYRINGE_DIAMETER = 10  # mm，注射器直径
A = math.pi * (SYRINGE_DIAMETER / 2) ** 2  # mm²，横截面积
STEPS_PER_REV = 6400  # 每转步数
STEP_DISTANCE = 1.0 / STEPS_PER_REV  # mm/步
TIME_STEP = 1  # 每秒

# GPIO引脚
STEP_PIN = 24  # 脉冲引脚
DIR_PIN = 17  # 方向引脚

Plus_Button = 10
Decr_Button = 2

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "raspbreey",
    "db": "1Patients_Datas",
    "charset": "utf8mb4",
}

# 蓝牙配置
BT_PORT = 2
