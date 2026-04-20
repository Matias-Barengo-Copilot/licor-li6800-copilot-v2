import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(name)s — %(message)s",
)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routers import chat, pages, ws

app = FastAPI(title="LI-COR LI-6800 — Post-Purchase Experience")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(chat.router)
app.include_router(ws.router)
