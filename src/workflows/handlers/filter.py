"""YeyoOS — AI-powered filter / scoring workflow handler."""

import logging
import re

logger = logging.getLogger("yeyoos.workflows.handlers.filter")


async def handle_filter(config: dict, variables: dict) -> dict:
    """Score input text against criteria using an AI judge.

    Internally delegates to :func:`handle_chat` to obtain a numeric score.

    Config:
        input_text (str): The text to evaluate.
        criteria (str): Natural-language description of the criteria.
        threshold (float): Minimum score to pass (default 0.5).

    Returns:
        dict with ``score``, ``passed``, and ``input``.
    """
    input_text: str = config.get("input_text", "")
    criteria: str = config.get("criteria", "")
    threshold: float = config.get("threshold", 0.5)

    if not input_text:
        return {"error": "input_text is required"}
    if not criteria:
        return {"error": "criteria is required"}

    try:
        from src.workflows.handlers.chat import handle_chat

        scoring_prompt = (
            "You are a strict scoring assistant. "
            "Score the following INPUT against the CRITERIA on a scale from 0.0 to 1.0. "
            "Reply with ONLY the numeric score (e.g. 0.72). No explanation.\n\n"
            f"CRITERIA: {criteria}\n\n"
            f"INPUT: {input_text}"
        )

        chat_result = await handle_chat(
            {"prompt": scoring_prompt, "model": config.get("model", "qwen2.5-coder:7b")},
            variables,
        )

        if "error" in chat_result:
            return {"error": f"Chat sub-call failed: {chat_result['error']}"}

        raw = chat_result.get("response", "").strip()
        match = re.search(r"(\d+(?:\.\d+)?)", raw)
        if not match:
            return {"error": f"Could not parse score from AI response: {raw!r}"}

        score = float(match.group(1))
        score = max(0.0, min(1.0, score))
        passed = score >= threshold

        logger.info("Filter score=%.2f threshold=%.2f passed=%s", score, threshold, passed)
        return {"score": score, "passed": passed, "input": input_text}

    except Exception as e:
        logger.exception("Filter handler failed")
        return {"error": str(e)}
