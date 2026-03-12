"""
数据库操作模块
用于管理仿真数据的存储和查询
"""

import aiomysql
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger("Database")

# 数据库连接配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",  # 根据实际情况修改
    "password": "123456",  # 根据实际情况修改
    "db": "2patients_datas",  # 数据库名
    "charset": "utf8mb4",
    "autocommit": True,
}

# 全局连接池
db_pool = None


def _require_pool():
    """Return the active connection pool or raise a helpful error."""
    if db_pool is None:
        raise RuntimeError(
            "Database pool has not been initialised. Call init_db_pool() first."
        )
    return db_pool


async def init_db_pool():
    """初始化数据库连接池"""
    global db_pool
    try:
        # 直接连接到2patients_datas数据库
        db_pool = await aiomysql.create_pool(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            db=DB_CONFIG["db"],
            charset=DB_CONFIG["charset"],
            autocommit=DB_CONFIG["autocommit"],
            minsize=1,
            maxsize=10,
        )
        logger.info(f"数据库连接池初始化成功，连接到 {DB_CONFIG['db']}")

        # 确保表存在
        await ensure_tables()
    except Exception as e:
        logger.error(f"数据库连接池初始化失败: {e}")
        raise


async def close_db_pool():
    """关闭数据库连接池"""
    global db_pool
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()
        logger.info("数据库连接池已关闭")


def is_db_connected():
    """检查数据库连接池是否已初始化并可用"""
    global db_pool
    return db_pool is not None and not db_pool._closed


