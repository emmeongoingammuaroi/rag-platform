"""Alias entry point for `python -m app.eval.run`."""

from app.eval.__main__ import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
