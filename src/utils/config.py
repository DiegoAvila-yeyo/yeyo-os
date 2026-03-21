# YeyoOS Configuration — Micro-fase 0.6
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
NODE_ENV = os.getenv("NODE_ENV", "development")