async def ensure_tables():
    """确保数据库表存在"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 先删除旧表（如果存在）以确保表结构正确
            # await cursor.execute("DROP TABLE IF EXISTS vp_data")

            # 创建仿真数据表(如果不存在) - 使用 vp_data 表名
            # 注意：这里的 CREATE 语句仅在表完全不存在时执行
            # 具体的结构检查和迁移逻辑在下方
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vp_data (
                    simulation_id INT NOT NULL,
                    time DATETIME NOT NULL,
                    bg DECIMAL(5,2),
                    cgm DECIMAL(5,2),
                    bg_prev DECIMAL(5,2),
                    cho DECIMAL(5,2),
                    cob DECIMAL(5,2),
                    insulin DECIMAL(6,3),
                    basal DECIMAL(6,3),
                    bolus DECIMAL(6,3),
                    iob DECIMAL(6,3),
                    PRIMARY KEY (simulation_id, time),
                    CONSTRAINT fk_vp_data_simulation_id FOREIGN KEY (simulation_id) REFERENCES vp_info(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            )

            # 创建仿真元数据表(记录每次仿真的基本信息) - 使用 sim_meta 表名
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vp_info (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    start_time DATETIME NOT NULL,
                    person VARCHAR(100),
                    patient_id VARCHAR(50),
                    patient_name VARCHAR(100),
                    patient_type VARCHAR(50),
                    patient_age INT,
                    patient_gender VARCHAR(20),
                    patient_blood_type VARCHAR(10),
                    sensor VARCHAR(50),
                    pump VARCHAR(50),
                    controller VARCHAR(50),
                    simulate_hours INT,
                    simulate_times INT,
                    data_count INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'running'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            )

            # 检查并添加缺失的患者信息字段（如果表已存在但字段不存在）
            patient_columns = [
                ("patient_id", "VARCHAR(50)"),
                ("patient_name", "VARCHAR(100)"),
                ("patient_type", "VARCHAR(50)"),
                ("patient_age", "INT"),
                ("patient_gender", "VARCHAR(20)"),
                ("patient_blood_type", "VARCHAR(10)"),
            ]

            for column_name, column_type in patient_columns:
                try:
                    # 尝试添加列，如果已存在会忽略错误
                    await cursor.execute(
                        f"ALTER TABLE vp_info ADD COLUMN {column_name} {column_type}"
                    )
                    logger.info(f"添加列 {column_name} 到 vp_info 表")
                except Exception as e:
                    # 列已存在，忽略错误
                    if "Duplicate column name" not in str(e):
                        logger.debug(f"列 {column_name} 可能已存在: {e}")

            # ==========================================
            # 创建真实患者相关表 (tp_info, tp_data)
            # ==========================================

            # 创建真实患者元数据表
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tp_info (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    start_time DATETIME NOT NULL,
                    person VARCHAR(100),
                    patient_id VARCHAR(50),
                    patient_name VARCHAR(100),
                    patient_type VARCHAR(50),
                    patient_age INT,
                    patient_gender VARCHAR(20),
                    patient_blood_type VARCHAR(10),
                    notes TEXT,
                    sensor VARCHAR(50),
                    pump VARCHAR(50),
                    controller VARCHAR(50),
                    simulate_hours INT,
                    simulate_times INT,
                    data_count INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'active'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            )

            # 检查并添加 notes 列（如果表已存在但字段不存在）
            try:
                await cursor.execute(
                    "ALTER TABLE tp_info ADD COLUMN notes TEXT AFTER patient_blood_type"
                )
                logger.info("添加列 notes 到 tp_info 表")
            except Exception as e:
                if "Duplicate column name" not in str(e):
                    logger.debug(f"列 notes 可能已存在: {e}")

            # 创建真实患者数据表
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tp_data (
                    patient_record_id INT NOT NULL,
                    time DATETIME NOT NULL,
                    bg DECIMAL(5,2),
                    cgm DECIMAL(5,2),
                    bg_prev DECIMAL(5,2),
                    cho DECIMAL(5,2),
                    cob DECIMAL(5,2),
                    insulin DECIMAL(6,3),
                    basal DECIMAL(6,3),
                    bolus DECIMAL(6,3),
                    iob DECIMAL(6,3),
                    PRIMARY KEY (patient_record_id, time),
                    CONSTRAINT fk_tp_data_patient_record_id FOREIGN KEY (patient_record_id) REFERENCES tp_info(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            )
            logger.info("真实患者表 (tp_info, tp_data) 检查/创建完成")

            # ==========================================
            # 优化 vp_data 表结构
            # ==========================================

            # 检查 vp_data 表是否存在
            await cursor.execute("SHOW TABLES LIKE 'vp_data'")
            table_exists = await cursor.fetchone()

            if not table_exists:
                # 创建优化后的新表
                await cursor.execute(
                    """
                    CREATE TABLE vp_data (
                        simulation_id INT NOT NULL,
                        time DATETIME NOT NULL,
                        bg DECIMAL(5,2),
                        cgm DECIMAL(5,2),
                        bg_prev DECIMAL(5,2),
                        cho DECIMAL(5,2),
                        cob DECIMAL(5,2),
                        insulin DECIMAL(6,3),
                        basal DECIMAL(6,3),
                        bolus DECIMAL(6,3),
                        iob DECIMAL(6,3),
                        PRIMARY KEY (simulation_id, time),
                        CONSTRAINT fk_vp_data_simulation_id FOREIGN KEY (simulation_id) REFERENCES vp_info(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                logger.info("创建优化后的 vp_data 表成功")
            else:
                # 检查是否需要迁移 (检查是否存在 simulation_id 列)
                await cursor.execute("SHOW COLUMNS FROM vp_data LIKE 'simulation_id'")
                has_sim_id = await cursor.fetchone()

                if not has_sim_id:
                    logger.info("检测到旧版 vp_data 表结构，开始自动迁移...")
                    try:
                        # 1. 重命名 id -> simulation_id
                        # 注意：如果原表有索引，可能需要先删除索引，这里假设可以直接改名
                        await cursor.execute(
                            "ALTER TABLE vp_data CHANGE COLUMN id simulation_id INT NOT NULL"
                        )
                        logger.info("迁移: id 字段重命名为 simulation_id")

                        # 2. 删除冗余的 patient_id 字段
                        await cursor.execute(
                            "SHOW COLUMNS FROM vp_data LIKE 'patient_id'"
                        )
                        if await cursor.fetchone():
                            await cursor.execute(
                                "ALTER TABLE vp_data DROP COLUMN patient_id"
                            )
                            logger.info("迁移: 删除冗余 patient_id 字段")

                        # 3. 尝试添加联合主键 (simulation_id, time)
                        # 注意：如果存在重复数据，这一步会失败
                        try:
                            # 先删除可能存在的旧索引
                            await cursor.execute(
                                "SHOW INDEX FROM vp_data WHERE Key_name = 'idx_id'"
                            )
                            if await cursor.fetchone():
                                await cursor.execute("DROP INDEX idx_id ON vp_data")

                            await cursor.execute(
                                "ALTER TABLE vp_data ADD PRIMARY KEY (simulation_id, time)"
                            )
                            logger.info("迁移: 添加联合主键 (simulation_id, time)")
                        except Exception as e:
                            logger.warning(
                                f"迁移警告: 无法添加主键 (可能存在重复时间点数据): {e}"
                            )
                            # 如果添加主键失败，至少添加一个普通索引以保证性能
                            await cursor.execute(
                                "CREATE INDEX idx_simulation_id ON vp_data (simulation_id)"
                            )

                        # 4. 添加外键约束
                        try:
                            await cursor.execute(
                                "ALTER TABLE vp_data ADD CONSTRAINT fk_vp_data_simulation_id FOREIGN KEY (simulation_id) REFERENCES vp_info(id) ON DELETE CASCADE"
                            )
                            logger.info("迁移: 添加外键约束")
                        except Exception as e:
                            logger.warning(
                                f"迁移警告: 无法添加外键 (可能存在孤立数据): {e}"
                            )

                        logger.info("vp_data 表结构迁移完成")
                    except Exception as e:
                        logger.error(f"vp_data 表迁移过程中发生错误: {e}")

            await conn.commit()
            logger.info("数据库表检查完成")


async def create_new_real_patient(
    start_time,
    person,
    sensor,
    pump,
    controller,
    patient_id,
    patient_name,
    patient_type,
    patient_age,
    patient_gender,
    patient_blood_type,
    notes=None,
):
    """创建新的真实患者记录"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 如果没有提供 patient_id，先使用空字符串占位，稍后更新
            temp_patient_id = patient_id if patient_id else ""

            await cursor.execute(
                """
                INSERT INTO tp_info (
                    start_time, person, sensor, pump, controller,
                    patient_id, patient_name, patient_type, patient_age, patient_gender, patient_blood_type, notes,
                    status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
            """,
                (
                    start_time,
                    person,
                    sensor,
                    pump,
                    controller,
                    temp_patient_id,
                    patient_name,
                    patient_type,
                    patient_age,
                    patient_gender,
                    patient_blood_type,
                    notes,
                ),
            )
            await conn.commit()
            patient_record_id = cursor.lastrowid

            # 如果 patient_id 为空，则使用 ID 生成 TP{ID}
            if not patient_id:
                final_patient_id = f"TP{patient_record_id}"
                await cursor.execute(
                    "UPDATE tp_info SET patient_id = %s WHERE id = %s",
                    (final_patient_id, patient_record_id),
                )
                await conn.commit()
                logger.info(f"自动生成真实患者ID: {final_patient_id}")

            logger.info(
                f"创建真实患者记录: ID={patient_record_id}, Name={patient_name}"
            )
            return patient_record_id


async def get_all_real_patients():
    """获取所有真实患者记录列表"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT id, start_time, person, patient_id, patient_name, patient_type,
                       patient_age, patient_gender, patient_blood_type, notes,
                       sensor, pump, controller, 
                       created_at, updated_at, status
                FROM tp_info
                ORDER BY id DESC
            """
            )
            results = await cursor.fetchall()
            return results


async def save_real_patient_data(
    patient_record_id,
    time,
    bg,
    cgm,
    bg_prev,
    cho=None,
    cob=None,
    insulin=None,
    basal=None,
    bolus=None,
    iob=None,
):
    """保存单条真实患者数据"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO tp_data (patient_record_id, time, bg, cgm, bg_prev, cho, cob, insulin, basal, bolus, iob)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    patient_record_id,
                    time,
                    bg,
                    cgm,
                    bg_prev,
                    cho,
                    cob,
                    insulin,
                    basal,
                    bolus,
                    iob,
                ),
            )

            # 更新元数据中的数据计数
            await cursor.execute(
                """
                UPDATE tp_info
                SET data_count = data_count + 1, updated_at = NOW()
                WHERE id = %s
            """,
                (patient_record_id,),
            )

            await conn.commit()


async def get_real_patient_data(patient_record_id):
    """获取指定真实患者的所有数据"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT d.patient_record_id as id, i.patient_id, d.time, d.bg, d.cgm, d.bg_prev, 
                       d.cho, d.cob, d.insulin, d.basal, d.bolus, d.iob
                FROM tp_data d
                LEFT JOIN tp_info i ON d.patient_record_id = i.id
                WHERE d.patient_record_id = %s
                ORDER BY d.time ASC
            """,
                (patient_record_id,),
            )
            results = await cursor.fetchall()
            for row in results:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        row[key] = float(value)
            return results


