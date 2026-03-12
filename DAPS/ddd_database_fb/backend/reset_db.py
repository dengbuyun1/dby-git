import asyncio
import aiomysql
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResetDB")

# 数据库连接配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "db": "2patients_datas",
    "charset": "utf8mb4",
    "autocommit": True,
}


async def reset_database():
    try:
        logger.info("正在连接数据库...")
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            logger.info("正在清空 vp_data 表...")
            await cursor.execute("TRUNCATE TABLE vp_data")

            logger.info("正在清空 vp_info 表 (重置ID)...")
            # 由于有外键约束，可能需要先禁用外键检查
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            await cursor.execute("TRUNCATE TABLE vp_info")
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            logger.info("数据库重置成功！ID将从1开始。")

        conn.close()
    except Exception as e:
        logger.error(f"重置数据库失败: {e}")


if __name__ == "__main__":
    asyncio.run(reset_database())
