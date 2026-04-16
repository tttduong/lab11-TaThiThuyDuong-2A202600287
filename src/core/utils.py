"""
Lab 11 — Helper Utilities (OpenAI version)
"""
import openai


async def chat_with_agent(agent: dict, user_message: str, session_id=None):
    """Send a message to an agent (dict) and get the response via OpenAI.

    Args:
        agent: Dict with 'system_prompt' and 'model' keys
        user_message: Plain text message to send
        session_id: Unused — kept for API compatibility with original signature

    Returns:
        Tuple of (response_text, None)  — None replaces the old session object
    """
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=agent.get("model", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user",   "content": user_message},
        ],
    )
    text = response.choices[0].message.content or ""
    return text, None