async def delete_real_patient(patient_record_id):
    """删除指定的真实患者记录及其数据"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 删除数据 (如果有外键级联删除，这一步其实可以省略)
            await cursor.execute(
                "DELETE FROM tp_data WHERE patient_record_id = %s", (patient_record_id,)
            )
            # 删除元数据
            await cursor.execute(
                "DELETE FROM tp_info WHERE id = %s", (patient_record_id,)
            )
            await conn.commit()
            logger.info(f"删除真实患者记录: ID={patient_record_id}")


async def update_real_patient_info(patient_record_id, update_data):
    """更新真实患者信息"""
    pool = _require_pool()

    # 构建更新语句
    fields = []
    values = []
    for key, value in update_data.items():
        # 过滤允许更新的字段
        if key in [
            "patient_name",
            "patient_age",
            "patient_gender",
            "patient_blood_type",
            "notes",
            "sensor",
            "pump",
            "controller",
        ]:
            fields.append(f"{key} = %s")
            values.append(value)

    if not fields:
        return

    values.append(patient_record_id)
    query = f"UPDATE tp_info SET {', '.join(fields)}, updated_at = NOW() WHERE id = %s"

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, tuple(values))
            await conn.commit()
            logger.info(f"更新真实患者信息: ID={patient_record_id}")


async def create_new_simulation(
    start_time,
    person,
    sensor,
    pump,
    controller,
    simulate_hours,
    simulate_times,
    patient_id=None,
    patient_name=None,
    patient_type=None,
    patient_age=None,
    patient_gender=None,
    patient_blood_type=None,
):
    """创建新的仿真记录,返回仿真ID"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 先插入数据获取自增ID
            await cursor.execute(
                """
                INSERT INTO vp_info 
                (start_time, person, patient_id, patient_name, patient_type, patient_age, 
                 patient_gender, patient_blood_type, sensor, pump, controller, 
                 simulate_hours, simulate_times, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'running')
            """,
                (
                    start_time,
                    person,
                    None,  # patient_id暂时为空,后面更新
                    patient_name,
                    patient_type,
                    patient_age,
                    patient_gender,
                    patient_blood_type,
                    sensor,
                    pump,
                    controller,
                    simulate_hours,
                    simulate_times,
                ),
            )

            await conn.commit()

            # 获取新插入的ID
            await cursor.execute("SELECT LAST_INSERT_ID()")
            result = await cursor.fetchone()
            simulation_id = result[0]

            # 根据patient_type生成带前缀的patient_id
            prefix = "VP"  # 默认虚拟患者

            # 添加调试日志
            logger.info(
                f"调试: patient_type 原始值 = {patient_type}, 类型 = {type(patient_type)}"
            )

            if patient_type:
                type_str = str(patient_type).lower()
                logger.info(f"调试: patient_type 转换后 = {type_str}")

                if "真实" in type_str or "true" in type_str or type_str == "tp":
                    prefix = "TP"
                    logger.info(f"调试: 判断为真实患者, prefix = TP")
                elif "虚拟" in type_str or "virtual" in type_str or type_str == "vp":
                    prefix = "VP"
                    logger.info(f"调试: 判断为虚拟患者, prefix = VP")
                else:
                    logger.info(f"调试: 未匹配到任何条件,使用默认 prefix = VP")
            else:
                logger.info(f"调试: patient_type 为空,使用默认 prefix = VP")

            # 格式化patient_id: VP001, TP002等
            formatted_patient_id = f"{prefix}{simulation_id:03d}"
            logger.info(f"调试: 最终生成的 patient_id = {formatted_patient_id}")

            # 更新patient_id字段
            await cursor.execute(
                """
                UPDATE vp_info
                SET patient_id = %s
                WHERE id = %s
                """,
                (formatted_patient_id, simulation_id),
            )

            await conn.commit()

            logger.info(
                f"创建仿真记录成功: ID={simulation_id}, patient_id={formatted_patient_id}"
            )

            logger.info(f"创建新仿真记录: ID={simulation_id}")
            return simulation_id


