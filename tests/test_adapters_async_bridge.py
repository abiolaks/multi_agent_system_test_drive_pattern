from __future__ import annotations

import asyncio
import unittest

from fabric_qa.adapters.async_bridge import run_sync


async def _double(x: int) -> int:
    return x * 2


class TestRunSync(unittest.TestCase):
    def test_runs_a_coroutine_when_no_event_loop_is_active(self) -> None:
        result = run_sync(_double(21))

        self.assertEqual(result, 42)

    def test_propagates_the_coroutines_exception(self) -> None:
        async def boom() -> None:
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            run_sync(boom())


class TestRunSyncFromWithinARunningLoop(unittest.IsolatedAsyncioTestCase):
    async def test_runs_a_coroutine_when_called_from_inside_a_running_event_loop(self) -> None:
        # this async test method's body runs on the test runner's own
        # event loop thread, so calling run_sync directly here (not via
        # asyncio.to_thread, which would move to a fresh thread with no
        # loop of its own) exercises the exact failure mode this module
        # exists to avoid: plain asyncio.run() here would raise
        # "asyncio.run() cannot be called from a running event loop"
        asyncio.get_running_loop()  # sanity-check a loop really is active

        result = run_sync(_double(21))

        self.assertEqual(result, 42)


if __name__ == "__main__":
    unittest.main()
