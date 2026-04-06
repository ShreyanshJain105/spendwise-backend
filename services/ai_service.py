"""AI-powered financial advisor service using NVIDIA API (Gemma 3n model)."""

import json
import logging
import os
from typing import Optional

import requests as http_requests

logger = logging.getLogger(__name__)

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "google/gemma-3n-e2b-it"

SYSTEM_PROMPT = """You are SpendWise AI, a friendly and knowledgeable personal finance advisor embedded in a personal finance tracking app.

Your role:
- Analyze the user's financial data and give concise, actionable advice
- Help users understand their spending patterns
- Suggest budgeting strategies and savings tips
- Answer general personal finance questions
- Be encouraging but honest about areas for improvement

Rules:
- Keep responses concise (2-4 paragraphs max)
- Use specific numbers from the user's data when available
- Format currency as ₹ (Indian Rupees)
- Never recommend specific stocks, crypto, or investment products
- If you don't have enough data, say so and give general advice
- Use bullet points for actionable tips
- Be warm and supportive in tone"""


def _get_api_key() -> Optional[str]:
    """Retrieve NVIDIA API key from environment."""
    return os.getenv("NVIDIA_API_KEY")


def _build_context_message(summary: Optional[dict]) -> str:
    """Build a financial context string from the user's account summary."""
    if not summary:
        return "No financial data available for this user yet."

    parts = [
        f"User's Financial Summary:",
        f"- Total Income: ₹{summary.get('total_income', '0')}",
        f"- Total Expenses: ₹{summary.get('total_expense', '0')}",
        f"- Balance: ₹{summary.get('balance', '0')}",
        f"- Total Transactions: {summary.get('transaction_count', 0)}",
    ]

    by_category = summary.get("by_category", {})
    if by_category:
        parts.append("- Spending by Category:")
        for cat, amt in by_category.items():
            parts.append(f"  • {cat}: ₹{amt}")

    budget_status = summary.get("budget_status", [])
    if budget_status:
        parts.append("- Budget Status:")
        for b in budget_status:
            parts.append(
                f"  • {b['category']}: ₹{b['spent_this_month']}/{b['limit']} "
                f"({b['percentage']}% used)"
            )

    return "\n".join(parts)


def get_financial_advice(
    user_message: str,
    summary: Optional[dict] = None,
) -> str:
    """Get AI-powered financial advice.

    Args:
        user_message: The user's question or request.
        summary: Optional account summary dict for personalized context.

    Returns:
        The AI assistant's response text.

    Raises:
        RuntimeError: If the API call fails.
    """
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("NVIDIA API key not configured")

    context = _build_context_message(summary)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n\n---\n\nUser question: {user_message}"},
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.20,
        "top_p": 0.70,
        "frequency_penalty": 0.00,
        "presence_penalty": 0.00,
        "stream": True,
    }

    try:
        response = http_requests.post(
            NVIDIA_API_URL, headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()
    except http_requests.RequestException as e:
        logger.error("NVIDIA API request failed: %s", e)
        raise RuntimeError(f"AI service unavailable: {e}")

    # Parse SSE stream and collect content
    full_reply = []
    for line in response.iter_lines():
        if not line:
            continue
        decoded = line.decode("utf-8")
        if not decoded.startswith("data: "):
            continue
        data_str = decoded[6:]  # strip "data: "
        if data_str.strip() == "[DONE]":
            break
        try:
            chunk = json.loads(data_str)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                full_reply.append(content)
        except json.JSONDecodeError:
            continue

    reply = "".join(full_reply).strip()
    if not reply:
        reply = "I'm sorry, I couldn't generate advice right now. Please try again."

    return reply
