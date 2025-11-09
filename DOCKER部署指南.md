# 🐳 BTC自动交易机器人 - Docker部署指南

## 📋 目录
- [为什么使用Docker](#为什么使用docker)
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [详细步骤](#详细步骤)
- [容器管理](#容器管理)
- [数据持久化](#数据持久化)
- [故障排除](#故障排除)
- [高级配置](#高级配置)

---

## 🎯 为什么使用Docker

### 优势
✅ **环境一致性** - 无需担心Python版本、依赖冲突  
✅ **快速部署** - 一条命令启动整个系统  
✅ **易于管理** - 统一的启动、停止、重启操作  
✅ **隔离性** - 不影响宿主机环境  
✅ **便携性** - 可在任何支持Docker的系统运行  
✅ **自动重启** - 容器异常退出会自动重启  

### 架构（v2.0 - 单容器架构）
```
┌──────────────────────────────────────┐
│         Docker Container             │
│      btc-trading-bot (统一)          │
├──────────────────────────────────────┤
│  run.py (主进程)                     │
│  ├─ Process 1: deepseekok2.py       │
│  │  - 交易逻辑                       │
│  │  - AI分析                         │
│  │  - OKX API                        │
│  │                                   │
│  └─ Process 2: streamlit            │
│     - Web界面                        │
│     - 数据展示                       │
│     - 实时监控                       │
├──────────────────────────────────────┤
│  端口: 8501                          │
│  自动重启: enabled                   │
│  健康检查: enabled                   │
└────────┬─────────────────────────────┘
         │
         ▼
┌────────────────────┐
│   共享数据卷       │
│  - trading_data    │
│  - trades_history  │
└────────────────────┘
```

**新架构优势：**
- ✅ 单容器管理，更简单
- ✅ 进程间通信更快
- ✅ 资源占用更少
- ✅ 统一日志输出
- ✅ 一键启动停止

---

## 🔧 前置要求

### 1. 安装Docker

#### Windows
- 下载并安装 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- 需要Windows 10 64位 (专业版、企业版或教育版) 或 Windows 11

#### macOS
- 下载并安装 [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- 支持 Intel 芯片和 Apple Silicon (M1/M2)

#### Linux
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装docker-compose
sudo apt-get install docker-compose-plugin
```

### 2. 验证安装
```bash
docker --version
docker-compose --version
```

应该看到类似输出：
```
Docker version 24.0.x
Docker Compose version v2.x.x
```

---

## 🚀 快速开始

### 一键启动（推荐）

#### Windows
```bash
# 双击运行
docker-start.bat
```

#### Linux/Mac
```bash
# 添加执行权限
chmod +x docker-start.sh docker-stop.sh

# 启动
./docker-start.sh
```

### 访问Web界面
浏览器打开：**http://localhost:8501**

---

## 📚 详细步骤

### 步骤1：准备配置文件

1. **复制环境变量模板**
```bash
# Linux/Mac
cp env.template .env

# Windows
copy env.template .env
```

2. **编辑.env文件，填入API密钥**
```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
OKX_API_KEY=xxxxxxxxxxxxx
OKX_SECRET=xxxxxxxxxxxxx
OKX_PASSWORD=xxxxxxxxxxxxx
```

### 步骤2：构建镜像

```bash
docker-compose build
```

这将：
- 拉取Python 3.11基础镜像
- 安装所有依赖包
- 构建统一的容器镜像（包含交易程序 + Web界面）
- 配置`run.py`作为启动入口

### 步骤3：启动服务

```bash
# 后台运行
docker-compose up -d

# 前台运行（查看实时日志）
docker-compose up
```

### 步骤4：验证服务

```bash
# 查看容器状态
docker-compose ps

# 应该看到容器正在运行
# NAME               STATUS
# btc-trading-bot    Up X minutes (healthy)
```

---

## 🎮 容器管理

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 停止并删除容器
docker-compose down

# 查看服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看最近的日志
docker-compose logs --tail=50

# 进入容器内部
docker exec -it btc-trading-bot bash

# 查看容器内进程
docker exec btc-trading-bot ps aux

# 重新构建镜像
docker-compose build --no-cache

# 查看资源占用
docker stats
```

### 快速脚本

#### Windows
```bash
# 启动
docker-start.bat

# 停止
docker-stop.bat
```

#### Linux/Mac
```bash
# 启动
./docker-start.sh

# 停止
./docker-stop.sh
```

---

## 💾 数据持久化

### 数据存储位置

所有数据文件都通过Docker卷挂载到宿主机：

```yaml
volumes:
  - ./trading_data.json:/app/trading_data.json    # 系统状态
  - ./trades_history.json:/app/trades_history.json # 交易历史
  - ./data:/app/data                               # 其他数据
```

### 备份数据

```bash
# 备份所有数据文件
mkdir backup_$(date +%Y%m%d)
cp trading_data.json trades_history.json backup_$(date +%Y%m%d)/
```

### 恢复数据

```bash
# 停止容器
docker-compose down

# 恢复数据文件
cp backup_20240101/trading_data.json .
cp backup_20240101/trades_history.json .

# 重启容器
docker-compose up -d
```

---

## 🔍 故障排除

### 问题1：容器无法启动

**症状**：`docker-compose up -d` 后容器立即退出

**排查步骤**：
```bash
# 查看容器日志
docker-compose logs

# 检查容器状态
docker-compose ps

# 查看详细日志
docker-compose logs --tail=100
```

**常见原因**：
- `.env` 文件配置错误
- API密钥无效
- 端口被占用

### 问题2：端口被占用

**错误信息**：`Bind for 0.0.0.0:8501 failed: port is already allocated`

**解决方案**：
```bash
# 方案1：修改端口
# 编辑 docker-compose.yml，将 8501:8501 改为 8502:8501
ports:
  - "8502:8501"

# 方案2：停止占用端口的程序
# Windows
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8501
kill -9 <PID>
```

### 问题3：无法访问Web界面

**排查步骤**：
```bash
# 1. 检查容器是否运行
docker-compose ps

# 2. 检查容器健康状态
docker inspect btc-trading-bot | grep -A 5 Health

# 3. 查看日志
docker-compose logs --tail=50

# 4. 测试容器内部网络
docker exec btc-trading-bot curl -f http://localhost:8501/_stcore/health

# 5. 检查进程
docker exec btc-trading-bot ps aux | grep -E "run.py|streamlit"
```

### 问题4：容器频繁重启

**排查步骤**：
```bash
# 查看详细日志
docker-compose logs --tail=100

# 查看重启次数
docker inspect btc-trading-bot --format='{{.RestartCount}}'

# 常见原因：
# - API密钥错误
# - 网络连接问题
# - 账户模式不匹配（逐仓/全仓）
# - run.py进程异常退出
```

### 问题5：数据不同步

**症状**：Web界面显示旧数据或无数据

**解决方案**：
```bash
# 1. 检查数据文件权限
ls -l trading_data.json trades_history.json

# 2. 检查卷挂载
docker inspect btc-trading-bot | grep -A 10 Mounts

# 3. 检查run.py进程
docker exec btc-trading-bot ps aux | grep run.py

# 4. 重启容器
docker-compose restart
```

---

## ⚙️ 高级配置

### 自定义端口

编辑 `docker-compose.yml`：
```yaml
btc-trading-bot:
  ports:
    - "8888:8501"  # 改为8888端口
```

### 资源限制

编辑 `docker-compose.yml`：
```yaml
btc-trading-bot:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1024M
      reservations:
        cpus: '0.5'
        memory: 512M
```

### 自定义网络

```yaml
networks:
  trading-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 日志配置

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"    # 单个日志文件最大50MB
    max-file: "5"      # 保留5个日志文件
```

### 使用外部数据卷

```yaml
volumes:
  data:
    external: true
    name: btc-trading-data
```

```bash
# 创建外部卷
docker volume create btc-trading-data
```

---

## 🌐 远程部署

### 部署到云服务器

```bash
# 1. 连接到云服务器
ssh user@your-server.com

# 2. 克隆项目
git clone <your-repo>
cd ds-okx

# 3. 配置.env
cp env.template .env
vim .env

# 4. 启动服务
docker-compose up -d

# 5. 配置防火墙（开放8501端口）
# Ubuntu/Debian
sudo ufw allow 8501

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

### 使用反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 启用HTTPS

```bash
# 使用Certbot获取免费SSL证书
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 📊 监控和维护

### 查看资源使用

```bash
# 实时监控
docker stats

# 查看磁盘使用
docker system df

# 清理未使用的镜像和容器
docker system prune -a
```

### 定期备份

创建备份脚本 `backup.sh`：
```bash
#!/bin/bash
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp trading_data.json trades_history.json $BACKUP_DIR/
tar -czf ${BACKUP_DIR}.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR
echo "备份完成: ${BACKUP_DIR}.tar.gz"
```

### 自动更新

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d
```

---

## 🔒 安全建议

1. **保护.env文件**
   ```bash
   chmod 600 .env
   ```

2. **使用只读卷（可选）**
   ```yaml
   volumes:
     - ./config.yml:/app/config.yml:ro
   ```

3. **限制容器权限**
   ```yaml
   security_opt:
     - no-new-privileges:true
   ```

4. **定期更新镜像**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

---

## 📞 获取帮助

### 查看日志
```bash
# 查看所有日志
docker-compose logs

# 实时跟踪日志
docker-compose logs -f --tail=50

# 导出日志到文件
docker-compose logs > logs.txt
```

### 常见问题检查清单

- [ ] Docker和docker-compose是否正确安装
- [ ] `.env`文件是否存在并配置正确
- [ ] API密钥是否有效
- [ ] 端口8501是否被占用
- [ ] 容器是否在运行：`docker-compose ps`
- [ ] 日志中是否有错误信息
- [ ] 数据文件权限是否正确

---

## 🎉 总结

Docker部署让您的BTC交易机器人：
- ✅ 5分钟内完成部署
- ✅ 环境隔离，不污染系统
- ✅ 自动重启，稳定运行
- ✅ 易于维护和更新
- ✅ 支持一键备份和恢复

**开始使用：**
```bash
# Windows
docker-start.bat

# Linux/Mac
./docker-start.sh

# 访问Web界面
http://localhost:8501
```

**祝您交易顺利！** 🚀

