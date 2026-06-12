# config.py
import os

USE_MOCK = os.getenv("USE_MOCK", "false").strip().lower() in {"1", "true", "yes", "on"}
BASE_URL = os.getenv("BASE_URL", "http://47.108.254.241:8000").rstrip("/")
