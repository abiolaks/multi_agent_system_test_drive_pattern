from __future__ import annotations

import asyncio
import threading
from typing import Coroutine, TypeVar

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _background_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_lock:
        if _loop is None:
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, daemon=True).start()
            _loop = loop
        return _loop


def run_sync(coro: Coroutine[object, object, T]) -> T:
    """Run an async call from a sync Port method, on one persistent loop.

    Adapters (GraphEmailPort, FabricDataAgentPort) implement synchronous
    Port protocols but wrap async SDKs whose clients (GraphServiceClient,
    MCP ClientSession) hold resources bound to whichever event loop first
    used them. Two problems follow from that:

    1. Calling asyncio.run() directly conflicts with an event loop already
       running on the calling thread - which is exactly the case when
       these adapters are called from inside workflow.py's async ask().
    2. Spinning up a *fresh* loop per call (e.g. a new thread with its own
       asyncio.run() each time) avoids problem 1, but breaks a reused
       client's async resources on the second call, since they were bound
       to the first call's now-closed loop.

    Dispatching every call onto the same long-lived background loop avoids
    both: it never touches the caller's own loop, and any SDK client
    reused across calls consistently sees the same loop for the life of
    the process.
    """
    return asyncio.run_coroutine_threadsafe(coro, _background_loop()).result()
