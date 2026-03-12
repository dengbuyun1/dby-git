# 数据库配置说明

## 1. 安装MariaDB/MySQL

确保你的系统已安装MariaDB或MySQL数据库服务器。

## 2. 创建数据库

```sql
CREATE DATABASE vsim CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 3. 创建数据库用户(可选)

```sql
-- 创建专用用户
CREATE USER 'vsim_user'@'localhost' IDENTIFIED BY 'your_password';

-- 授予权限
GRANT ALL PRIVILEGES ON vsim.* TO 'vsim_user'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;
```

## 4. 配置数据库连接

编辑 `backend/database.py` 文件中的数据库配置:

```python
DB_CONFIG = {
    'host': 'localhost',        # 数据库主机地址
    'port': 3306,               # 数据库端口
    'user': 'root',             # 数据库用户名(修改为你的用户名)
    'password': '',             # 数据库密码(修改为你的密码)
    'db': 'vsim',              # 数据库名
    'charset': 'utf8mb4',
    'autocommit': True
}
```

## 5. 安装Python依赖

```bash
cd backend
pip install -r requirements.txt
```

主要依赖:
- websockets: WebSocket服务器
- aiomysql: 异步MySQL客户端
- PyMySQL: MySQL驱动

## 6. 数据库表结构

程序会自动创建以下两个表:

### simulation_meta (仿真元数据表)
- id: 仿真ID(自增主键)
- start_time: 开始时间
- person: 患者姓名
- sensor: 传感器类型
- pump: 泵类型
- controller: 控制器类型
- simulate_hours: 仿真时长(小时)
- simulate_times: 采样次数
- data_count: 数据点数
- created_at: 创建时间
- updated_at: 更新时间
- status: 状态(running/completed/error)

### simulation_data (仿真数据表)
- id: 仿真ID(外键)
- i: 数据索引
- sin: SIN值
- cos: COS值
- tan: TAN值

## 7. 启动服务器

```bash
cd backend
python base.py
```

服务器会自动:
1. 连接数据库
2. 创建必要的表(如果不存在)
3. 启动WebSocket服务器

## 8. 前端使用

前端会通过WebSocket连接到后端:
- 查看仿真记录列表
- 查看仿真数据图表
- 运行新的仿真(自动保存到数据库)
- 删除仿真记录

## 常见问题

### Q: 连接数据库失败
A: 检查以下内容:
1. MariaDB/MySQL服务是否启动
2. database.py中的配置是否正确
3. 用户名密码是否正确
4. 数据库vsim是否已创建

### Q: 表不存在
A: 程序会自动创建表,如果遇到问题,可以手动执行:
```sql
USE vsim;
SHOW TABLES;
```

### Q: 权限不足
A: 确保数据库用户有CREATE、INSERT、SELECT、UPDATE、DELETE权限