async def save_simulation_data(
    simulation_id,
    time,
    bg,
    cgm,
    bg_prev,
    cho=None,
    cob=None,
    insulin=None,
    basal=None,
    bolus=None,
    iob=None,
):
    """保存单条仿真数据"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO vp_data (simulation_id, time, bg, cgm, bg_prev, cho, cob, insulin, basal, bolus, iob)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    simulation_id,
                    time,
                    bg,
                    cgm,
                    bg_prev,
                    cho,
                    cob,
                    insulin,
                    basal,
                    bolus,
                    iob,
                ),
            )

            # 更新元数据中的数据计数
            await cursor.execute(
                """
                UPDATE vp_info
                SET data_count = data_count + 1, updated_at = NOW()
                WHERE id = %s
            """,
                (simulation_id,),
            )

            await conn.commit()


async def update_simulation_status(simulation_id, status):
    """更新仿真状态"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE vp_info
                SET status = %s, updated_at = NOW()
                WHERE id = %s
            """,
                (status, simulation_id),
            )
            await conn.commit()
            logger.info(f"更新仿真状态: ID={simulation_id}, status={status}")


async def get_all_simulations():
    """获取所有仿真记录列表"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT id, start_time, person, patient_id, patient_name, patient_type,
                       patient_age, patient_gender, patient_blood_type,
                       sensor, pump, controller, 
                       simulate_hours, simulate_times, data_count, 
                       created_at, updated_at, status
                FROM vp_info
                ORDER BY id DESC
            """
            )
            results = await cursor.fetchall()
            return results


async def get_simulation_data(simulation_id):
    """获取指定仿真的所有数据"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # 联表查询以获取 patient_id，保持返回结构兼容性
            await cursor.execute(
                """
                SELECT d.simulation_id as id, i.patient_id, d.time, d.bg, d.cgm, d.bg_prev, 
                       d.cho, d.cob, d.insulin, d.basal, d.bolus, d.iob
                FROM vp_data d
                LEFT JOIN vp_info i ON d.simulation_id = i.id
                WHERE d.simulation_id = %s
                ORDER BY d.time ASC
            """,
                (simulation_id,),
            )
            results = await cursor.fetchall()
            for row in results:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        row[key] = float(value)
            return results


