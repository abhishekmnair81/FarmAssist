import asyncio
import base64
import httpx
import os
import json

prompt = """Analyze this image carefully for an agricultural diagnosis and advisory system.
First inspect what is shown:
- Is it a chemical container, pesticide bottle, insecticide sachet, fertilizer bag, or printed product label?
- Or is it a living plant, crop, leaf, foliage, stem, or fruit showing plant symptoms?
- Or is it non-agricultural?

Classify the image into exactly ONE category:
1. "AGROCHEMICAL" - For physical bottles, sachets, packets, cartons, cans, or chemical labels (pesticide, insecticide, fungicide, herbicide, fertilizer).
2. "CROP_LEAF" - For living agricultural crops, plant leaves, field foliage, or plant diseases/pests.
3. "NON_AGRICULTURAL" - For anything not related to agriculture.

Respond ONLY with valid JSON in this schema:
{
  "classification": "AGROCHEMICAL or CROP_LEAF or NON_AGRICULTURAL",
  "agrochemical": {
    "brand_name": null,
    "active_ingredient": null,
    "category": null,
    "visible_instructions": null
  },
  "crop_leaf": {
    "crop_name": null,
    "suspected_issue": null,
    "issue_type": null,
    "symptoms": null,
    "severity": null
  },
  "visual_summary": "description"
}"""

async def test():
    key = os.environ.get('NVIDIA_API_KEY')
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    for name, p in [('CHEM', '/app/test_chem.jpg'), ('LEAF', '/app/test_leaf.jpg')]:
        with open(p, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post('https://integrate.api.nvidia.com/v1/chat/completions',
                headers=headers,
                json={'model': 'meta/llama-3.2-11b-vision-instruct',
                      'messages': [{'role': 'user', 'content': [
                          {'type': 'text', 'text': prompt},
                          {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
                      ]}], 'max_tokens': 300, 'temperature': 0.1})
            print(f'=== {name} ===')
            print(r.json()['choices'][0]['message']['content'])

if __name__ == '__main__':
    asyncio.run(test())
