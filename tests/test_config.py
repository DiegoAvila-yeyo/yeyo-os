import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.config import DATABASE_URL, REDIS_URL, NODE_ENV

def test_database_url_loaded():
    assert DATABASE_URL is not None
    assert "yeyo_db" in DATABASE_URL

def test_redis_url_loaded():
    assert REDIS_URL is not None
    assert "6379" in REDIS_URL

def test_node_env_loaded():
    assert NODE_ENV == "development"
