import asyncio
import logging
import sys
import os

# 添加当前目录到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
from database import init_db_pool, ensure_tables, close_db_pool

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FixTables")


async def main():
    logger.info("开始检查数据库表...")
    try:
        await init_db_pool()
        logger.info("数据库连接成功")

        await ensure_tables()
        logger.info("表结构检查/修复完成")

        # 检查数据
        pool = database.db_pool
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT COUNT(*) FROM tp_info")
                count_info = await cursor.fetchone()
                logger.info(f"tp_info 表记录数: {count_info[0]}")

                await cursor.execute("SELECT COUNT(*) FROM tp_data")
                count_data = await cursor.fetchone()
                logger.info(f"tp_data 表记录数: {count_data[0]}")

                # 列出所有表
                await cursor.execute("SHOW TABLES")
                tables = await cursor.fetchall()
                logger.info(f"当前数据库中的表: {[t[0] for t in tables]}")

    except Exception as e:
        logger.error(f"发生错误: {e}")
    finally:
        await close_db_pool()
        logger.info("数据库连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
