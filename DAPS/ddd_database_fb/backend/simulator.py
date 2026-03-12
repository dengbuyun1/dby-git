from database import save_simulation_data
from simglucose.simulation.env import T1DSimEnv
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.actuator.pump import InsulinPump
from simglucose.sensor.cgm import CGMSensor
from simglucose.simulation.scenario import CustomScenario
from simglucose.simulation.scenario_gen import RandomScenario

from simglucose.controller.base import Action

import base
import asyncio
import json
import websockets
import logging
import os
import csv
from datetime import time, datetime, timedelta, date
from vpatient_matching import VPatientMatcher  # 新增导入
from personalizer import Personalizer
import pandas as pd

from database import (
    init_db_pool,
    close_db_pool,
    create_new_simulation,
    create_new_real_patient,  # 新增
    get_all_real_patients,  # 新增
    save_simulation_data,
    update_simulation_status,
    get_all_simulations,
    get_simulation_data,
    get_simulation_info,
    delete_simulation,
    delete_real_patient,  # 新增
    is_db_connected,
)

# 导入TCP客户端
from tcp_client import create_bridge
from csv_data_provider import CSVDataProvider

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TCPSimulator")

import random

# 初始化 CSV 数据提供者
csv_provider = CSVDataProvider(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "processed_state",
    )
)
replay_running = False
REAL_PATIENT_DATASETS = {}  # 存储患者ID到CSV文件的映射

# 初始化虚拟患者匹配器
matcher = VPatientMatcher()

# ===========================================
# TCP连接配置 - 直接在这里修改树莓派的IP地址和端口
# ===========================================
RASPBERRY_PI_IP = "192.168.137.4"  # 修改为你的树莓派IP地址
RASPBERRY_PI_PORT = 8888  # 树莓派TCP服务端口
# ===========================================

# 全局状态
clients = set()
simulation_running = False  # 控制仿真是否运行
current_simulation_id = None  # 当前仿真ID
bluetooth_bridge = None  # TCP桥接对象（变量名保留兼容性）

###一些参数
now = datetime.now()
year = now.year
month = now.month
day = now.day
hour = 0
minute = 0
second = 0
default_date = date(year, month, day)
default_time = time(hour, minute, second)

start_time = datetime.combine(default_date, default_time)
person = "xiaoming"
sensor = "Dexcom"  # Dexcom-5-12, GuardianRT-3-20, Navigator-1-60
sample_time = 3
mini_step = 20
pump = "Insulet"
controller = "remote"
simulate_hours = 1

# PID 参数 (Moved to base.py)


# 患者详细信息
patient_id = None
patient_name = None
patient_type = None
patient_age = None
patient_gender = None
patient_blood_type = None
simulate_times = sample_time * simulate_hours

# 餐食设置
meal_mode = "random"  # 'random' 或 'custom'
meal_custom_type = "daily"  # 'daily' 或 'manual'
meal_repeat_days = 3
meal_daily_meals = []
meal_manual_meals = []

# daily_meals = [(7, 45), (12, 30), (16, 15), (18, 80), (23, 10)]
# scen = []
# for d in range(simulate_hours * simple_time):
#     for hour, amount in daily_meals:
#         # 使用 timedelta 表示相对于 start_time 的偏移
#         scen.append((timedelta(days=d, hours=hour), amount))
base_datas = [start_time, person, sensor, pump, controller, simulate_times]
###一些参数


def build_bluetooth_payload(info: dict, obs) -> str | None:
    """Create the payload sent to the Raspberry Pi controller."""

    try:
        pname = info.get("patient_name", "unknown")
        timestamp = info.get("time")
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.isoformat()
        else:
            timestamp_str = datetime.now().isoformat()

        bg = float(info.get("bg", getattr(obs, "BG", 0.0)))
        cgm = float(getattr(obs, "CGM", info.get("CGM", 0.0)))
        meal = float(info.get("meal", 0.0))

        # 构建 JSON payload
        payload = {
            "patient_name": pname,
            "timestamp": timestamp_str,
            "bg": bg,
            "cgm": cgm,
            "cho": meal,
            "controller": controller,  # 全局变量
            "kp": base.kp,
            "ki": base.ki,
            "kd": base.kd,
            "target": base.target,
            # New Controller Parameters
            "g_lower": base.g_lower,
            "g_upper": base.g_upper,
            "g_safety": base.g_safety,
            "basal_rate": base.basal_rate,
            "pred_horizon_min": base.pred_horizon_min,
            "control_horizon_min": base.control_horizon_min,
            "u_min": base.u_min,
            "u_max": base.u_max,
            "hypo_guard": base.hypo_guard,
            "soft_upper": base.soft_upper,
            "basal_floor": base.basal_floor,
            "q_bg": base.q_bg,
            "q_low": base.q_low,
            "w_under": base.w_under,
            "w_over": base.w_over,
        }
        return json.dumps(payload)

    except (TypeError, ValueError) as exc:
        logger.warning("蓝牙载荷构建失败: %s | info=%s", exc, info)
        return None


async def request_remote_action(info: dict, obs) -> tuple[Action, dict] | None:
    if not bluetooth_bridge:
        return None

    payload = build_bluetooth_payload(info, obs)
    if not payload:
        return None

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, bluetooth_bridge.request, payload, 2.0)

    if not response:
        return None

    data = {}
    try:
        # 尝试解析JSON
        try:
            data = json.loads(response)
            basal = float(data.get("basal", 0.0))
            bolus = float(data.get("bolus", 0.0))
        except json.JSONDecodeError:
            # 兼容旧格式 CSV
            insulin_str, basal_str, bolus_str = response.split(",")
            basal = float(basal_str)
            bolus = float(bolus_str)
            data = {"basal": basal, "bolus": bolus, "insulin": float(insulin_str)}
        # insulin_str is currently unused but kept for debugging
    except ValueError:
        logger.warning("蓝牙返回格式异常: %s", response)
        return None

    return Action(basal=basal, bolus=bolus), data


