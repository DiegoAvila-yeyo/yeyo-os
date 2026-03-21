import httpx
import os
from dotenv import load_dotenv

load_dotenv()

def test_ollama_api_reachable():
    r = httpx.get(f"{os.getenv('OLLAMA_HOST')}/api/tags")
    assert r.status_code == 200

def test_ollama_generate():
    r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/generate", json={
        "model": os.getenv('OLLAMA_MODEL'),
        "prompt": "Say OK",
        "stream": False
    }, timeout=60)
    assert r.status_code == 200
    assert "response" in r.json()
    assert len(r.json()["response"]) > 0

def test_ollama_chat():
    r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/chat", json={
        "model": os.getenv('OLLAMA_MODEL'),
        "messages": [{"role": "user", "content": "Say hello"}],
        "stream": False
    }, timeout=60)
    assert r.status_code == 200
    assert "message" in r.json()
