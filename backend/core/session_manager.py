import json
import uuid
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class Message:
    id: str
    role: MessageRole
    content: str
    timestamp: str
    model: Optional[str] = None
    images: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    usage: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Session:
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    first_message: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)

class SessionManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        self.sessions_index_file = self.data_dir / "sessions_index.json"
        self._executor = ThreadPoolExecutor(max_workers=4)
        # 内存缓存
        self._sessions_cache: Dict[str, Session] = {}
        self._cache_ttl = 300  # 5分钟缓存
        self._cache_timestamps: Dict[str, float] = {}
    
    def generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        return str(uuid.uuid4())
    
    def generate_message_id(self) -> str:
        """生成唯一的消息ID"""
        return str(uuid.uuid4())

    def _is_cache_valid(self, session_id: str) -> bool:
        """检查缓存是否有效"""
        if session_id not in self._cache_timestamps:
            return False
        import time
        return time.time() - self._cache_timestamps[session_id] < self._cache_ttl

    def _update_cache(self, session_id: str, session: Session):
        """更新缓存"""
        import time
        self._sessions_cache[session_id] = session
        self._cache_timestamps[session_id] = time.time()

    async def _read_json_file(self, file_path: Path) -> Dict[str, Any]:
        """异步读取JSON文件"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: json.load(open(file_path, 'r', encoding='utf-8'))
        )

    async def _write_json_file(self, file_path: Path, data: Dict[str, Any]):
        """异步写入JSON文件"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            lambda: json.dump(data, open(file_path, 'w', encoding='utf-8'),
                            indent=2, ensure_ascii=False)
        )
    
    async def create_session(self, title: Optional[str] = None) -> Session:
        """创建新会话"""
        session_id = self.generate_session_id()
        now = datetime.now().isoformat()
        
        if not title:
            title = f"新对话 {datetime.now().strftime('%m-%d %H:%M')}"
        
        session = Session(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
            message_count=0
        )
        
        # 创建会话文件
        session_file = self.sessions_dir / f"{session_id}.json"
        session_data = {
            "session": session.to_dict(),
            "messages": []
        }

        await self._write_json_file(session_file, session_data)

        # 更新会话索引
        await self._update_sessions_index(session)

        # 更新缓存
        self._update_cache(session_id, session)

        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话信息（带缓存）"""
        # 检查缓存
        if self._is_cache_valid(session_id):
            return self._sessions_cache.get(session_id)

        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            data = await self._read_json_file(session_file)
            session_data = data.get("session", {})
            session = Session(**session_data)

            # 更新缓存
            self._update_cache(session_id, session)

            return session
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None
    
    async def add_message(self, session_id: str, role: MessageRole, content: str, 
                         model: Optional[str] = None, images: Optional[List[str]] = None,
                         attachments: Optional[List[str]] = None, 
                         usage: Optional[Dict[str, Any]] = None) -> Optional[Message]:
        """添加消息到会话"""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            # 读取现有数据
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 创建新消息
            message = Message(
                id=self.generate_message_id(),
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                model=model,
                images=images,
                attachments=attachments,
                usage=usage
            )
            
            # 添加消息
            data["messages"].append(message.to_dict())
            
            # 更新会话信息
            session = Session(**data["session"])
            session.updated_at = datetime.now().isoformat()
            session.message_count = len(data["messages"])
            
            # 如果是第一条用户消息，设置为会话标题
            if role == MessageRole.USER and session.message_count == 1:
                session.first_message = content[:50] + "..." if len(content) > 50 else content
                if not session.title or session.title.startswith("新对话"):
                    session.title = session.first_message
            
            data["session"] = session.to_dict()
            
            # 保存数据
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 更新索引
            await self._update_sessions_index(session)
            
            return message
            
        except Exception as e:
            print(f"Error adding message to session {session_id}: {e}")
            return None
    
    async def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """获取会话消息"""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return []
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages_data = data.get("messages", [])
            messages = [Message(**msg) for msg in messages_data]
            
            if limit:
                return messages[-limit:]
            return messages
            
        except Exception as e:
            print(f"Error loading messages from session {session_id}: {e}")
            return []
    
    async def get_conversation_context(self, session_id: str, max_messages: int = 10) -> List[Dict[str, str]]:
        """获取对话上下文（用于AI模型）"""
        messages = await self.get_messages(session_id)
        
        # 获取最近的消息
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        # 转换为AI模型格式
        context = []
        for msg in recent_messages:
            if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                context.append({
                    "role": str(msg.role),
                    "content": msg.content
                })
        
        return context
    
    async def list_sessions(self, limit: int = 50, search: Optional[str] = None) -> List[Session]:
        """列出所有会话"""
        try:
            if not self.sessions_index_file.exists():
                return []
            
            with open(self.sessions_index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            sessions_data = index_data.get("sessions", [])
            sessions = [Session(**session) for session in sessions_data]
            
            # 如果有搜索关键词，进行过滤
            if search:
                search_lower = search.lower()
                filtered_sessions = []
                for session in sessions:
                    # 搜索标题和首条消息
                    if (search_lower in session.title.lower() or 
                        (session.first_message and search_lower in session.first_message.lower())):
                        filtered_sessions.append(session)
                sessions = filtered_sessions
            
            # 按更新时间排序
            sessions.sort(key=lambda x: x.updated_at, reverse=True)
            
            return sessions[:limit]
            
        except Exception as e:
            print(f"Error listing sessions: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            
            if session_file.exists():
                session_file.unlink()
            
            # 从索引中移除
            await self._remove_from_index(session_id)
            
            return True
            
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False
    
    async def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return False
        
        try:
            # 读取现有数据
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 更新标题
            session = Session(**data["session"])
            session.title = title
            session.updated_at = datetime.now().isoformat()
            
            data["session"] = session.to_dict()
            
            # 保存数据
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 更新索引
            await self._update_sessions_index(session)
            
            return True
            
        except Exception as e:
            print(f"Error updating session title {session_id}: {e}")
            return False
    
    async def _update_sessions_index(self, session: Session):
        """更新会话索引"""
        try:
            # 读取现有索引
            if self.sessions_index_file.exists():
                with open(self.sessions_index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            else:
                index_data = {"sessions": []}
            
            sessions = index_data["sessions"]
            
            # 查找现有会话并更新，或添加新会话
            updated = False
            for i, existing_session in enumerate(sessions):
                if existing_session["id"] == session.id:
                    sessions[i] = session.to_dict()
                    updated = True
                    break
            
            if not updated:
                sessions.append(session.to_dict())
            
            # 保持最新的会话在前面，限制总数
            sessions.sort(key=lambda x: x["updated_at"], reverse=True)
            if len(sessions) > 1000:  # 限制最多1000个会话
                sessions = sessions[:1000]
            
            index_data["sessions"] = sessions
            
            # 保存索引
            with open(self.sessions_index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error updating sessions index: {e}")
    
    async def _remove_from_index(self, session_id: str):
        """从索引中移除会话"""
        try:
            if not self.sessions_index_file.exists():
                return
            
            with open(self.sessions_index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            sessions = index_data.get("sessions", [])
            sessions = [s for s in sessions if s["id"] != session_id]
            
            index_data["sessions"] = sessions
            
            with open(self.sessions_index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error removing session from index: {e}")
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        try:
            sessions = await self.list_sessions(limit=1000)
            
            total_sessions = len(sessions)
            total_messages = sum(session.message_count for session in sessions)
            
            # 按日期统计
            today = date.today().isoformat()
            today_sessions = len([s for s in sessions if s.created_at.startswith(today)])
            
            # 最活跃的会话
            most_active = max(sessions, key=lambda x: x.message_count) if sessions else None
            
            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "today_sessions": today_sessions,
                "most_active_session": {
                    "id": most_active.id,
                    "title": most_active.title,
                    "message_count": most_active.message_count
                } if most_active else None
            }
            
        except Exception as e:
            print(f"Error getting session stats: {e}")
            return {
                "total_sessions": 0,
                "total_messages": 0,
                "today_sessions": 0,
                "most_active_session": None
            }