async def get_simulation_info(simulation_id):
    """获取指定仿真的元数据信息"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT id, start_time, person, patient_id, patient_name, patient_type,
                       patient_age, patient_gender, patient_blood_type,
                       sensor, pump, controller, 
                       simulate_hours, simulate_times, data_count, 
                       created_at, updated_at, status
                FROM vp_info
                WHERE id = %s
            """,
                (simulation_id,),
            )
            result = await cursor.fetchone()
            return result


async def delete_simulation(simulation_id):
    """删除指定的仿真记录及其数据"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 删除仿真数据 (如果有外键级联删除，这一步其实可以省略，但保留也无妨)
            await cursor.execute(
                "DELETE FROM vp_data WHERE simulation_id = %s", (simulation_id,)
            )
            # 删除元数据
            await cursor.execute("DELETE FROM vp_info WHERE id = %s", (simulation_id,))
            await conn.commit()
            logger.info(f"删除仿真记录: ID={simulation_id}")


async def delete_real_patient(patient_record_id):
    """删除指定的真实患者记录及其数据"""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 删除真实患者数据
            # tp_data 表使用 patient_record_id 作为外键关联 tp_info.id
            try:
                await cursor.execute(
                    "DELETE FROM tp_data WHERE patient_record_id = %s",
                    (patient_record_id,),
                )
            except Exception as e:
                # 如果列名不对或者表不存在，记录警告但不阻断主记录删除
                logger.warning(f"尝试删除 tp_data 失败 (可能是表结构差异): {e}")

            # 删除元数据
            await cursor.execute(
                "DELETE FROM tp_info WHERE id = %s", (patient_record_id,)
            )
            await conn.commit()
            logger.info(f"删除真实患者记录: ID={patient_record_id}")
