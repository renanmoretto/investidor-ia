import logging
import threading
import uuid
from dataclasses import dataclass, field

from src.settings import INVESTORS

logger = logging.getLogger(__name__)

COOKIE_NAME = 'chat_session'
DEFAULT_INVESTOR = next(iter(INVESTORS))


@dataclass
class Chat:
    investor: str
    agent_session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    messages: list[dict] = field(default_factory=list)
    streaming: bool = False
    stop: threading.Event = field(default_factory=threading.Event)

    def request_stop(self):
        """Stops the current answer. The chat is free for a new message at once,
        also when the agent is still blocked in a tool call."""
        self.stop.set()
        self.streaming = False
        if self.messages and self.messages[-1].get('status') == 'streaming':
            self.messages[-1]['status'] = 'stopped'


@dataclass
class ChatSession:
    id: str
    last_investor: str = DEFAULT_INVESTOR
    chats: dict[str, Chat] = field(default_factory=dict)

    def chat(self, investor: str) -> Chat:
        if investor not in self.chats:
            self.chats[investor] = Chat(investor=investor)
        return self.chats[investor]

    def reset_chat(self, investor: str) -> Chat:
        old = self.chats.get(investor)
        if old:
            old.request_stop()
        self.chats[investor] = Chat(investor=investor)
        logger.info('chat reset session=%s investor=%s', self.id, investor)
        return self.chats[investor]


_sessions: dict[str, ChatSession] = {}
_lock = threading.Lock()


def get_or_create(session_id: str | None) -> ChatSession:
    with _lock:
        if session_id and session_id in _sessions:
            return _sessions[session_id]
        session = ChatSession(id=uuid.uuid4().hex)
        _sessions[session.id] = session
        logger.info('chat session created id=%s', session.id)
        return session
