import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from src.settings import INVESTORS

logger = logging.getLogger(__name__)

COOKIE_NAME = 'chat_session'
DEFAULT_INVESTOR = next(iter(INVESTORS))


class Run:
    """One answer in progress. It runs as a background task, so it continues when the browser
    leaves the page. It keeps all its events, so a browser can follow it from the start at any time."""

    def __init__(self):
        self.events: list[dict] = []
        self.done = False
        self.task: asyncio.Task | None = None
        self._changed = asyncio.Event()

    def publish(self, event: dict):
        self.events.append(event)
        self._changed.set()

    def finish(self):
        self.done = True
        self._changed.set()

    async def follow(self) -> AsyncIterator[dict]:
        sent = 0
        while True:
            while sent < len(self.events):
                yield self.events[sent]
                sent += 1
            if self.done:
                return
            # no await between the checks above and clear(), so an event cannot be lost
            self._changed.clear()
            await self._changed.wait()


@dataclass
class Chat:
    investor: str
    agent_session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    messages: list[dict] = field(default_factory=list)
    run: Run | None = None

    @property
    def streaming(self) -> bool:
        return self.run is not None and not self.run.done

    def request_stop(self):
        if self.streaming and self.run.task:
            self.run.task.cancel()


@dataclass
class ChatSession:
    id: str
    last_investor: str = DEFAULT_INVESTOR
    chats: dict[str, Chat] = field(default_factory=dict)

    @property
    def running(self) -> list[str]:
        return [investor for investor, chat in self.chats.items() if chat.streaming]

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


def get(session_id: str | None) -> ChatSession | None:
    return _sessions.get(session_id) if session_id else None


def get_or_create(session_id: str | None) -> ChatSession:
    session = get(session_id)
    if not session:
        session = ChatSession(id=uuid.uuid4().hex)
        _sessions[session.id] = session
        logger.info('chat session created id=%s', session.id)
    return session
