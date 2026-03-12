import math
import asyncio
import json
import websockets
import logging
from datetime import datetime, date, time, timedelta
from database import (
    init_db_pool,
    close_db_pool,
    create_new_simulation,
    save_simulation_data,
    update_simulation_status,
    get_all_simulations,
    get_simulation_data,
    get_simulation_info,
    delete_simulation,
)


# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("BaseDataServer")

# 全局状态
clients = set()
simulation_running = False  # 控制仿真是否运行
current_simulation_id = None  # 当前仿真ID

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
pump = "Insulet"
controller = "PID"
simulate_hours = 1

# PID 参数
kp = 0.0
ki = 0.0
kd = 0.0
target = 120.0

# New Controller Parameters (Aligned with Python files)
g_lower = 30
g_upper = 180
g_safety = 90
basal_rate = 0.015
pred_horizon_min = 120
control_horizon_min = 45
u_min = -0.02
u_max = 0.04
hypo_guard = 95
soft_upper = 180
basal_floor = 0.35
q_bg = 1.0
q_low = 10.0
w_under = 120
w_over = 1.5

# 患者详细信息
patient_id = None
patient_name = None
patient_type = None
patient_age = None
patient_gender = None
patient_blood_type = None
simulate_times = sample_time * simulate_hours

# daily_meals = [(7, 45), (12, 30), (16, 15), (18, 80), (23, 10)]
# scen = []
# for d in range(simulate_hours * simple_time):
#     for hour, amount in daily_meals:
#         # 使用 timedelta 表示相对于 start_time 的偏移
#         scen.append((timedelta(days=d, hours=hour), amount))
base_datas = [start_time, person, sensor, pump, controller, simulate_times]
###一些参数


def base_params():
    global simulation_running, year, month, day, hour, minute, second, person, sensor, pump, controller, start_time, base_datas, simulate_hours, sample_time, mini_step, simulate_times, current_simulation_id
    global patient_id, patient_name, patient_type, patient_age, patient_gender, patient_blood_type
    global kp, ki, kd, target
    global g_lower, g_upper, g_safety, basal_rate, pred_horizon_min, control_horizon_min, u_min, u_max, hypo_guard, soft_upper, basal_floor, q_bg, q_low, w_under, w_over
    return (
        simulation_running,
        year,
        month,
        day,
        hour,
        minute,
        second,
        person,
        sensor,
        pump,
        controller,
        start_time,
        base_datas,
        simulate_hours,
        sample_time,
        mini_step,
        simulate_times,
        current_simulation_id,
        patient_id,
        patient_name,
        patient_type,
        patient_age,
        patient_gender,
        patient_blood_type,
        kp,
        ki,
        kd,
        target,
        g_lower,
        g_upper,
        g_safety,
        basal_rate,
        pred_horizon_min,
        control_horizon_min,
        u_min,
        u_max,
        hypo_guard,
        soft_upper,
        basal_floor,
        q_bg,
        q_low,
        w_under,
        w_over,
    )


async def generate_realtime_data():
    """实时生成数据"""
    global current_simulation_id
    i = 0
    while True:
        try:
            # 只有在仿真运行时才生成和发送数据
            if simulation_running:
                # 生成当前数据点
                x = i
                sin_value = math.sin(i / 10) * 10 + 50
                cos_value = math.cos(i / 10) * 10 + 50
                tan_value = math.tan(i / 10) * 10 + 50

                # 创建数据包
                data_packet = {
                    "timestamp": datetime.now().isoformat(),
                    "i": x,
                    "sin": round(sin_value, 2),
                    "cos": round(cos_value, 2),
                    "tan": round(tan_value, 2),
                }

                # 保存到数据库
                if current_simulation_id is not None:
                    try:
                        await save_simulation_data(
                            current_simulation_id,
                            x,
                            round(sin_value, 2),
                            round(cos_value, 2),
                            round(tan_value, 2),
                            1,
                            1,
                            1,
                            1,
                            1,
                        )
                    except Exception as db_error:
                        logger.error(f"保存数据到数据库失败: {db_error}")

                # 发送给所有连接的客户端
                if clients:
                    message = json.dumps(data_packet)
                    await asyncio.gather(
                        *[client.send(message) for client in clients],
                        return_exceptions=True,
                    )
                    logger.info(
                        f"发送数据: i={x}, sin={sin_value:.2f}, cos={cos_value:.2f}, tan={tan_value:.2f}"
                    )

                i += 1
            else:
                # 仿真未运行时，重置计数器
                i = 0
                await asyncio.sleep(0.1)
                continue

            # 每10ms生成一个数据点
            await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"生成数据时出错: {e}")
            await asyncio.sleep(1)


async def websocket_handler(websocket):
    """WebSocket连接处理器"""
    global simulation_running, year, month, day, hour, minute, second, person, sensor, pump, controller, start_time, base_datas, simulate_hours, sample_time, mini_step, simulate_times, current_simulation_id
    global patient_id, patient_name, patient_type, patient_age, patient_gender, patient_blood_type
    clients.add(websocket)
    logger.info(f"新客户端连接，当前客户端数量: {len(clients)}")

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
                    kp = params.get("kp", kp)
                    ki = params.get("ki", ki)
                    kd = params.get("kd", kd)
                    target = params.get("target", target)

                    # New Controller Parameters Update
                    g_lower = params.get("g_lower", g_lower)
                    g_upper = params.get("g_upper", g_upper)
                    g_safety = params.get("g_safety", g_safety)
                    basal_rate = params.get("basal_rate", basal_rate)
                    pred_horizon_min = params.get("pred_horizon_min", pred_horizon_min)
                    control_horizon_min = params.get(
                        "control_horizon_min", control_horizon_min
                    )
                    u_min = params.get("u_min", u_min)
                    u_max = params.get("u_max", u_max)
                    hypo_guard = params.get("hypo_guard", hypo_guard)
                    soft_upper = params.get("soft_upper", soft_upper)
                    basal_floor = params.get("basal_floor", basal_floor)
                    q_bg = params.get("q_bg", q_bg)
                    q_low = params.get("q_low", q_low)
                    w_under = params.get("w_under", w_under)
                    w_over = params.get("w_over", w_over)

                    # 更新患者详细信息（可选）
                    patient_id = params.get("patient_id", patient_id)
                    patient_name = params.get("patient_name", patient_name)
                    patient_type = params.get("patient_type", patient_type)
                    patient_age = params.get("patient_age", patient_age)
                    patient_gender = params.get("patient_gender", patient_gender)
                    patient_blood_type = params.get(
                        "patient_blood_type", patient_blood_type
                    )

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

                    # 重新计算simulate_times
                    simulate_times = sample_time * simulate_hours

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
                        print(f"PID参数: Kp={kp}, Ki={ki}, Kd={kd}, Target={target}")
                    print(f"仿真时长: {simulate_hours} 小时")
                    print(f"采样次数: {simulate_times}")
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

    # 启动WebSocket服务器
    server = await websockets.serve(websocket_handler, "localhost", 8766)
    logger.info("Base数据服务器启动在 ws://localhost:8766")

    # 启动数据生成任务
    data_task = asyncio.create_task(generate_realtime_data())

    try:
        # 同时运行服务器和数据生成
        await asyncio.gather(server.wait_closed(), data_task)
    except KeyboardInterrupt:
        logger.info("服务器关闭")
    finally:
        server.close()
        await server.wait_closed()
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
