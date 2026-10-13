"""Convenience entry point: `python run.py`, or press Run/Debug on this file in your IDE.

Equivalent to `python -m bot`. It lives in the project root so the `bot`
package is always importable, no matter how you launch it.
"""

import asyncio

from bot.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
