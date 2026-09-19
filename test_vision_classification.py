import asyncio
import base64
import json
import httpx
from app.config import settings
from app.services.vision_service import _parse_entity_output, ENTITY_EXTRACTION_PROMPT

async def run_test():
    key = settings.effective_nvidia_api_key
    url = f"{settings.NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    test_images = [
        ("Leaf Spot", "/app/test_leaf.jpg"),
        ("Chemical Packet", "/app/test_chem.jpg"),
        ("Non-agri Laptop", "/app/test_other.jpg")
    ]

    async with httpx.AsyncClient(timeout=30) as client:
        for label, img_path in test_images:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": "meta/llama-3.2-11b-vision-instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ENTITY_EXTRACTION_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.1
            }
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                raw = r.json()["choices"][0]["message"]["content"]
                parsed = _parse_entity_output(raw)
                print(f"=== TEST: {label} ===")
                print("RAW OUTPUT:\n", raw)
                print("PARSED RESULT:\n", json.dumps(parsed, indent=2))
            else:
                print(f"=== TEST: {label} FAILED: HTTP {r.status_code} ===")

if __name__ == "__main__":
    asyncio.run(run_test())
