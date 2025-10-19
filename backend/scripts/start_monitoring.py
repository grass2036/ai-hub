#!/usr/bin/env python3
"""
系统监控服务启动脚本
Week 5 Day 3: 系统监控和运维自动化
"""

import asyncio
import signal
import sys
import logging
from contextlib import asynccontextmanager

from backend.core.logging_service import start_log_collection
from backend.core.monitoring_service import start_monitoring
from backend.core.health_checker import start_health_checks
from backend.core.notification_service import start_notification_processing

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/monitoring.log', 'a', 'utf-8')
    ]
)

logger = logging.getLogger(__name__)


class MonitoringServicesManager:
    """监控服务管理器"""

    def __init__(self):
        self.tasks = []
        self.running = False

    async def start_services(self):
        """启动所有监控服务"""
        logger.info("Starting AI Hub monitoring services...")

        # 启动日志收集服务
        logger.info("Starting log collection service...")
        log_task = asyncio.create_task(start_log_collection())
        self.tasks.append(log_task)

        # 启动监控服务
        logger.info("Starting metrics monitoring service...")
        monitor_task = asyncio.create_task(start_monitoring())
        self.tasks.append(monitor_task)

        # 启动健康检查服务
        logger.info("Starting health check service...")
        health_task = asyncio.create_task(start_health_checks())
        self.tasks.append(health_task)

        # 启动通知处理服务
        logger.info("Starting notification processing service...")
        notification_task = asyncio.create_task(start_notification_processing())
        self.tasks.append(notification_task)

        self.running = True
        logger.info("All monitoring services started successfully!")

    async def stop_services(self):
        """停止所有监控服务"""
        logger.info("Stopping monitoring services...")
        self.running = False

        # 取消所有任务
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Task {task.get_name()} cancelled")

        logger.info("All monitoring services stopped")

    async def handle_shutdown(self, signal_num, frame):
        """处理关闭信号"""
        logger.info(f"Received signal {signal_num}, shutting down...")
        await self.stop_services()
        sys.exit(0)


async def main():
    """主函数"""
    # 创建监控目录
    import os
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data/metrics", exist_ok=True)

    manager = MonitoringServicesManager()

    # 注册信号处理器
    def signal_handler(signum, frame):
        asyncio.create_task(manager.handle_shutdown(signum, frame))

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # 启动服务
        await manager.start_services()

        # 保持运行
        while manager.running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        await manager.stop_services()
    except Exception as e:
        logger.error(f"Fatal error in monitoring services: {e}")
        await manager.stop_services()
        raise


if __name__ == "__main__":
    asyncio.run(main())