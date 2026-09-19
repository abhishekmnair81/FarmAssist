import asyncio, httpx
from app.config import settings

async def check_models():
    # Check Groq models
    print('--- GROQ MODELS ---')
    headers = {'Authorization': f'Bearer {settings.GROQ_API_KEY}'}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get('https://api.groq.com/openai/v1/models', headers=headers)
            if r.status_code == 200:
                models = [m['id'] for m in r.json()['data']]
                vision_models = [m for m in models if 'vision' in m.lower()]
                print('Groq Vision models:', vision_models)
                print('Sample Groq models:', models[:15])
            else:
                print('Groq status:', r.status_code, r.text[:100])
        except Exception as e:
            print('Groq error:', e)

    # Check NVIDIA models
    print('\n--- NVIDIA NIM MODELS ---')
    key = settings.effective_nvidia_api_key
    n_headers = {'Authorization': f'Bearer {key}'}
    base_url = settings.NVIDIA_BASE_URL.rstrip('/')
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f'{base_url}/models', headers=n_headers)
            if r.status_code == 200:
                n_models = [m['id'] for m in r.json()['data']]
                print('Total NVIDIA models:', len(n_models))
                llama_models = [m for m in n_models if 'llama' in m.lower()]
                print('NVIDIA LLaMA models:', llama_models)
                mistral_models = [m for m in n_models if 'mistral' in m.lower()]
                print('NVIDIA Mistral models:', mistral_models)
                deepseek_models = [m for m in n_models if 'deepseek' in m.lower()]
                print('NVIDIA DeepSeek models:', deepseek_models)
            else:
                print('NVIDIA status:', r.status_code, r.text[:100])
        except Exception as e:
            print('NVIDIA error:', e)

if __name__ == '__main__':
    asyncio.run(check_models())
