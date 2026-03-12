from datetime import time, datetime, timedelta, date

global simulation_running, current_patient, simulation_start_time, simulation_hours
global bluetooth_socket, controller_type, controller_params

from simglucose.simulation.env import T1DSimEnv
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.actuator.pump import InsulinPump
from simglucose.sensor.cgm import CGMSensor
from simglucose.simulation.scenario import CustomScenario
from simglucose.simulation.scenario_gen import RandomScenario

from simglucose.controller.basal_bolus_ctrller import BBController
from simglucose.controller.pid_ctrller import PIDController

# from simglucose.controller.my_ctrller import MPCController
# from simglucose.controller.mpc_ctrller import MPCController

"""
    obs: Observation(CGM=125.37019394560548, BG=135.0788790930625) 
    action: ctrller_action(basal=0, bolus=0) 
    reward: 0.16197118037954328 
    done: False 
    info: {
        'sample_time': 5.0, 'patient_name': 'adolescent#001', 'meal': 0.0, 'patient_state': array([  0.        ,   0.        ,   0.        , 218.29656673, 137.61351317,   6.02354155,  50.88305117, 133.19420867, 110.10571246,   4.18776553,  25.7511215 , 124.7492827 ,226.26292309]), 
        'time': datetime.datetime(2025, 9, 12, 8, 0), 'bg': 135.0788790930625, 'lbgi': 0.0, 'hbgi': 1.163648069048848, 'risk': 1.163648069048848, 'insulin': 0.0, 'IOB':0.0}

    {'sample_time': np.float64(5.0), 'patient_name': 'adult#001', 'meal': np.float64(0.0), 'patient_state': array([ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  2.65370112e+02,
        1.62457097e+02,  5.50432649e+00, -1.22682368e-07,  1.00250000e+02,
        1.00250000e+02,  3.20762505e+00,  7.24341763e+01,  1.41153779e+02,        2.65370112e+02]), 'time': datetime.datetime(2025, 9, 26, 4, 20), 'bg': np.float64(138.56000006205576), 'lbgi': np.float64(0.0), 'hbgi': np.float64(1.5109019864155901), 'risk': np.float64(1.5109019864155901), 'insulin': np.float64(0.021122675006746666), 'iob': np.float64(1.2591508280479502e-09), 'cob': np.float64(0.0)}"""
now = datetime.now()
# start_time = datetime.combine(now.date(), datetime.min.time())

year = now.year
month = now.month
day = now.day
hour = 0
minute = 0
second = 0
default_date = date(year, month, day)
default_time = time(hour, minute, second)
start_time = datetime.combine(default_date, default_time)


import requests, concurrent.futures
import json, threading

executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)


def send_to_frontend(data):
    """发送数据到前端API"""
    try:
        # 发送到Flask API服务器
        url = "http://localhost:5000/api/glucose-data"

        response = requests.post(
            url,
            json=data,
            timeout=1,
        )
        if response.status_code == 200:
            print(
                f"数据发送成功 [{data.get('pname', 'unknown')}]: {data.get('timestamp', 'no-time')}"
            )
        else:
            print(f"数据发送失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"发送数据时出错: {e}")


try:

    # 使用选择的患者ID
    simulation_start_time = start_time
    simulation_hours = 1
    current_patient = "adult#001"
    # adult#001-adult#010, adolescent#001-adolescent#010, child#001-child#010
    patient = T1DPatient.withName(current_patient)
    sensor = CGMSensor.withName("GuardianRT", seed=1)
    # Dexcom, GuardianRT, Navigator
    pump = InsulinPump.withName("Insulet")

    # 使用全局变量中的开始时间
    start_time = simulation_start_time
    print(f"使用仿真开始时间: {start_time}")

    # 根据仿真时长创建场景
    hours = simulation_hours
    print(f"仿真时长设置为: {hours}小时")

    # 这里设置餐食，（7点，餐食量g/sample_time），前端暂时没整设置餐食的。
    # 这里设置餐食：使用程序生成方式，重复 days 天（每天天的餐食一致）
    # 每项为 (小时, 餐食量 g)
    daily_meals = [(7, 45), (12, 30), (16, 15), (18, 80), (23, 10)]
    days = 3  # 例如：3 天
    scen = []
    for d in range(days):
        for hour, amount in daily_meals:
            # 使用 timedelta 表示相对于 start_time 的偏移
            scen.append((timedelta(days=d, hours=hour), amount))
    # scen=['custom']

    # 例如：6点开始仿真想要7点进餐，则餐食时间需要调整为：（1，45）
    scenario = CustomScenario(start_time=start_time, scenario=scen)
    env = T1DSimEnv(patient, sensor, pump, scenario)
    controller = BBController()
    # controller = PIDController(0.003, 0, 0.003, 140)
    # controller = PIDController(0.00212544, 1.02805e-05, 3.53603e-05, 140)
    # adult#001(0.00212544, 1.02805e-05, 3.53603e-05)
    # adult#002(0.00684571, 5.61543e-06, 0.000273128)
    # adult#003(0.00212544, 1.02805e-05, 3.53603e-05)
    # adult#004(0.00212544, 1.02805e-05, 3.53603e-05)
    # adult#005(0.00212544, 1.02805e-05, 3.53603e-05)
    # adult#006(0.00212544, 1.02805e-05, 3.53603e-05)
    # # 根据控制器类型创建相应的控制器

    # 初始化环境
    obs, reward, done, info = env.reset()
    hours = simulation_hours
    # 5->12->1h; 3->20->1h; 1->60->1h
    total_steps = int(12 * 24 * days)  # 假设每小时20步（每3分钟1步）
    current_step = 0
    sequence_id = 0

    while current_step < total_steps:
        env.render(close=False)
        action = controller.policy(obs, reward, done, **info)
        # print('Insu',insulin)
        obs, reward, done, info = env.step(action)
        # print(info)
        # print(obs[0], "===", info["insulin"])

        # 准备数据并添加序列号
        datas = {
            "pname": info["patient_name"],
            "timestamp": info["time"].isoformat(),
            "CGM": float(obs[0]),
            "BG": float(obs[1]),
            "meal": float(info["meal"]),
            "cob": float(info["cob"]),
            "basal": float(action.basal),
            "bolus": float(action.bolus),
            "insulin": float(info["insulin"]),
            "iob": float(info["iob"]),
            "seq_id": sequence_id,  # 添加序列号
        }

        # 发送数据到前端
        send_action = executor.submit(send_to_frontend, datas)
        current_step += 1
        sequence_id += 1

        # 仿真时长达到，自动停止
    if current_step >= total_steps or done:
        simulation_running = False
        # if bluetooth_socket:
        #     try:
        #         print('发送停止信号')
        #     except Exception as e:
        #         print(f"发送停止信号错误: {e}")
        print("仿真时长达到，自动停止")

except Exception as e:
    print(f"仿真过程中出错: {e}")
    import traceback

    traceback.print_exc()
finally:
    simulation_running = False
    print("over")
