import os

import requests

DEFAULT_MODEL = "llama-3.3-70b-versatile"


def synthesize_answer(query: str, chunks: list[dict]) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    context = "\n\n".join(
        f"[{i + 1}] (artifact {c['artifact_id'][:8]}, commit {c['commit_ref'][:8]}): {c['text']}"
        for i, c in enumerate(chunks)
    )
    prompt = (
        "Answer the question using ONLY the numbered excerpts below. Cite the excerpt "
        "number(s) you used, like [1] or [2][3]. If the excerpts don't contain the "
        "answer, say so plainly instead of guessing.\n\n"
        f"Excerpts:\n{context}\n\nQuestion: {query}"
    )

    api_url = os.environ.get("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
    model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
