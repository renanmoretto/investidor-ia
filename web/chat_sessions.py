import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from src import db
from src.settings import INVESTORS

logger = logging.getLogger(__name__)

COOKIE_NAME = 'chat_session'
# the chats are saved, so the cookie must outlive the browser session to find them again
COOKIE_MAX_AGE = 60 * 60 * 24 * 365
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
    # set when a new conversation replaces this one; an answer still in progress must not be saved then
    replaced: bool = False

    @property
    def streaming(self) -> bool:
        return self.run is not None and not self.run.done

    def request_stop(self):
        if self.streaming and self.run.task:
            self.run.task.cancel()

    def save_message(self, message: dict):
        if self.replaced:
            return
        db.add_chat_message(self.agent_session_id, message)


@dataclass
class ChatSession:
    id: str
    last_investor: str = DEFAULT_INVESTOR
    chats: dict[str, Chat] = field(default_factory=dict)

    @property
    def running(self) -> list[str]:
        return [investor for investor, chat in self.chats.items() if chat.streaming]

    def open(self, investor: str) -> Chat:
        """The chat of the investor, set as the one to show when the user comes back."""
        if self.last_investor != investor:
            self.last_investor = investor
            db.save_chat_session(self.id, investor)
        return self.chat(investor)

    def chat(self, investor: str) -> Chat:
        if investor not in self.chats:
            self._new_chat(investor)
        return self.chats[investor]

    def reset_chat(self, investor: str) -> Chat:
        old = self.chats.get(investor)
        if old:
            old.replaced = True
            old.request_stop()
        logger.info('chat reset session=%s investor=%s', self.id, investor)
        return self._new_chat(investor)

    def _new_chat(self, investor: str) -> Chat:
        chat = Chat(investor=investor)
        self.chats[investor] = chat
        db.save_chat(self.id, investor, chat.agent_session_id)
        return chat


_sessions: dict[str, ChatSession] = {}


def get(session_id: str | None) -> ChatSession | None:
    if not session_id:
        return None
    if session_id not in _sessions:
        saved = db.get_chat_session(session_id)
        if not saved:
            return None
        _sessions[session_id] = ChatSession(
            id=saved['id'],
            last_investor=saved['last_investor'] if saved['last_investor'] in INVESTORS else DEFAULT_INVESTOR,
            chats={chat['investor']: Chat(**chat) for chat in saved['chats'] if chat['investor'] in INVESTORS},
        )
        logger.info('chat session loaded id=%s chats=%d', session_id, len(_sessions[session_id].chats))
    return _sessions[session_id]


def get_or_create(session_id: str | None) -> ChatSession:
    session = get(session_id)
    if not session:
        session = ChatSession(id=uuid.uuid4().hex)
        _sessions[session.id] = session
        db.save_chat_session(session.id, session.last_investor)
        logger.info('chat session created id=%s', session.id)
    return session
