"""
用户行为跟踪系统
Week 5 Day 3: 智能数据分析平台 - 用户行为跟踪
收集、分析和存储用户行为数据，支持实时处理和模式识别
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import hashlib
import statistics

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """事件类型枚举"""
    PAGE_VIEW = "page_view"
    API_CALL = "api_call"
    USER_ACTION = "user_action"
    ERROR_OCCURRED = "error_occurred"
    PERFORMANCE_METRIC = "performance_metric"
    BUSINESS_EVENT = "business_event"
    SYSTEM_EVENT = "system_event"

class ActionType(str, Enum):
    """用户行为类型"""
    CLICK = "click"
    SCROLL = "scroll"
    HOVER = "hover"
    INPUT = "input"
    SUBMIT = "submit"
    NAVIGATE = "navigate"
    DOWNLOAD = "download"
    SEARCH = "search"
    FILTER = "filter"
    SORT = "sort"

@dataclass
class UserEvent:
    """用户行为事件"""
    event_id: str
    user_id: str
    session_id: str
    event_type: EventType
    action_type: Optional[ActionType] = None
    timestamp: datetime = None
    url: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    properties: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.properties is None:
            self.properties = {}
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        if self.action_type:
            data['action_type'] = self.action_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserEvent':
        """从字典创建事件"""
        data['event_type'] = EventType(data['event_type'])
        if 'action_type' in data and data['action_type']:
            data['action_type'] = ActionType(data['action_type'])
        if 'timestamp' in data:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class UserSession:
    """用户会话"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    page_views: int = 0
    api_calls: int = 0
    total_duration: Optional[float] = None
    bounce_rate: Optional[float] = None
    conversion_events: int = 0
    error_count: int = 0
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}

    def update_duration(self):
        """更新会话持续时间"""
        if self.end_time and self.start_time:
            self.total_duration = (self.end_time - self.start_time).total_seconds()

