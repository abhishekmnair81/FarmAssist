import asyncio
import os
import httpx
from app.config import settings

async def check_one(client, model, key):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
        "temperature": 0.1
    }
    try:
        r = await client.post(url, headers=headers, json=payload, timeout=6.0)
        if r.status_code == 200:
            print(f"[OK] {model}", flush=True)
            return model
    except Exception:
        pass
    return None

async def main():
    key = settings.effective_nvidia_api_key
    async with httpx.AsyncClient() as client:
        r = await client.get("https://integrate.api.nvidia.com/v1/models", headers={"Authorization": f"Bearer {key}"})
        if r.status_code != 200:
            print("Failed to get models")
            return
        all_models = [m["id"] for m in r.json().get("data", [])]
        print(f"Testing {len(all_models)} models concurrently...", flush=True)
        tasks = [check_one(client, m, key) for m in all_models]
        results = await asyncio.gather(*tasks)
        working = [m for m in results if m]
        print(f"\n--- WORKING MODELS ({len(working)}) ---", flush=True)
        for w in working:
            print(w, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
