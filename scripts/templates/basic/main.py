#!/usr/bin/env python3
"""
{{PROJECT_NAME}}
Created by {{DEVELOPER_NAME}} on {{DATE}}
"""

import asyncio
import logging
import argparse
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class {{PROJECT_NAME.replace('-', ' ').title().replace(' ', '')}}App:
    """应用主类"""

    def __init__(self):
        self.running = False

    async def initialize(self):
        """初始化应用"""
        logger.info("Initializing {{PROJECT_NAME}} application")
        # TODO: 实现初始化逻辑

    async def start(self):
        """启动应用"""
        logger.info("Starting {{PROJECT_NAME}} application")
        self.running = True

        try:
            # TODO: 实现应用主逻辑
            await self.run()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            await self.stop()

    async def run(self):
        """运行应用主循环"""
        while self.running:
            try:
                # TODO: 实现应用逻辑
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """停止应用"""
        logger.info("Stopping {{PROJECT_NAME}} application")
        self.running = False
        # TODO: 实现清理逻辑


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="{{PROJECT_NAME}}")
    parser.add_argument("--port", type=int, default=8000, help="端口号")
    parser.add_argument("--host", default="localhost", help="主机地址")
    parser.add_argument("--reload", action="store_true", help="自动重载")

    args = parser.parse_args()

    app = {{PROJECT_NAME.replace('-', ' ').title().replace(' ', '')}}App()
    await app.initialize()
    await app.start()


if __name__ == "__main__":
    asyncio.run(main())