import logging
import threading
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

COOKIE_NAME = 'chat_session'


@dataclass
class ChatSession:
    id: str
    investor: str = 'buffett'
    messages: list[dict] = field(default_factory=list)


_sessions: dict[str, ChatSession] = {}
_lock = threading.Lock()


def get_or_create(session_id: str | None) -> ChatSession:
    with _lock:
        if session_id and session_id in _sessions:
            return _sessions[session_id]
        session = ChatSession(id=session_id or uuid.uuid4().hex)
        _sessions[session.id] = session
        logger.info('chat session created id=%s', session.id)
        return session


def reset(session_id: str | None) -> ChatSession:
    with _lock:
        _sessions.pop(session_id, None)
    logger.info('chat session reset id=%s', session_id)
    return get_or_create(None)
