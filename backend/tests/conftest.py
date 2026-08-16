"""Shared test fixtures.

The DB engine is a module-level singleton, but pytest-asyncio builds a fresh event
loop per test. asyncpg pools bind to the loop that created them, so the second
DB-touching test in a run inherits connections owned by a dead loop and fails
intermittently ("coroutine 'Connection._cancel' was never awaited", InterfaceError).

Disposing the singleton after each test makes every test build its pool on its own
loop, which removes that whole class of flakiness.
"""

import pytest_asyncio

import src.database as _db


@pytest_asyncio.fixture(autouse=True)
async def reset_db_engine_between_tests():
    yield
    engine = getattr(_db, "_db_engine", None)
    if engine is not None:
        try:
            await engine.dispose()
        except Exception:
            pass
    _db._db_engine = None
    _db._db_session_factory = None
