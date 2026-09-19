import httpx
import os
import asyncio
import base64
import json

prompt = """Analyze this image carefully for an agricultural decision support system.
Classify the image into exactly ONE category and extract all details in strictly valid JSON format.

Categories:
1. "AGROCHEMICAL": A bottle, packet, can, sachet, drum, or container of pesticide, insecticide, fungicide, herbicide, fertilizer, or growth regulator.
2. "CROP_LEAF": A growing plant, leaf, crop, fruit, stem, or tree showing health, disease, pest damage, fungal lesions, or spots.
3. "NON_AGRICULTURAL": Any image not related to crops, plants, farm chemicals, or agriculture.

CRITICAL CLASSIFICATION RULE:
- If you see a green leaf or plant with disease spots or insect damage, the classification is ALWAYS "CROP_LEAF", NEVER "AGROCHEMICAL".
- Only classify as "AGROCHEMICAL" if the image shows an actual physical container, bottle, packet, sachet, or printed label of a chemical product.

Respond ONLY with a single JSON object in this schema:
{
  "classification": "CROP_LEAF",
  "agrochemical": {
    "brand_name": "",
    "active_ingredient": "",
    "category": "",
    "visible_instructions": ""
  },
  "crop_leaf": {
    "crop_name": "Plant",
    "suspected_issue": "Fungal Leaf Spot",
    "issue_type": "FUNGAL",
    "symptoms": "Brown circular spots with yellow halo",
    "severity": "MODERATE"
  },
  "visual_summary": "Leaf with fungal spots"
}"""

async def test():
    key = os.environ.get('NVIDIA_API_KEY')
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    imgs = [('LEAF', '/app/test_leaf.jpg'), ('CHEM', '/app/test_chem.jpg'), ('OTHER', '/app/test_other.jpg')]
    async with httpx.AsyncClient(timeout=30) as client:
        for name, p in imgs:
            with open(p, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            res = await client.post('https://integrate.api.nvidia.com/v1/chat/completions',
                headers=headers,
                json={
                    'model': 'meta/llama-3.2-11b-vision-instruct',
                    'messages': [{'role': 'user', 'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
                    ]}],
                    'max_tokens': 300,
                    'temperature': 0.1
                })
            print(f'=== {name} ===')
            print(res.json()['choices'][0]['message']['content'])

if __name__ == '__main__':
    asyncio.run(test())
