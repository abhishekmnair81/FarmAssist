import os
import time
import asyncio
import httpx
from app.config import settings

async def test():
    key = settings.effective_nvidia_api_key
    base_url = settings.NVIDIA_BASE_URL.rstrip("/")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    models_to_test = [
        ("Text", "mistralai/mistral-7b-instruct-v0.3"),
        ("Text", "mistralai/mistral-large-2-instruct"),
        ("Text", "nvidia/llama-3.1-nemotron-70b-instruct"),
        ("Vision", "meta/llama-3.2-11b-vision-instruct"),
        ("Vision", "meta/llama-3.2-90b-vision-instruct"),
    ]

    async with httpx.AsyncClient() as client:
        for mtype, model in models_to_test:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Reply with only: PONG"}],
                "max_tokens": 10,
                "temperature": 0.1
            }
            start = time.time()
            try:
                r = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=25.0)
                elapsed = time.time() - start
                if r.status_code == 200:
                    ans = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    print(f"[{mtype}] {model}: SUCCESS ({elapsed:.2f}s) -> '{ans}'")
                else:
                    print(f"[{mtype}] {model}: HTTP {r.status_code} ({elapsed:.2f}s) -> {r.text[:100]}")
            except Exception as e:
                elapsed = time.time() - start
                print(f"[{mtype}] {model}: ERROR ({elapsed:.2f}s) -> {e}")

if __name__ == "__main__":
    asyncio.run(test())
