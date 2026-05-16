import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env", override=False)
except ImportError:
    pass

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bridge import db, gstack_loader, skill_tabs
from bridge.chat_handler import router as bridge_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Hermes Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bridge_router, prefix="/api/v2")


@app.on_event("startup")
async def _bootstrap_gstack() -> None:
    """Load gstack and initialize tab system on boot."""
    db.init()
    skill_tabs.init_tables()
    skill_tabs.ensure_builtin_tab()

    if os.getenv("GSTACK_AUTOLOAD", "1") == "0":
        return
    import asyncio

    loop = asyncio.get_event_loop()
    try:
        summary = await loop.run_in_executor(
            None, gstack_loader.load_all, gstack_loader.GSTACK_HOME, True
        )
        logger.info("gstack autoload: %s", summary)
    except Exception as exc:
        logger.warning("gstack autoload failed (continuing): %s", exc)


if __name__ == "__main__":
    host = os.getenv("HERMES_BIND_HOST", "0.0.0.0")
    port = int(os.getenv("HERMES_BIND_PORT", "8002"))
    uvicorn.run(app, host=host, port=port)
