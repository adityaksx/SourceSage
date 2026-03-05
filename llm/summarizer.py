import requests


def summarize(text):

    prompt = f"""
You are analyzing a developer learning resource.

Extract and return the following fields:

TITLE:
One clear title describing the content.

SUMMARY:
Explain the resource in 3–5 sentences.

KEY TOPICS:
List important technologies or concepts mentioned.

DIFFICULTY:
Beginner / Intermediate / Advanced

RESOURCE TYPE:
Tutorial / Course / Tool / GitHub Project / Article / Video

Content:
{text}
"""

    r = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    return r.json()["response"]