class BehaviorTracker:
    """行为跟踪器"""

    def __init__(self, buffer_size: int = 10000):
        self.buffer_size = buffer_size
        self.event_buffer: deque = deque(maxlen=buffer_size)
        self.sessions: Dict[str, UserSession] = {}
        self.user_profiles: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.real_time_processors: List[Callable] = []
        self._running = False

    async def start_tracking(self):
        """开始跟踪"""
        self._running = True
        logger.info("用户行为跟踪已启动")

        # 启动后台处理任务
        asyncio.create_task(self._process_events())

    async def stop_tracking(self):
        """停止跟踪"""
        self._running = False
        logger.info("用户行为跟踪已停止")

    def track_event(self, event: UserEvent):
        """跟踪单个事件"""
        # 添加到缓冲区
        self.event_buffer.append(event)

        # 更新会话信息
        self._update_session(event)

        # 更新用户档案
        self._update_user_profile(event)

        # 实时处理
        for processor in self.real_time_processors:
            try:
                asyncio.create_task(processor(event))
            except Exception as e:
                logger.error(f"实时处理器错误: {e}")

    def track_page_view(self, user_id: str, session_id: str, url: str, **kwargs):
        """跟踪页面访问"""
        event = UserEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            event_type=EventType.PAGE_VIEW,
            url=url,
            properties=kwargs
        )
        self.track_event(event)

    def track_api_call(self, user_id: str, session_id: str, endpoint: str, method: str,
                      status_code: int, response_time: float, **kwargs):
        """跟踪API调用"""
        event = UserEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            event_type=EventType.API_CALL,
            properties={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time": response_time,
                **kwargs
            }
        )
        self.track_event(event)

    def track_user_action(self, user_id: str, session_id: str, action_type: ActionType,
                         element: str, page: str, **kwargs):
        """跟踪用户操作"""
        event = UserEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            event_type=EventType.USER_ACTION,
            action_type=action_type,
            properties={
                "element": element,
                "page": page,
                **kwargs
            }
        )
        self.track_event(event)

    def track_error(self, user_id: str, session_id: str, error_type: str,
                   error_message: str, context: Dict[str, Any] = None):
        """跟踪错误事件"""
        event = UserEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            event_type=EventType.ERROR_OCCURRED,
            properties={
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {}
            }
        )
        self.track_event(event)

    def _update_session(self, event: UserEvent):
        """更新会话信息"""
        session_id = event.session_id
        user_id = event.user_id

        if session_id not in self.sessions:
            self.sessions[session_id] = UserSession(
                session_id=session_id,
                user_id=user_id,
                start_time=event.timestamp
            )

        session = self.sessions[session_id]
        session.end_time = event.timestamp

        # 更新会话统计
        if event.event_type == EventType.PAGE_VIEW:
            session.page_views += 1
        elif event.event_type == EventType.API_CALL:
            session.api_calls += 1
        elif event.event_type == EventType.ERROR_OCCURRED:
            session.error_count += 1

        # 检查是否为转化事件
        if self._is_conversion_event(event):
            session.conversion_events += 1

        session.update_duration()

    def _update_user_profile(self, event: UserEvent):
        """更新用户档案"""
        user_id = event.user_id
        profile = self.user_profiles[user_id]

        # 更新基础信息
        profile["last_activity"] = event.timestamp
        profile["total_events"] = profile.get("total_events", 0) + 1
        profile["session_count"] = len(set([
            e.session_id for e in self.event_buffer
            if e.user_id == user_id
        ]))

        # 更新行为偏好
        if event.event_type == EventType.PAGE_VIEW:
            profile["most_visited_pages"] = self._update_counter(
                profile.get("most_visited_pages", {}),
                event.url or "unknown"
            )

        elif event.event_type == EventType.USER_ACTION and event.action_type:
            profile["most_common_actions"] = self._update_counter(
                profile.get("most_common_actions", {}),
                event.action_type.value
            )

        # 更新设备信息
        if event.user_agent:
            profile["devices"] = self._update_counter(
                profile.get("devices", {}),
                self._extract_device_type(event.user_agent)
            )

    def _is_conversion_event(self, event: UserEvent) -> bool:
        """判断是否为转化事件"""
        conversion_events = [
            "signup", "purchase", "subscribe", "upgrade", "download"
        ]

        properties = event.properties or {}
        return any(event_type in str(properties).lower() for event_type in conversion_events)

    def _update_counter(self, counter: Dict[str, int], key: str) -> Dict[str, int]:
        """更新计数器"""
        counter[key] = counter.get(key, 0) + 1
        return dict(sorted(counter.items(), key=lambda x: x[1], reverse=True)[:10])

    def _extract_device_type(self, user_agent: str) -> str:
        """提取设备类型"""
        user_agent_lower = user_agent.lower()
        if "mobile" in user_agent_lower:
            return "mobile"
        elif "tablet" in user_agent_lower:
            return "tablet"
        else:
            return "desktop"

    async def _process_events(self):
        """后台事件处理"""
        while self._running:
            try:
                # 处理缓冲区中的事件
                if self.event_buffer:
                    events_to_process = list(self.event_buffer)
                    for event in events_to_process:
                        await self._process_single_event(event)

                # 等待一段时间再处理
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"事件处理错误: {e}")
                await asyncio.sleep(5)

    async def _process_single_event(self, event: UserEvent):
        """处理单个事件"""
        # 调用事件处理器
        for handler in self.event_handlers.get(event.event_type, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")

    def add_event_handler(self, event_type: EventType, handler: Callable):
        """添加事件处理器"""
        self.event_handlers[event_type].append(handler)

    def add_real_time_processor(self, processor: Callable):
        """添加实时处理器"""
        self.real_time_processors.append(processor)

    def get_user_events(self, user_id: str, limit: int = 100) -> List[UserEvent]:
        """获取用户事件"""
        user_events = [
            event for event in self.event_buffer
            if event.user_id == user_id
        ]
        return sorted(user_events, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_session_events(self, session_id: str) -> List[UserEvent]:
        """获取会话事件"""
        return [
            event for event in self.event_buffer
            if event.session_id == session_id
        ]

    def get_user_session(self, session_id: str) -> Optional[UserSession]:
        """获取用户会话"""
        return self.sessions.get(session_id)

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案"""
        return dict(self.user_profiles.get(user_id, {}))

    def get_active_sessions(self, minutes: int = 30) -> List[UserSession]:
        """获取活跃会话"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        return [
            session for session in self.sessions.values()
            if session.end_time and session.end_time > cutoff_time
        ]

    def get_event_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取事件统计"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [
            event for event in self.event_buffer
            if event.timestamp > cutoff_time
        ]

        stats = {
            "total_events": len(recent_events),
            "unique_users": len(set(event.user_id for event in recent_events)),
            "unique_sessions": len(set(event.session_id for event in recent_events)),
            "event_types": defaultdict(int),
            "action_types": defaultdict(int),
            "top_pages": defaultdict(int),
            "error_rate": 0
        }

        error_count = 0
        for event in recent_events:
            stats["event_types"][event.event_type.value] += 1

            if event.action_type:
                stats["action_types"][event.action_type.value] += 1

            if event.url:
                stats["top_pages"][event.url] += 1

            if event.event_type == EventType.ERROR_OCCURRED:
                error_count += 1

        # 计算错误率
        if stats["total_events"] > 0:
            stats["error_rate"] = (error_count / stats["total_events"]) * 100

        # 转换为普通字典并排序
        stats["event_types"] = dict(sorted(stats["event_types"].items(), key=lambda x: x[1], reverse=True))
        stats["action_types"] = dict(sorted(stats["action_types"].items(), key=lambda x: x[1], reverse=True))
        stats["top_pages"] = dict(sorted(stats["top_pages"].items(), key=lambda x: x[1], reverse=True)[:10])

        return stats

# 全局行为跟踪器实例
behavior_tracker = BehaviorTracker()

def get_behavior_tracker() -> BehaviorTracker:
    """获取行为跟踪器实例"""
    return behavior_tracker

# 便捷函数
def track_page_view(user_id: str, session_id: str, url: str, **kwargs):
    """便捷页面访问跟踪"""
    behavior_tracker.track_page_view(user_id, session_id, url, **kwargs)

def track_api_call(user_id: str, session_id: str, endpoint: str, method: str,
                  status_code: int, response_time: float, **kwargs):
    """便捷API调用跟踪"""
    behavior_tracker.track_api_call(user_id, session_id, endpoint, method,
                                  status_code, response_time, **kwargs)

def track_user_action(user_id: str, session_id: str, action_type: ActionType,
                     element: str, page: str, **kwargs):
    """便捷用户操作跟踪"""
    behavior_tracker.track_user_action(user_id, session_id, action_type,
                                      element, page, **kwargs)