# def get_simulation_params():
#     """
#     获取最新的仿真参数，这些参数会实时反映前端操作的影响
#     返回值顺序：simulation_running, year, month, day, hour, minute, second, person, sensor, pump, controller, start_time, base_datas, simulate_hours, sample_time, simulate_times, current_simulation_id, patient_id, patient_name, patient_type, patient_age, patient_gender, patient_blood_type
#     """
#     return base.base_params()
#
#
# # 为了兼容性，保留原有的全局变量赋值（但这些是静态的，建议使用 get_simulation_params() 获取实时值）
# global simulation_running, year, month, day, hour, minute, second, person, sensor, pump, controller, start_time, base_datas, simulate_hours, sample_time, simulate_times, current_simulation_id
# global patient_id, patient_name, patient_type, patient_age, patient_gender, patient_blood_type
#
# (
#     simulation_running,
#     year,
#     month,
#     day,
#     hour,
#     minute,
#     second,
#     person,
#     sensor,
#     pump,
#     controller,
#     start_time,
#     base_datas,
#     simulate_hours,
#     sample_time,
#     mini_step,
#     simulate_times,
#     current_simulation_id,
#     patient_id,
#     patient_name,
#     patient_type,
#     patient_age,
#     patient_gender,
#     patient_blood_type,
# ) = base.base_params()


