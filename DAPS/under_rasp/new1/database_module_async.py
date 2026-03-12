"""
异步数据库模块 - 性能优化版

通过队列 + 后台线程批量写入,避免阻塞主循环
预期提升: 10-50ms → <1ms
"""

import pymysql
import threading
import queue
import time
from datetime import datetime
from config_module import DB_CONFIG


class AsyncDatabaseWriter:
    """异步数据库写入器"""

    def __init__(self, batch_size=10, flush_interval=1.0):
        """
        Args:
            batch_size: 批量写入的记录数
            flush_interval: 强制刷新间隔 (秒)
        """
        self.connection = None
        self.write_queue = queue.Queue(maxsize=1000)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.running = False
        self.worker_thread = None

        # 统计
        self.total_writes = 0
        self.failed_writes = 0
        self.queue_overflow = 0

    def connect(self):
        """连接到MySQL数据库"""
        try:
            self.connection = pymysql.connect(
                host=DB_CONFIG["host"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                db=DB_CONFIG["db"],
                charset=DB_CONFIG["charset"],
                cursorclass=pymysql.cursors.DictCursor,
            )
            print("MySQL数据库连接成功 (异步模式)")
            return True
        except Exception as e:
            print(f"MySQL连接错误: {e}")
            return False

    def start(self):
        """启动异步写入线程"""
        if not self.connect():
            print("警告: 数据库连接失败,数据将仅保存在内存队列")

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        print("异步数据库写入线程已启动")

    def stop(self, timeout=10):
        """停止异步写入线程并刷新所有待写入数据"""
        print("正在停止异步数据库写入...")
        self.running = False

        if self.worker_thread:
            self.worker_thread.join(timeout)

        # 刷新剩余数据
        self._flush_remaining()

        if self.connection:
            self.connection.close()
            print("数据库连接已关闭")

        print(
            f"异步写入统计: 总计{self.total_writes}条, "
            f"失败{self.failed_writes}条, "
            f"队列溢出{self.queue_overflow}次"
        )

    def save_async(self, patient_id, time_str, cgm, cho, basal, bolus, insulin):
        """
        异步保存数据到队列 (非阻塞)

        Args:
            patient_id: 病人ID
            time_str: 时间字符串
            cgm: CGM值
            cho: 碳水
            basal: 基础胰岛素
            bolus: 餐时胰岛素
            insulin: 总胰岛素

        Returns:
            bool: 是否成功加入队列
        """
        try:
            # 非阻塞放入队列
            self.write_queue.put_nowait(
                (patient_id, time_str, cgm, cho, basal, bolus, insulin)
            )
            return True
        except queue.Full:
            self.queue_overflow += 1
            if self.queue_overflow % 10 == 0:
                print(f"警告: 数据库队列已满 (溢出{self.queue_overflow}次)")
            return False

    def _worker(self):
        """后台工作线程: 批量写入数据"""
        batch = []
        last_flush = time.time()

        while self.running or not self.write_queue.empty():
            try:
                # 等待数据,最多0.1秒
                try:
                    item = self.write_queue.get(timeout=0.1)
                    batch.append(item)
                except queue.Empty:
                    pass

                # 批量写入条件: 1) 达到批大小 或 2) 超过时间间隔
                current_time = time.time()
                should_flush = len(batch) >= self.batch_size or (
                    batch and current_time - last_flush >= self.flush_interval
                )

                if should_flush:
                    self._batch_write(batch)
                    batch = []
                    last_flush = current_time

            except Exception as e:
                print(f"异步写入线程错误: {e}")
                time.sleep(1)

        # 最后刷新
        if batch:
            self._batch_write(batch)

    def _batch_write(self, batch):
        """批量写入数据"""
        if not batch:
            return

        # 检查连接
        try:
            if self.connection:
                self.connection.ping(reconnect=True)
            else:
                self.connect()
        except:
            if not self.connect():
                print("数据库重连失败,丢弃本批数据")
                self.failed_writes += len(batch)
                return

        # 批量插入
        cursor = self.connection.cursor()
        sql = """
            INSERT INTO BG_Datas (patient_id, time, cgm, cho, basal, bolus, insulin) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        try:
            cursor.executemany(sql, batch)
            self.connection.commit()
            self.total_writes += len(batch)
            # print(f"批量写入 {len(batch)} 条记录")
        except Exception as e:
            print(f"批量写入错误: {e}")
            self.connection.rollback()
            self.failed_writes += len(batch)

    def _flush_remaining(self):
        """刷新所有剩余数据"""
        batch = []
        while not self.write_queue.empty():
            try:
                item = self.write_queue.get_nowait()
                batch.append(item)
            except queue.Empty:
                break

        if batch:
            print(f"刷新剩余 {len(batch)} 条记录...")
            self._batch_write(batch)

    def get_stats(self):
        """获取统计信息"""
        return {
            "queue_size": self.write_queue.qsize(),
            "total_writes": self.total_writes,
            "failed_writes": self.failed_writes,
            "queue_overflow": self.queue_overflow,
        }


# ==================== 全局实例 ====================
_async_db = None


def get_async_db():
    """获取全局异步数据库实例"""
    global _async_db
    if _async_db is None:
        _async_db = AsyncDatabaseWriter(batch_size=10, flush_interval=1.0)
        _async_db.start()
    return _async_db


def save_to_database_async(
    connection_unused, patient_id, time_str, cgm, cho, basal, bolus, insulin
):
    """
    异步保存数据 (兼容接口)

    注意: connection_unused 参数保留是为了兼容原 save_to_database() 接口
    """
    db = get_async_db()
    return db.save_async(patient_id, time_str, cgm, cho, basal, bolus, insulin)


def stop_async_db():
    """停止异步数据库 (程序退出时调用)"""
    global _async_db
    if _async_db:
        _async_db.stop()
        _async_db = None


# ==================== 兼容原模块 ====================
def connect_mysql():
    """
    兼容原接口 - 返回 None (因为异步模式不需要连接对象)
    """
    get_async_db()  # 初始化异步DB
    return None  # 返回 None,但不影响功能


def save_to_database(connection, patient_id, time_str, cgm, cho, basal, bolus, insulin):
    """
    兼容原接口 - 转发到异步版本
    """
    return save_to_database_async(
        connection, patient_id, time_str, cgm, cho, basal, bolus, insulin
    )


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("异步数据库模块测试\n")

    # 启动
    db = AsyncDatabaseWriter(batch_size=5, flush_interval=2.0)
    db.start()

    # 模拟写入
    print("模拟写入 50 条数据...\n")
    for i in range(50):
        timestamp = datetime.now().isoformat()
        success = db.save_async(
            patient_id=f"test#{i//10}",
            time_str=timestamp,
            cgm=100 + i,
            cho=i % 20,
            basal=0.8,
            bolus=float(i % 5),
            insulin=0.8 + float(i % 5),
        )

        if not success:
            print(f"第 {i} 条加入队列失败")

        time.sleep(0.01)  # 模拟实时数据

    print("\n等待写入完成...\n")
    time.sleep(3)

    # 统计
    stats = db.get_stats()
    print(f"队列剩余: {stats['queue_size']}")
    print(f"总写入: {stats['total_writes']}")
    print(f"失败: {stats['failed_writes']}")
    print(f"溢出: {stats['queue_overflow']}")

    # 停止
    db.stop()
    print("\n测试完成")
