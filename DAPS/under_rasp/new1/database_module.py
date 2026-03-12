import pymysql
from config_module import DB_CONFIG


def connect_mysql():
    """连接到MySQL数据库"""
    try:
        connection = pymysql.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            db=DB_CONFIG["db"],
            charset=DB_CONFIG["charset"],
            cursorclass=pymysql.cursors.DictCursor,
        )
        print("MySQL数据库连接成功")
        return connection
    except Exception as e:
        print(f"MySQL连接错误: {e}")
        return None


def save_to_database(connection, patient_id, time_str, cgm, cho, basal, bolus, insulin):
    """保存数据到数据库"""
    if not connection:
        return False

    # 检查连接是否可用，若不可用则重连
    try:
        connection.ping(reconnect=True)
    except:
        connection = connect_mysql()
        if not connection:
            return False

    cursor = connection.cursor()
    sql = "INSERT INTO BG_Datas (patient_id, time, cgm, cho, basal, bolus, insulin) VALUES (%s, %s, %s, %s, %s, %s, %s)"

    try:
        cursor.execute(sql, (patient_id, time_str, cgm, cho, basal, bolus, insulin))
        connection.commit()
        print("数据成功保存到数据库")
        return True
    except Exception as e:
        print(f"数据库保存错误: {e}")
        connection.rollback()
        return False
