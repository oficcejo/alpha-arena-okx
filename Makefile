# BTC自动交易机器人 - Makefile
# 提供便捷的管理命令

.PHONY: help build up down restart logs logs-bot logs-web status clean backup

# 默认目标：显示帮助
help:
	@echo "========================================="
	@echo "BTC自动交易机器人 - 管理命令"
	@echo "========================================="
	@echo ""
	@echo "部署相关:"
	@echo "  make build      - 构建Docker镜像"
	@echo "  make up         - 启动服务"
	@echo "  make down       - 停止服务"
	@echo "  make restart    - 重启服务"
	@echo ""
	@echo "监控相关:"
	@echo "  make logs       - 查看所有日志"
	@echo "  make logs-bot   - 查看交易程序日志"
	@echo "  make logs-web   - 查看Web界面日志"
	@echo "  make status     - 查看服务状态"
	@echo ""
	@echo "维护相关:"
	@echo "  make clean      - 清理容器和镜像"
	@echo "  make backup     - 备份数据文件"
	@echo "  make update     - 更新并重新部署"
	@echo ""

# 构建镜像
build:
	@echo "🔨 构建Docker镜像..."
	docker-compose build

# 启动服务
up:
	@echo "🚀 启动服务..."
	docker-compose up -d
	@echo "✅ 服务已启动"
	@echo "🌐 访问Web界面: http://localhost:8501"

# 停止服务
down:
	@echo "🛑 停止服务..."
	docker-compose down
	@echo "✅ 服务已停止"

# 重启服务
restart:
	@echo "🔄 重启服务..."
	docker-compose restart
	@echo "✅ 服务已重启"

# 查看所有日志
logs:
	docker-compose logs -f

# 查看交易程序日志
logs-bot:
	docker-compose logs -f trading-bot

# 查看Web界面日志
logs-web:
	docker-compose logs -f web-interface

# 查看服务状态
status:
	@echo "========================================="
	@echo "服务状态"
	@echo "========================================="
	docker-compose ps
	@echo ""
	@echo "========================================="
	@echo "资源使用"
	@echo "========================================="
	docker stats --no-stream

# 清理容器和镜像
clean:
	@echo "🧹 清理容器和镜像..."
	docker-compose down --rmi all -v
	@echo "✅ 清理完成"

# 备份数据
backup:
	@echo "💾 备份数据..."
	@mkdir -p backup
	@cp trading_data.json backup/trading_data_$(shell date +%Y%m%d_%H%M%S).json 2>/dev/null || true
	@cp trades_history.json backup/trades_history_$(shell date +%Y%m%d_%H%M%S).json 2>/dev/null || true
	@echo "✅ 备份完成，文件保存在 backup/ 目录"

# 更新并重新部署
update:
	@echo "🔄 更新代码..."
	git pull
	@echo "🔨 重新构建..."
	docker-compose build --no-cache
	@echo "🚀 重新部署..."
	docker-compose up -d
	@echo "✅ 更新完成"

# 快速启动（首次部署）
install: build up
	@echo ""
	@echo "========================================="
	@echo "部署完成！"
	@echo "========================================="
	@echo "🌐 Web界面: http://localhost:8501"
	@echo ""
	@echo "常用命令:"
	@echo "  make logs       - 查看日志"
	@echo "  make status     - 查看状态"
	@echo "  make restart    - 重启服务"
	@echo "========================================="

