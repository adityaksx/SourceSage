# llm/ollama_client.py

import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

# Only 1 Ollama call at a time — prevents HTTP 500 on concurrent requests
_ollama_semaphore = asyncio.Semaphore(1)

OLLAMA_URL = "http://localhost:11434/api/generate"
TIMEOUT = 90  # seconds


async def ollama_generate(model: str, prompt: str, stream: bool = False) -> str:
    """
    Single shared async function for all Ollama calls.
    Semaphore ensures no concurrent requests to Ollama.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }

    async with _ollama_semaphore:
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    response = await client.post(OLLAMA_URL, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return data.get("response", "").strip()

            except httpx.ConnectError:
                logger.error("[OLLAMA] Not running. Start with: ollama serve")
                return ""

            except httpx.HTTPStatusError as e:
                if attempt < 2:
                    logger.warning(f"[OLLAMA] HTTP {e.response.status_code}, retry {attempt+1}/3...")
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    logger.error(f"[OLLAMA] HTTP error after 3 retries: {e}")
                    return ""

            except Exception as e:
                logger.error(f"[OLLAMA] Unexpected error: {e}")
                return ""
