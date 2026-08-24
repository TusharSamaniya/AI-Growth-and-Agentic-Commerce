# A tiny in-memory pub/sub bus for Server-Sent Events. Each open /events
# connection subscribes (gets its own queue); publish() fans an event out to all
# of them. In-memory only: it resets on restart and does NOT replay past events
# to late subscribers — fine for live "payment received" nudges, while polling
# and the webhook remain the durable source of truth for an order's status.
import asyncio


# Every open SSE connection registers its queue here.
_subscribers: set[asyncio.Queue] = set()


def subscribe() -> asyncio.Queue:
    """Register a new subscriber; returns the queue the /events stream drains."""
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    """Drop a subscriber when its connection closes."""
    _subscribers.discard(queue)


def publish(event: str) -> None:
    """Fan an event string out to every connected subscriber."""
    for queue in _subscribers:
        queue.put_nowait(event)