async def simulator():
    global simulation_running, year, month, day, hour, minute, second, person, sensor, pump, controller, start_time, base_datas, simulate_hours, sample_time, mini_step, simulate_times, current_simulation_id
    global patient_id, patient_name, patient_type, patient_age, patient_gender, patient_blood_type
    global kp, ki, kd, target
    global meal_mode, meal_custom_type, meal_repeat_days, meal_daily_meals, meal_manual_meals
    global bluetooth_bridge
    global replay_running

    logger.info("仿真器已启动，等待启动命令...")

    while True:
        # 等待 simulation_running 或 replay_running 被设置为 True
        while not simulation_running and not replay_running:
            await asyncio.sleep(0.5)

        if replay_running:
            logger.info("开始 CSV 回放模式...")
            while replay_running:
                data = csv_provider.get_next_data()
                if data:
                    # 准备硬件数据默认值
                    hardware_data = {
                        "pwmDuty": 0,
                        "pwmFreq": 1000,
                        "motorPos": 0,
                        "motorStatus": "Stopped",
                        "direction": "Forward",
                    }
                    tcp_status = "disconnected"

                    # 如果TCP桥接已连接，发送数据到树莓派
                    if (
                        bluetooth_bridge
                        and bluetooth_bridge.enabled
                        and bluetooth_bridge.is_connected
                    ):
                        tcp_status = "connected"
                        try:
                            # 构造发送给树莓派的数据
                            payload = {
                                "patient_name": str(patient_id),
                                "timestamp": data["timestamp"],
                                "bg": data["bg"],
                                "cgm": data["cgm"],
                                "cho": data["cho"],
                                "insulin": data["insulin"],  # 发送胰岛素值
                                "iob": data["iob"],
                                "cob": data["cob"],
                                "controller": "replay",
                            }

                            loop = asyncio.get_running_loop()
                            # 发送请求并等待响应
                            response_str = await loop.run_in_executor(
                                None, bluetooth_bridge.request, json.dumps(payload), 0.5
                            )

                            if response_str:
                                response = json.loads(response_str)
                                if "hardware" in response:
                                    hardware_data.update(response["hardware"])
                        except Exception as e:
                            logger.error(f"TCP通信错误: {e}")

                    # Broadcast data
                    msg = {
                        "type": "base_data",
                        "timestamp": data["timestamp"],
                        "bg": data["bg"],
                        "cgm": data["cgm"],
                        "cho": data["cho"],
                        "cob": data["cob"],
                        "insulin": data["insulin"],
                        "iob": data["iob"],
                        "db_status": (
                            "connected" if is_db_connected() else "disconnected"
                        ),
                        "tcp_status": tcp_status,
                        "hardware_data": hardware_data,
                    }

                    if clients:
                        message = json.dumps(msg)
                        await asyncio.gather(
                            *[client.send(message) for client in clients],
                            return_exceptions=True,
                        )

                    await asyncio.sleep(1)  # 1 second per data point
                else:
                    logger.info("CSV 回放结束")
                    replay_running = False
            continue

        logger.info("收到启动信号，开始初始化仿真环境...")

        # 初始化 CSV 保存
        DATA_DIR = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "DATA",
        )
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"simulation_data_{timestamp_str}.csv"
        csv_filepath = os.path.join(DATA_DIR, csv_filename)

        csv_file = open(csv_filepath, "w", newline="")
        csv_writer = csv.writer(csv_file)
        # Header: datatime/bg/cgm/insulin/cho/下位机的pwm/下位机电机的推动距离
        csv_writer.writerow(
            ["datetime", "bg", "cgm", "insulin", "cho", "pwm", "motor_pos"]
        )
        logger.info(f"Created simulation data file: {csv_filepath}")

        # 仿真开始时才创建环境
        simulation_hours = simulate_hours
        current_patient = person  # 使用全局变量 person
        patient = T1DPatient.withName(current_patient)
        Sensor = CGMSensor.withName(sensor, seed=1)
        Pump = InsulinPump.withName(pump)
        Start_time = start_time
        Hours = 24

        # 用于缓存当前仿真的patient_id，避免每次都查询数据库
        cached_patient_id = None

        # 根据前端设置生成餐食场景
        scen = []

        if meal_mode == "random":
            # 随机餐食模式
            scenario = RandomScenario(start_time=Start_time, seed=1)
            print(f"使用随机餐食模式")
        else:
            # 自定义餐食模式
            if meal_custom_type == "daily":
                # 每日重复模式
                if meal_daily_meals:
                    for d in range(meal_repeat_days):
                        for meal in meal_daily_meals:
                            hour_val = meal.get("hour", 0)
                            amount_val = meal.get("amount", 0)
                            scen.append((timedelta(days=d, hours=hour_val), amount_val))
                    print(
                        f"使用每日重复餐食: {len(meal_daily_meals)} 次/天, 重复 {meal_repeat_days} 天"
                    )
                else:
                    # 如果没有设置，使用默认餐食
                    daily_meals = [(7, 45), (12, 30), (16, 15), (18, 80), (23, 10)]
                    for d in range(3):
                        for hour_val, amount_val in daily_meals:
                            scen.append((timedelta(days=d, hours=hour_val), amount_val))
                    print(f"使用默认每日餐食")
            else:
                # 完全自定义模式
                if meal_manual_meals:
                    for meal in meal_manual_meals:
                        hour_val = meal.get("hour", 0)
                        amount_val = meal.get("amount", 0)
                        scen.append((timedelta(hours=hour_val), amount_val))
                    print(f"使用完全自定义餐食: {len(meal_manual_meals)} 个时间点")
                else:
                    print(f"自定义餐食为空，使用无餐食场景")

            scenario = CustomScenario(start_time=Start_time, scenario=scen)

        env = T1DSimEnv(patient, Sensor, Pump, scenario)

        obs, reward, done, info = env.reset()
        # 计算总步数：总分钟数 / 采样间隔
        total_steps = int(simulate_hours * 60 / sample_time)
        current_step = 0
        sequence_id = 0
        bg_prev = None
        last_action = Action(basal=0.0, bolus=0.0)

        print(
            f"sensor: {sensor}, pump: {pump}, sample_time: {sample_time}, mini_step: {mini_step}, controller: {controller}, patient: {current_patient}, start_time: {Start_time}, hours: {Hours}, total_steps: {total_steps}"
        )

        # 仿真循环
        while current_step < total_steps:
            try:
                if simulation_running:
                    env.render(close=True)

                    # 添加日志：记录发送给树莓派的数据
                    payload = build_bluetooth_payload(info, obs)
                    if payload:
                        logger.info(f"Sending to Pi: {payload}")

                    remote_result = await request_remote_action(info, obs)
                    pi_data = {}
                    if remote_result is None:
                        action = last_action
                    else:
                        action, pi_data = remote_result
                        last_action = action

                    step_result = env.step(action)
                    obs, reward, done, info = step_result

                    obs_bg = getattr(obs, "BG", None)
                    info_bg = info.get("bg") if isinstance(info, dict) else None
                    current_bg = float(
                        info_bg
                        if info_bg is not None
                        else (obs_bg if obs_bg is not None else 0.0)
                    )

                    obs_cgm = getattr(obs, "CGM", None)
                    info_cgm = info.get("cgm") if isinstance(info, dict) else None

                    patient_name_value = info.get("patient_name", current_patient)
                    timestamp_value = info.get("time", datetime.now())
                    if isinstance(timestamp_value, datetime):
                        timestamp_iso = timestamp_value.isoformat()
                    else:
                        timestamp_iso = datetime.now().isoformat()

                    datas = {
                        "type": "simulation_data",  # 添加消息类型，适配前端
                        "pname": patient_name_value,
                        "timestamp": timestamp_iso,
                        "CGM": float(
                            info_cgm
                            if info_cgm is not None
                            else (obs_cgm if obs_cgm is not None else 0.0)
                        ),
                        "BG": current_bg,
                        "meal": float(info.get("meal", 0.0)),
                        "cob": float(info.get("cob", 0.0)),
                        "basal": float(action.basal),
                        "bolus": float(action.bolus),
                        "insulin": float(pi_data.get("insulin", 0.0)),
                        "iob": float(pi_data.get("iob", 0.0)),
                        "seq_id": sequence_id,
                        # 添加前端需要的字段映射
                        "bg": current_bg,
                        "cgm": float(
                            info_cgm
                            if info_cgm is not None
                            else (obs_cgm if obs_cgm is not None else 0.0)
                        ),
                        "cho": float(info.get("meal", 0.0)),
                        # 添加数据库连接状态
                        "db_status": (
                            "connected" if is_db_connected() else "disconnected"
                        ),
                        # 添加TCP连接状态
                        "tcp_status": (
                            "connected"
                            if (
                                bluetooth_bridge
                                and bluetooth_bridge.enabled
                                and bluetooth_bridge.is_connected
                            )
                            else "disconnected"
                        ),
                        # 添加硬件数据 (从TCP桥接获取)
                        "hardware_data": (
                            bluetooth_bridge.last_hardware_data
                            if (
                                bluetooth_bridge and bluetooth_bridge.last_hardware_data
                            )
                            else {
                                "pwmDuty": 0,
                                "pwmFreq": 1000,
                                "motorPos": 0,
                                "motorStatus": "Stopped",
                                "direction": "Forward",
                            }
                        ),
                    }

                    # Write to CSV
                    try:
                        pwm_val = datas["hardware_data"].get("pwmDuty", 0)
                        # 树莓派返回的是 actualDelivery (实际推注量 U)，对应用户的"推动距离"需求
                        # 原代码尝试获取 motorPos 但树莓派未返回该字段，导致为0
                        motor_pos_val = datas["hardware_data"].get("actualDelivery", 0)
                        csv_writer.writerow(
                            [
                                datas["timestamp"],
                                datas["bg"],
                                datas["cgm"],
                                datas["insulin"],
                                datas["cho"],
                                pwm_val,
                                motor_pos_val,
                            ]
                        )
                        csv_file.flush()
                    except Exception as e:
                        logger.error(f"Error writing to CSV: {e}")

                    if current_simulation_id is not None:
                        try:
                            if cached_patient_id is None:
                                sim_info = await get_simulation_info(
                                    current_simulation_id
                                )
                                if sim_info and sim_info.get("patient_id"):
                                    cached_patient_id = sim_info["patient_id"]
                                    logger.info(
                                        "从数据库获取 patient_id: %s", cached_patient_id
                                    )
                                else:
                                    cached_patient_id = f"VP{current_simulation_id:03d}"
                                    logger.warning(
                                        "未能从数据库获取 patient_id，使用默认值: %s",
                                        cached_patient_id,
                                    )

                            await save_simulation_data(
                                simulation_id=current_simulation_id,
                                time=info["time"],
                                bg=current_bg,
                                cgm=float(datas["CGM"]),
                                bg_prev=(
                                    bg_prev if bg_prev is not None else current_bg
                                ),
                                cho=float(datas["meal"]),
                                cob=float(datas["cob"]),
                                insulin=float(datas["insulin"]),
                                basal=float(action.basal),
                                bolus=float(action.bolus),
                                iob=float(datas["iob"]),
                            )

                            bg_prev = current_bg

                        except Exception as db_error:
                            logger.error(f"保存数据到数据库失败: {db_error}")

                    if clients:
                        # Debug log for insulin value
                        # logger.info(f"Sending data to frontend - Insulin: {datas['insulin']}, IOB: {datas['iob']}")
                        message = json.dumps(datas)
                        await asyncio.gather(
                            *[client.send(message) for client in clients],
                            return_exceptions=True,
                        )

                    await asyncio.sleep(0.01)

                    current_step += 1
                    sequence_id += 1

                    if current_step >= total_steps or done:
                        simulation_running = False
                        cached_patient_id = None
                        if bluetooth_bridge:
                            bluetooth_bridge.send_stop()
                        print("simulation over")

                        # 发送仿真结束消息给前端
                        if clients:
                            end_message = json.dumps({"status": "simulation_completed"})
                            await asyncio.gather(
                                *[client.send(end_message) for client in clients],
                                return_exceptions=True,
                            )
                        break
                else:
                    # 如果仿真未运行，发送心跳包/状态更新，保持连接状态实时性
                    if clients:
                        try:
                            status_update = {
                                "type": "status_update",
                                "db_status": (
                                    "connected" if is_db_connected() else "disconnected"
                                ),
                                "tcp_status": (
                                    "connected"
                                    if (
                                        bluetooth_bridge
                                        and bluetooth_bridge.enabled
                                        and bluetooth_bridge.is_connected
                                    )
                                    else "disconnected"
                                ),
                            }
                            message = json.dumps(status_update)
                            await asyncio.gather(
                                *[client.send(message) for client in clients],
                                return_exceptions=True,
                            )
                        except Exception as e:
                            logger.error(f"发送状态更新失败: {e}")

                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"生成数据时出错: {e}")
                await asyncio.sleep(1)

        if csv_file:
            csv_file.close()
            logger.info(f"Closed simulation data file: {csv_filepath}")


