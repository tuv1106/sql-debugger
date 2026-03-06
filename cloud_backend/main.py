import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloud_backend.config import ALLOWED_ORIGINS, LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="SQL Debugger — Cloud Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
