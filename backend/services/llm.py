import os


CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def generate_answer(question: str, context_chunks: list[str]) -> str:
    if not context_chunks:
        return "I could not find relevant context in your uploaded documents."

    if _use_fake_llm():
        return _fallback_answer(question, context_chunks)

    client = _openai_client()
    context_block = "\n\n---\n\n".join(context_chunks)
    prompt = (
        "You are a retrieval-augmented assistant. Answer using only the provided context. "
        "If the context does not contain enough information, state that clearly.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_block}"
    )

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "Provide accurate answers grounded in the supplied context."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return (response.choices[0].message.content or "").strip()


def _use_fake_llm() -> bool:
    return os.getenv("RAG_USE_FAKE_LLM", "").lower() == "true" or not os.getenv("OPENAI_API_KEY")


def _openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required for LLM responses.") from exc
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _fallback_answer(question: str, context_chunks: list[str]) -> str:
    preview = " ".join(context_chunks)[:1200]
    return (
        "Generated in fallback mode (no OpenAI API key configured).\n"
        f"Question: {question}\n"
        f"Most relevant context excerpt: {preview}"
    )