async def websocket_handler(websocket):
    """WebSocket连接处理器"""
    global simulation_running, year, month, day, hour, minute, second, person, sensor, pump, controller, start_time, base_datas, simulate_hours, sample_time, mini_step, simulate_times, current_simulation_id
    global patient_id, patient_name, patient_type, patient_age, patient_gender, patient_blood_type
    global meal_mode, meal_custom_type, meal_repeat_days, meal_daily_meals, meal_manual_meals, bluetooth_bridge
    global replay_running
    clients.add(websocket)
    logger.info(f"新客户端连接，当前客户端数量: {len(clients)}")

    # 发送初始连接状态
    try:
        initial_status = {
            "type": "status_update",
            "db_status": "connected" if is_db_connected() else "disconnected",
            "tcp_status": (
                "connected"
                if (
                    bluetooth_bridge
                    and bluetooth_bridge.enabled
                    and bluetooth_bridge.is_connected
                )
                else "disconnected"
            ),
        }
        await websocket.send(json.dumps(initial_status))
    except Exception as e:
        logger.error(f"发送初始状态失败: {e}")

    try:
        async for message in websocket:
            try:
                # 解析接收到的消息
                data = json.loads(message)
                command = data.get("command")

                if command == "create_simulation":
                    # 仅创建仿真记录，不启动仿真
                    try:
                        current_simulation_id = await create_new_simulation(
                            start_time,
                            person,
                            sensor,
                            pump,
                            controller,
                            simulate_hours,
                            simulate_times,
                            patient_id,
                            patient_name,
                            patient_type,
                            patient_age,
                            patient_gender,
                            patient_blood_type,
                        )
                        logger.info(
                            f"收到创建仿真命令，创建仿真ID: {current_simulation_id}"
                        )
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "simulation_created",
                                    "status": "simulation_created",
                                    "simulation_id": current_simulation_id,
                                }
                            )
                        )
                    except Exception as e:
                        logger.error(f"创建仿真记录失败: {e}")
                        await websocket.send(
                            json.dumps(
                                {
                                    "status": "error",
                                    "message": f"创建仿真失败: {str(e)}",
                                }
                            )
                        )

                elif command == "create_vpatient":
                    # 创建新虚拟患者
                    try:
                        logger.info(f"Received create_vpatient command: {data}")
                        real_profile = data.get("real_profile", {})
                        base_vp_id = data.get("base_vp_id")

                        result = matcher.create_new_patient(real_profile, base_vp_id)
                        logger.info(f"create_new_patient result: {result}")

                        await websocket.send(
                            json.dumps(
                                {"type": "create_vpatient_result", "data": result}
                            )
                        )

                        # 如果成功，广播更新后的库数据
                        if "error" not in result:
                            library_data = matcher.get_library_data()
                            await websocket.send(
                                json.dumps(
                                    {"type": "vpatients_data", "data": library_data}
                                )
                            )

                    except Exception as e:
                        logger.error(f"创建虚拟患者失败: {e}")
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "create_vpatient_result",
                                    "data": {"error": str(e)},
                                }
                            )
                        )

                elif command == "start_replay":
                    patient_id = data.get("patient_id")
                    logger.info(f"收到开始回放命令，患者ID: {patient_id}")

                    # 尝试从映射中获取数据集，如果没有则尝试直接使用 patient_id (兼容旧逻辑)
                    dataset_id = REAL_PATIENT_DATASETS.get(patient_id, patient_id)

                    if csv_provider.load_patient(dataset_id):
                        replay_running = True
                        simulation_running = False  # Stop simulation if running
                        logger.info(
                            f"已启动患者 {patient_id} (数据集: {dataset_id}) 的数据回放"
                        )
                    else:
                        # 如果找不到映射的数据集，尝试随机分配一个（针对已有患者）
                        available_datasets = [
                            f
                            for f in os.listdir(csv_provider.data_dir)
                            if f.endswith(".csv")
                        ]
                        if available_datasets:
                            selected_dataset = random.choice(available_datasets)
                            dataset_id = selected_dataset.replace(".csv", "")
                            REAL_PATIENT_DATASETS[patient_id] = dataset_id
                            logger.info(
                                f"为已有患者 {patient_id} 随机分配并启动数据集: {dataset_id}"
                            )
                            if csv_provider.load_patient(dataset_id):
                                replay_running = True
                                simulation_running = False
                            else:
                                logger.error(f"无法加载数据集 {dataset_id}")
                        else:
                            logger.error(
                                f"无法加载患者 {patient_id} 的数据，且无可用数据集"
                            )

                elif command == "stop_replay":
                    logger.info("收到停止回放命令")
                    replay_running = False

                elif command == "create_real_patient":
                    # 创建真实患者
                    logger.info(f"收到创建真实患者请求: {data}")
                    try:
                        params = data.get("params", {})
                        # 提取参数
                        p_start_time = datetime.now()  # 真实患者默认当前时间
                        p_person = params.get("person", "Real Patient")
                        p_sensor = params.get("sensor", "Dexcom")
                        p_pump = params.get("pump", "Insulet")
                        p_controller = params.get("controller", "PID")
                        p_patient_id = params.get("patient_id", None)
                        p_patient_name = params.get("patient_name", "Unknown")
                        p_patient_type = "Real"
                        p_patient_age = int(params.get("patient_age", 30))
                        p_patient_gender = params.get("patient_gender", "Male")
                        p_patient_blood_type = params.get("patient_blood_type", "A")
                        p_notes = params.get("notes", "")

                        logger.info(
                            f"正在写入数据库 tp_info: {p_patient_name} ({p_patient_id})"
                        )
                        new_id = await create_new_real_patient(
                            p_start_time,
                            p_person,
                            p_sensor,
                            p_pump,
                            p_controller,
                            p_patient_id,
                            p_patient_name,
                            p_patient_type,
                            p_patient_age,
                            p_patient_gender,
                            p_patient_blood_type,
                            p_notes,
                        )
                        logger.info(f"真实患者创建成功，ID: {new_id}")

                        # 随机分配一个数据集给该患者
                        available_datasets = [
                            f
                            for f in os.listdir(csv_provider.data_dir)
                            if f.endswith(".csv")
                        ]
                        if available_datasets:
                            selected_dataset = random.choice(available_datasets)
                            # 去掉 .csv 后缀作为 dataset_id
                            dataset_id = selected_dataset.replace(".csv", "")
                            REAL_PATIENT_DATASETS[new_id] = dataset_id
                            logger.info(f"为患者 {new_id} 分配了数据集: {dataset_id}")
                        else:
                            logger.warning("没有可用的CSV数据集")

                        # 发送成功响应
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "response",
                                    "command": "create_real_patient",
                                    "status": "success",
                                    "data": {"id": new_id},
                                }
                            )
                        )

                    except Exception as e:
                        logger.error(f"创建真实患者失败: {e}", exc_info=True)
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "response",
                                    "command": "create_real_patient",
                                    "status": "error",
                                    "message": f"创建失败: {str(e)}",
                                }
                            )
                        )

                elif command == "get_real_patients_list":
                    # 获取真实患者列表
                    try:
                        sims = await get_all_real_patients()
                        # 处理 datetime 对象
                        for sim in sims:
                            for key, value in sim.items():
                                if isinstance(value, datetime):
                                    sim[key] = value.isoformat()

                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "real_patients_list",
                                    "data": sims,
                                }
                            )
                        )
                    except Exception as e:
                        logger.error(f"获取真实患者列表失败: {e}")

                elif command == "start_simulation":
                    # 启动仿真
                    try:
                        # 如果提供了simulation_id，则使用现有的
                        sim_id = data.get("simulation_id")
                        if sim_id:
                            current_simulation_id = sim_id
                            logger.info(f"使用现有仿真ID启动: {current_simulation_id}")
                        else:
                            # 否则创建新的
                            current_simulation_id = await create_new_simulation(
                                start_time,
                                person,
                                sensor,
                                pump,
                                controller,
                                simulate_hours,
                                simulate_times,
                                patient_id,
                                patient_name,
                                patient_type,
                                patient_age,
                                patient_gender,
                                patient_blood_type,
                            )
                            logger.info(
                                f"收到启动仿真命令，创建仿真ID: {current_simulation_id}"
                            )

                        simulation_running = True
                        print("\n" + "=" * 50)
                        print("仿真参数信息:")
                        print(f"仿真ID: {current_simulation_id}")
                        print(f"开始时间: {start_time}")
                        print(f"患者姓名: {person}")
                        if patient_id:
                            print(f"患者ID: {patient_id}")
                            print(f"患者姓名: {patient_name}")
                            print(f"患者类型: {patient_type}")
                            print(f"患者年龄: {patient_age}")
                            print(f"患者性别: {patient_gender}")
                            print(f"患者血型: {patient_blood_type}")
                        print(f"传感器: {sensor}")
                        print(f"泵类型: {pump}")
                        print(f"控制器: {controller}")
                        print(f"仿真时长: {simulate_hours} 小时")
                        print(f"采样次数: {simulate_times}")
                        if meal_mode == "random":
                            print(f"餐食模式: 随机")
                        else:
                            print(f"餐食模式: 自定义")
                            if meal_custom_type == "daily":
                                print(f"  - 每日重复: {meal_repeat_days} 天")
                                print(f"  - 每日餐食数: {len(meal_daily_meals)}")
                            else:
                                print(
                                    f"  - 完全自定义: {len(meal_manual_meals)} 个时间点"
                                )
                        print("=" * 50 + "\n")
                        await websocket.send(
                            json.dumps(
                                {
                                    "status": "simulation_started",
                                    "simulation_id": current_simulation_id,
                                }
                            )
                        )
                    except Exception as e:
                        logger.error(f"创建仿真记录失败: {e}")
                        await websocket.send(
                            json.dumps(
                                {
                                    "status": "error",
                                    "message": f"启动仿真失败: {str(e)}",
                                }
                            )
                        )

                elif command == "stop_simulation":
                    simulation_running = False
                    # 更新仿真状态为已完成
                    if current_simulation_id is not None:
                        try:
                            await update_simulation_status(
                                current_simulation_id, "completed"
                            )
                        except Exception as e:
                            logger.error(f"更新仿真状态失败: {e}")
                    if bluetooth_bridge:
                        bluetooth_bridge.send_stop()
                    logger.info("收到停止仿真命令，停止发送数据")
                    await websocket.send(json.dumps({"status": "simulation_stopped"}))

                elif command == "update_params":
                    # 更新参数
                    params = data.get("params", {})
                    year = params.get("year", year)
                    month = params.get("month", month)
                    day = params.get("day", day)
                    hour = params.get("hour", hour)
                    minute = params.get("minute", minute)
                    second = params.get("second", second)
                    person = params.get("person", person)
                    sensor = params.get("sensor", sensor)
                    pump = params.get("pump", pump)
                    controller = params.get("controller", controller)
                    simulate_hours = params.get("simulate_hours", simulate_hours)

                    # PID 参数更新
                    base.kp = params.get("kp", base.kp)
                    base.ki = params.get("ki", base.ki)
                    base.kd = params.get("kd", base.kd)
                    base.target = params.get("target", base.target)

                    # 更新患者详细信息（可选）
                    patient_id = params.get("patient_id", patient_id)
                    patient_name = params.get("patient_name", patient_name)
                    patient_type = params.get("patient_type", patient_type)
                    patient_age = params.get("patient_age", patient_age)
                    patient_gender = params.get("patient_gender", patient_gender)
                    patient_blood_type = params.get(
                        "patient_blood_type", patient_blood_type
                    )

                    # 更新餐食设置（新增）
                    meal_mode = params.get("meal_mode", "random")
                    meal_custom_type = params.get("meal_custom_type", "daily")
                    meal_repeat_days = params.get("meal_repeat_days", 3)
                    meal_daily_meals = params.get("meal_daily_meals", [])
                    meal_manual_meals = params.get("meal_manual_meals", [])

                    # 根据sensor更新sample_time
                    match sensor:
                        case "Dexcom":
                            sample_time = 3  # 每天的时间段数
                            mini_step = 20
                        case "GuardianRT":
                            sample_time = 5
                            mini_step = 12
                        case "Navigator":
                            sample_time = 1
                            mini_step = 60
                        # case _:
                        #     sample_time = 5  # 默认值

                    # 重新计算simulate_times (总步数 = 总分钟数 / 采样间隔)
                    simulate_times = int(simulate_hours * 60 / sample_time)

                    # 更新开始时间
                    default_date = date(year, month, day)
                    default_time = time(hour, minute, second)
                    start_time = datetime.combine(default_date, default_time)

                    # 更新base_datas
                    base_datas = [
                        start_time,
                        person,
                        sensor,
                        pump,
                        controller,
                        simulate_times,
                    ]

                    # 打印更新后的参数
                    print("\n" + "=" * 50)
                    print("参数已更新！")
                    print(f"开始时间: {start_time}")
                    print(f"患者姓名: {person}")
                    if patient_id:
                        print(f"患者ID: {patient_id}")
                        print(f"患者姓名: {patient_name}")
                        print(f"患者类型: {patient_type}")
                        print(f"患者年龄: {patient_age}")
                        print(f"患者性别: {patient_gender}")
                        print(f"患者血型: {patient_blood_type}")
                    print(f"传感器: {sensor} (采样频率: {sample_time}/小时)")
                    print(f"泵类型: {pump}")
                    print(f"控制器: {controller}")
                    if controller == "pid":
                        print(
                            f"PID参数: Kp={base.kp}, Ki={base.ki}, Kd={base.kd}, Target={base.target}"
                        )
                    print(f"仿真时长: {simulate_hours} 小时")
                    print(f"采样次数: {simulate_times}")
                    if meal_mode == "random":
                        print(f"餐食模式: 随机")
                    else:
                        print(f"餐食模式: 自定义")
                        if meal_custom_type == "daily":
                            print(f"  - 每日重复: {meal_repeat_days} 天")
                            print(f"  - 每日餐食数: {len(meal_daily_meals)}")
                        else:
                            print(f"  - 完全自定义: {len(meal_manual_meals)} 个时间点")
                    print(f"完整参数: {base_datas}")
                    print("=" * 50 + "\n")

                    logger.info(f"参数已更新: {base_datas}")
                    await websocket.send(
                        json.dumps(
                            {
                                "status": "params_updated",
                                "params": {
                                    "start_time": start_time.isoformat(),
                                    "person": person,
                                    "sensor": sensor,
                                    "pump": pump,
                                    "controller": controller,
                                    "simulate_times": simulate_times,
                                },
                                "simulate_times": simulate_times,
                            }
                        )
                    )

                # --- 新增: 虚拟患者匹配 ---
                elif command == "get_vpatients_stats":
                    stats = matcher.get_stats()
                    await websocket.send(
                        json.dumps({"type": "vpatients_stats", "data": stats})
                    )

                elif command == "get_vpatients_data":
                    data = matcher.get_library_data()
                    await websocket.send(
                        json.dumps({"type": "vpatients_data", "data": data})
                    )

                elif command == "match_vpatient":
                    params = data.get("params", {})
                    result = matcher.match(params)
                    await websocket.send(
                        json.dumps({"type": "match_result", "data": result})
                    )

                elif command == "create_vpatient":
                    # Duplicate handler removed
                    pass
                # ------------------------

                elif command == "start_calibration":
                    # 高精度匹配/校准
                    real_patient_id = data.get("real_patient_id")
                    base_vp_id = data.get("base_vp_id")
                    
                    if not real_patient_id or not base_vp_id:
                        await websocket.send(json.dumps({"type": "calibration_result", "data": {"status": "error", "message": "Missing ID"}}))
                        continue

                    dataset_id = REAL_PATIENT_DATASETS.get(real_patient_id, real_patient_id)
                    # Try both with and without .csv, and check default path
                    csv_path = os.path.join(csv_provider.data_dir, f"{dataset_id}")
                    if not csv_path.endswith(".csv"):
                        csv_path += ".csv"
                    
                    if os.path.exists(csv_path):
                        await websocket.send(json.dumps({"type": "calibration_progress", "progress": 0, "status": "started"}))
                        
                        def run_calib():
                            try:
                                df = pd.read_csv(csv_path)
                                # Clean data
                                df['bg'] = pd.to_numeric(df['bg'], errors='coerce')
                                df['insulin'] = pd.to_numeric(df['insulin'], errors='coerce').fillna(0)
                                df['carbs'] = pd.to_numeric(df['carbs'], errors='coerce').fillna(0)
                                
                                # Convert BG from mmol/L to mg/dL if needed? 
                                # Sample showed 8.6, likely mmol/L. simglucose uses mg/dL.
                                # Check if max BG < 30. If so, multiply by 18.
                                max_bg = df['bg'].max()
                                if max_bg < 50: # Safe threshold
                                    df['bg'] = df['bg'] * 18.0182
                                
                                real_data = {
                                    'bg': df['bg'].fillna(0).tolist(),
                                    'insulin': df['insulin'].tolist(),
                                    'cho': df['carbs'].tolist(),
                                    'step_minutes': 1 # Data looks like 1 min
                                }
                                
                                p = Personalizer()
                                best_params = p.run_optimization(real_data, base_vp_id)
                                
                                # Validate
                                metrics = p.validate_model(real_data, best_params, base_vp_id)
                                
                                new_id = f"{real_patient_id}_Optimized"
                                matcher.save_optimized_patient(new_id, best_params, base_vp_id)
                                
                                return {
                                    "status": "success", 
                                    "new_id": new_id, 
                                    "params": best_params,
                                    "metrics": metrics
                                }
                            except Exception as e:
                                logger.error(f"Calibration failed: {e}")
                                return {"status": "error", "message": str(e)}

                        loop = asyncio.get_running_loop()
                        result = await loop.run_in_executor(None, run_calib)
                        
                        await websocket.send(json.dumps({
                            "type": "calibration_result",
                            "data": result
                        }))
                        
                        if result.get("status") == "success":
                             await websocket.send(json.dumps({"type": "vpatients_data", "data": matcher.get_library_data()}))
                    else:
                        await websocket.send(json.dumps({"type": "calibration_result", "data": {"status": "error", "message": "Dataset not found"}}))

                elif command == "get_simulations_list":
                    # 获取所有仿真记录列表
                    try:
                        simulations = await get_all_simulations()
                        # 转换datetime为字符串
                        for sim in simulations:
                            if sim.get("start_time"):
                                sim["start_time"] = sim["start_time"].isoformat()
                            if sim.get("created_at"):
                                sim["created_at"] = sim["created_at"].isoformat()
                            if sim.get("updated_at"):
                                sim["updated_at"] = sim["updated_at"].isoformat()

                        await websocket.send(
                            json.dumps(
                                {"status": "simulations_list", "data": simulations}
                            )
                        )
                    except Exception as e:
                        logger.error(f"获取仿真列表失败: {e}")
                        await websocket.send(
                            json.dumps(
                                {
                                    "status": "error",
                                    "message": f"获取仿真列表失败: {str(e)}",
                                }
                            )
                        )

                elif command == "get_simulation_data":
                    # 获取指定仿真的数据
                    simulation_id = data.get("simulation_id")
                    if simulation_id is None:
                        await websocket.send(
                            json.dumps(
                                {"status": "error", "message": "缺少simulation_id参数"}
                            )
                        )
                    else:
                        try:
                            sim_data = await get_simulation_data(simulation_id)
                            sim_info = await get_simulation_info(simulation_id)

                            # 转换datetime为字符串
                            if sim_info and sim_info.get("start_time"):
                                sim_info["start_time"] = sim_info[
                                    "start_time"
                                ].isoformat()
                            if sim_info and sim_info.get("created_at"):
                                sim_info["created_at"] = sim_info[
                                    "created_at"
                                ].isoformat()
                            if sim_info and sim_info.get("updated_at"):
                                sim_info["updated_at"] = sim_info[
                                    "updated_at"
                                ].isoformat()

                            await websocket.send(
                                json.dumps(
                                    {
                                        "status": "simulation_data",
                                        "simulation_id": simulation_id,
                                        "info": sim_info,
                                        "data": sim_data,
                                    }
                                )
                            )
                        except Exception as e:
                            logger.error(f"获取仿真数据失败: {e}")
                            await websocket.send(
                                json.dumps(
                                    {
                                        "status": "error",
                                        "message": f"获取仿真数据失败: {str(e)}",
                                    }
                                )
                            )

                elif command == "delete_simulation":
                    # 删除指定仿真
                    simulation_id = data.get("simulation_id")
                    if simulation_id is None:
                        await websocket.send(
                            json.dumps(
                                {"status": "error", "message": "缺少simulation_id参数"}
                            )
                        )
                    else:
                        try:
                            await delete_simulation(simulation_id)
                            await websocket.send(
                                json.dumps(
                                    {
                                        "status": "simulation_deleted",
                                        "simulation_id": simulation_id,
                                    }
                                )
                            )
                        except Exception as e:
                            logger.error(f"删除仿真失败: {e}")
                            await websocket.send(
                                json.dumps(
                                    {
                                        "status": "error",
                                        "message": f"删除仿真失败: {str(e)}",
                                    }
                                )
                            )

                elif command == "delete_real_patient":
                    # 删除真实患者
                    patient_record_id = data.get("patient_record_id")
                    if patient_record_id is None:
                        await websocket.send(
                            json.dumps(
                                {
                                    "status": "error",
                                    "message": "缺少patient_record_id参数",
                                }
                            )
                        )
                    else:
                        try:
                            await delete_real_patient(patient_record_id)
                            await websocket.send(
                                json.dumps(
                                    {
                                        "status": "real_patient_deleted",
                                        "patient_record_id": patient_record_id,
                                    }
                                )
                            )
                        except Exception as e:
                            logger.error(f"删除真实患者失败: {e}")
                            await websocket.send(
                                json.dumps(
                                    {
                                        "status": "error",
                                        "message": f"删除真实患者失败: {str(e)}",
                                    }
                                )
                            )

                else:
                    logger.warning(f"未知命令: {command}")

            except json.JSONDecodeError:
                logger.error(f"收到无效JSON消息: {message}")
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")

    except websockets.exceptions.ConnectionClosed:
        logger.info("客户端连接关闭")
    finally:
        clients.remove(websocket)
        logger.info(f"客户端断开连接，当前客户端数量: {len(clients)}")


async def main():
    """主函数"""
    # 初始化数据库连接池
    await init_db_pool()

    global bluetooth_bridge
    # 使用配置的IP和端口创建TCP连接
    logger.info(f"正在连接树莓派: {RASPBERRY_PI_IP}:{RASPBERRY_PI_PORT}")
    bluetooth_bridge = create_bridge(host=RASPBERRY_PI_IP, port=RASPBERRY_PI_PORT)

    # 启动WebSocket服务器
    server = await websockets.serve(websocket_handler, "localhost", 8766)
    logger.info("Base数据服务器启动在 ws://localhost:8766")

    # 启动数据生成任务
    data_task = asyncio.create_task(simulator())

    try:
        # 同时运行服务器和数据生成
        await asyncio.gather(server.wait_closed(), data_task)
    except KeyboardInterrupt:
        logger.info("服务器关闭")
    finally:
        server.close()
        await server.wait_closed()
        if bluetooth_bridge:
            bluetooth_bridge.stop()
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
