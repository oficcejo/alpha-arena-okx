# OKX BTC交易机器人 - 智能交易系统

## 老版本进场判断较好，但出场时机判断不是很佳，特引入新的策略和创建新的ai提示词

## 新版本正在调试策略中，为能稳定盈利，请大家耐心等待。

### 11.1测试进展--目前经几天不断调整策略，11月1日测试1天，胜率很高，为减少大家不必要损失，新版本源码再测试一段时间更新上传，请大家耐心等待

**新版支持BTC\ETH\SOL，可自由设定，使用ict-2022策略交易，进出场更加准确**

[多币种ICT策略ai机器人演示网站multi-okx.zhongdu.net](http://192.227.137.234:5003/)

<img width="1910" height="923" alt="image" src="https://github.com/user-attachments/assets/708e9f82-2f91-4eee-be39-f1361d7fd601" />
<img width="1910" height="923" alt="image" src="https://github.com/user-attachments/assets/e77c54aa-a250-4e40-95b7-c361d7896d15" />
<img width="1910" height="923" alt="image" src="https://github.com/user-attachments/assets/72de12c2-96af-4f65-95d6-9c3acaeb50cb" />


## 项目概述
**（以下源码为老版单币种版，经测试实现持续亏损，于11月1日暂停测试，不建议新手部署使用，请耐心等待新版更新）**

这是一个基于DeepSeek AI的OKX BTC/USDT自动交易系统，集成了实时数据分析、AI决策和Web可视化界面。支持Docker容器化部署，确保系统稳定运行。
<img width="1910" height="923" alt="image" src="https://github.com/user-attachments/assets/04c39b2b-6d16-42bc-b6ea-a716419034e9" />
<img width="1910" height="923" alt="image" src="https://github.com/user-attachments/assets/442e402e-64e9-41c9-85cc-71e041bc14b9" />

## 🚀 功能特性


### 🤖 交易机器人
- **智能AI决策**: 使用DeepSeek AI分析市场趋势
- **技术指标分析**: RSI、MACD、布林带等完整技术指标
- **智能仓位管理**: 动态调整仓位大小
- **风险管理**: 自动止损止盈设置
- **实时监控**: 每15分钟自动执行分析
- **Docker容器化**: 独立进程运行，确保稳定性

### 🌐 Web展示界面
- **实时数据监控**: BTC价格、账户余额、持仓情况
- **AI决策展示**: 交易信号、信心程度、分析理由
- **图表可视化**: 价格走势图、绩效统计图表
- **交易记录**: 完整的交易历史记录
- **绩效分析**: 胜率、总盈亏、平均盈亏统计
- **Docker部署**: 独立Web服务，支持高可用

## 📁 系统架构

```
├── deepseekok2.py          # 主交易机器人
├── web_app.py              # Web服务器
├── data_manager.py         # 数据管理模块
├── Dockerfile              # Docker镜像配置
├── docker-compose.yml      # 多服务编排
├── docker-start.sh         # Linux/Mac启动脚本
├── docker-start.bat        # Windows启动脚本
├── .env.example           # 环境变量模板
├── DOCKER_DEPLOYMENT.md    # Docker部署指南
├── templates/              # Web模板
│   └── index.html          # 主界面
└── data/                   # 数据存储目录
    ├── system_status.json
    ├── trades.json
    └── performance.json
```

## 🏃‍♂️ 快速开始

### 服务器部署，推荐美国vps服务器部署，价格便宜，无需翻墙，自动运行，访问okx交易所速度快。
推荐美国老牌服务器厂商RackNerd稳定服务器**支持支付宝付款**
- [推荐：满足要求型：1核心1G内存24GSSD2T带宽11.29美元/年](https://my.racknerd.com/aff.php?aff=13902&pid=903)
- [进阶型：1核心2G内存40GSSD3.5T带宽18.29美元/年](https://my.racknerd.com/aff.php?aff=13902&pid=904)
- [推荐型：2核心3.5G内存65GSSD7T带宽32.49美元/年](https://my.racknerd.com/aff.php?aff=13902&pid=905)
- [高端型：4核心6G内存140GSSD12T带宽59.99美元/年](https://my.racknerd.com/aff.php?aff=13902&pid=907)

### 前期准备

#### 获取API密钥

**AI模型（二选一）：**

1. **DeepSeek API** (默认): https://platform.deepseek.com/
   - 注册账号
   - 创建API Key
   - 充值（按使用量计费，约0.14元/百万tokens）冲几十元能用1年
   - 模型：deepseek-chat

2. **阿里百炼 Qwen** (可选，后期支持): https://dashscope.console.aliyun.com/
   - 注册阿里云账号
   - 开通百炼服务
   - 创建API Key
   - 模型：qwen-max
   - 设置 `AI_PROVIDER=qwen`

**交易所：okx手机app是大陆唯一能用的交易所app，无需翻墙**

3. **OKX API**: https://www.gtohfmmy.com/join/6746503
   - 使用邀请码注册并完成任务，最高获100usdt奖励
   - API管理 → 创建API
   - 权限：需要"交易"权限
   - **重要**：妥善保管密钥，不要泄露


### 方法一：Docker部署（推荐）

#### 1. 配置环境变量

复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，设置您的API密钥：
```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_actual_deepseek_api_key

# OKX交易所配置
OKX_API_KEY=your_actual_okx_api_key
OKX_SECRET=your_actual_okx_secret
OKX_PASSWORD=your_actual_okx_password
```

#### 2. 启动Docker服务

首先进入目录

**Windows:**
```cmd
docker-start.bat
```

**Linux/Mac:**
```bash
chmod +x docker-start.sh
./docker-start.sh
```

或手动启动：
```bash
docker-compose up -d
```
**启动完毕会出现2个容器（宝塔面板为例）**

<img width="1621" height="295" alt="image" src="https://github.com/user-attachments/assets/cfb51c6d-d60e-4bb9-ae56-22e9aaa8641a" />

#### 3. 访问Web界面

打开浏览器访问: http://localhost:5002

### 方法二：传统部署

#### 创建环境​​windows
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### 1. 安装依赖
```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量
（同上）

#### 3. 分别启动服务

**终端1 - Web服务器:**
```bash
.\venv\Scripts\Activate.ps1 #windows激活虚拟环境
python web_app.py
```

**终端2 - 交易机器人:**
```bash
.\venv\Scripts\Activate.ps1
python deepseekok2.py
```

#### 4. 访问Web界面
http://localhost:5002

## 🖥️ Web界面功能

### 📊 实时监控面板
- **BTC价格**: 实时价格和涨跌幅
- **账户余额**: 可用资金和总资产
- **AI决策信号**: 当前交易信号和信心程度
- **持仓情况**: 当前持仓方向和盈亏

### 📈 图表分析
- **价格走势图**: BTC价格变化趋势
- **绩效统计**: 每日盈亏柱状图
- **交易信号标记**: 在价格图上标记交易点

### 📋 数据展示
- **交易记录**: 最近交易的时间、信号、价格、盈亏
- **AI分析详情**: 决策理由、止损止盈价格
- **技术指标**: RSI、MACD等指标状态

## ⚙️ 交易配置

在 `deepseekok2.py` 中可以调整交易参数：

*** 投入保证金计算公式=下单基数*信心系数*仓位比例%*趋势系数 ***
例：基数100usdt，高信心，仓位0.5，趋势，保证金=100*1.5*1.2=180，所投入保证金为180/10=18usdt

```python
TRADE_CONFIG = {
    'symbol': 'BTC/USDT:USDT',  # OKX的合约符号格式
    'leverage': 10,  # 杠杆倍数,只影响保证金不影响下单价值
    'timeframe': '15m',  # 使用15分钟K线
    'test_mode': False,  # 测试模式开关
    'data_points': 96,  # 24小时数据（96根15分钟K线）
    'analysis_periods': {
        'short_term': 20,  # 短期均线
        'medium_term': 50,  # 中期均线
        'long_term': 96  # 长期趋势
    },
    # 智能仓位参数
    'position_management': {
        'enable_intelligent_position': True,  # 🆕 新增：是否启用智能仓位管理
        'base_usdt_amount': 100,  # USDT投入下单基数
        'high_confidence_multiplier': 1.5,  # 高信心系数
        'medium_confidence_multiplier': 1.0,  # 中信心系数
        'low_confidence_multiplier': 0.5,  # 低信心系数
        'max_position_ratio': 50,  # 单次最大仓位比例默认50%
        'trend_strength_multiplier': 1.2  # 趋势系数
}
```

## 🐳 Docker常用管理命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看实时日志
```bash
docker-compose logs -f
```

### 查看特定服务日志
```bash
docker-compose logs -f web-app
docker-compose logs -f trading-bot
```

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 重新构建镜像
```bash
docker-compose build --no-cache
```

## 🔒 安全说明

⚠️ **重要安全提示**:

1. **实盘风险**: 请在模拟账户充分测试后再使用实盘
2. **API密钥安全**: 妥善保管交易所API密钥
3. **资金管理**: 合理设置仓位大小，避免过度杠杆
4. **监控运行**: 定期检查系统运行状态
5. **Docker安全**: 确保Docker环境安全，限制网络访问

## 🛠️ 故障排除

### 常见问题

**Q: Docker容器启动失败**
A: 检查.env文件配置和端口占用情况，查看详细日志：`docker-compose logs`

**Q: Web界面无法访问**
A: 检查5002端口是否被占用，或防火墙设置

**Q: 交易执行失败**
A: 检查API密钥权限和网络连接

**Q: 数据不更新**
A: 检查.env文件配置和网络连接

**Q: 交易机器人进程退出**
A: 检查Docker容器状态，查看交易机器人日志

### 日志查看

**Docker部署:**
```bash
docker-compose logs -f trading-bot  # 交易机器人日志
docker-compose logs -f web-app      # Web服务器日志
```

**传统部署:**
- 系统运行日志会实时显示在控制台
- Web界面数据存储在 `data/` 目录下

## 📊 数据持久化

- 交易数据存储在 `./data` 目录
- Docker部署时数据会持久化保存
- 支持数据备份和恢复

### 备份数据
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz data/
```

### 恢复数据
```bash
docker-compose down
tar -xzf backup-20231201.tar.gz
docker-compose up -d
```

## 🛠️ 技术栈

- **后端**: Python + Flask
- **前端**: HTML5 + Tailwind CSS + Chart.js
- **交易**: CCXT + OKX API
- **AI**: DeepSeek API
- **数据**: JSON文件存储
- **容器化**: Docker + Docker Compose

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。

---

**提示**: 交易有风险，投资需谨慎！

## 📚 相关文档

- [Docker部署指南](DOCKER_DEPLOYMENT.md) - 详细的Docker配置和故障排除
- [.env.example](.env.example) - 环境变量配置模板
