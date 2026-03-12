# 🚀 TCP通信快速参考

## 一分钟快速启动

### 仿真模式测试
```bash
# 1. 启动Rasp（仿真）
cd e:\GitHub\DAPS\under_rasp
python rasp_integration.py --sim

# 2. 新开终端，测试TCP
python test_tcp_communication.py
```

### Backend集成测试
```bash
# 1. 配置Backend端口
set TCP_TARGET_PORT=5000

# 2. 启动Rasp（仿真）
cd e:\GitHub\DAPS\under_rasp
python rasp_integration.py --sim

# 3. 启动Backend
cd e:\GitHub\DAPS\ddd_database_fb\backend
python simulator.py
```

---

## 📝 关键命令

| 命令 | 说明 |
|------|------|
| `python rasp_integration.py --sim` | 仿真模式启动 |
| `python rasp_integration.py` | 真实硬件模式 |
| `python test_tcp_communication.py` | 自动TCP测试 |
| `python test_tcp_communication.py -i` | 交互式TCP测试 |
| `quick_test.bat` | Windows一键测试 |

---

## 🔧 配置检查清单

- [ ] Backend端口设置为5000 (环境变量或修改代码)
- [ ] 防火墙允许端口5000
- [ ] Python 3.7+ 已安装
- [ ] 依赖包已安装 (`pip install -r requirements.txt`)

---

## 📊 数据格式速查

**Backend→Rasp:**  
`patient_name,timestamp,bg,cgm,cho\n`  
示例: `John,1704067200.5,150,148,45\n`

**Rasp→Backend:**  
`insulin,basal,bolus\n`  
示例: `2.5000,1.2000,1.3000\n`

---

## 🐛 常见问题速查

| 问题 | 解决 |
|------|------|
| Connection refused | 检查rasp是否启动，端口是否正确 |
| 端口被占用 | `netstat -ano \| findstr 5000` 查找并关闭进程 |
| 响应为0.0 | 检查算法参数，查看bg/cho输入值 |
| Backend连接失败 | 确认端口配置为5000 |

---

## 📚 文档导航

- **详细指南:** `TCP_INTEGRATION_GUIDE.md` (600行)
- **完成总结:** `TCP_INTEGRATION_SUMMARY.md`
- **架构文档:** `ARCHITECTURE.md`
- **开发总结:** `DEVELOPMENT_SUMMARY.md`

---

## 🔍 调试技巧

```bash
# 实时查看日志
tail -f rasp_integration.log

# 检查端口监听
netstat -an | findstr 5000

# 手动发送TCP数据
python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1',5000)); s.send(b'John,1704067200.5,150,148,45\n'); print(s.recv(1024)); s.close()"
```

---

**快速获取帮助:** 查看 `TCP_INTEGRATION_GUIDE.md` 故障排查章节
