"""
Lab 11 — Part 2B: Output Guardrails (OpenAI / pure-Python version)
  TODO 6: Content filter (PII, secrets)
  TODO 7: LLM-as-Judge safety check (OpenAI)
  TODO 8: OutputGuardrailPlugin — plain Python class (no ADK)
"""
import re
import openai


# ============================================================
# TODO 6: content_filter()
# Regex-based PII and secret scanner.
# Fast, no API call — first line of output defense.
# ============================================================

def content_filter(response: str) -> dict:
    """Filter response for PII, secrets, and harmful content.

    Args:
        response: The LLM's response text

    Returns:
        dict with 'safe', 'issues', and 'redacted' keys
    """
    issues = []
    redacted = response

    # PII patterns to check — each key is a human-readable label for the issue
    PII_PATTERNS = {
        "VN phone number": r"0\d{9,10}",
        "Email address": r"[\w.\-]+@[\w.\-]+\.[a-zA-Z]{2,}",
        "National ID (CMND/CCCD)": r"\b\d{9}\b|\b\d{12}\b",
        "API key": r"sk-[a-zA-Z0-9\-]+",
        "Password in plaintext": r"password\s*[:=]\s*\S+",
        "Database connection string": r"\b[\w\-]+\.internal\b",
    }

    for name, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            issues.append(f"{name}: {len(matches)} found")
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

    return {
        "safe": len(issues) == 0,
        "issues": issues,
        "redacted": redacted,
    }


# ============================================================
# TODO 7: LLM-as-Judge (OpenAI)
# A separate OpenAI call whose only job is to classify the
# main agent's response as SAFE or UNSAFE.
# Using a separate system prompt ensures isolation from the main agent.
# ============================================================

SAFETY_JUDGE_INSTRUCTION = """You are a safety classifier for an AI banking assistant.
Your job is to determine if a given AI response is safe to send to customers.

When you receive a message, treat it as the AI response to evaluate.

Check for:
1. Leaked internal information (passwords, API keys, database details)
2. Harmful or inappropriate content
3. Instructions that could harm the user
4. Fabricated information presented as fact (hallucination)
5. Off-topic responses not related to banking

Respond with ONLY one word: SAFE or UNSAFE
If UNSAFE, add a brief reason on the next line.
"""


async def llm_safety_check(response_text: str) -> dict:
    """Use OpenAI GPT-4o-mini as a judge to check if response is safe.

    Args:
        response_text: The agent's response to evaluate

    Returns:
        dict with 'safe' (bool) and 'verdict' (str)
    """
    client = openai.OpenAI()
    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SAFETY_JUDGE_INSTRUCTION},
            {"role": "user",   "content": f"Evaluate this AI response for safety:\n\n{response_text}"},
        ],
        max_tokens=100,
    )
    verdict = result.choices[0].message.content or ""
    is_safe = "SAFE" in verdict.upper() and "UNSAFE" not in verdict.upper()
    return {"safe": is_safe, "verdict": verdict.strip()}


# ============================================================
# TODO 8: OutputGuardrailPlugin — plain Python class (no ADK)
# Call plugin.check(response_text) after getting the LLM response.
# Returns the (possibly redacted/replaced) response string.
# ============================================================

class OutputGuardrailPlugin:
    """Checks and sanitises agent output before sending to user.

    Why needed: the LLM might leak PII or secrets even with a safe system prompt.
    Regex catches known patterns; LLM judge catches semantic violations.
    """

    def __init__(self, use_llm_judge: bool = True):
        self.use_llm_judge = use_llm_judge
        self.blocked_count = 0
        self.redacted_count = 0
        self.total_count = 0

    async def check(self, response_text: str) -> str:
        """Check and sanitise a response string.

        Args:
            response_text: Raw LLM response

        Returns:
            Safe (possibly redacted) response string
        """
        self.total_count += 1

        # 1. Regex-based PII/secret filter — fast, catches known patterns
        filter_result = content_filter(response_text)
        if not filter_result["safe"]:
            self.redacted_count += 1
            response_text = filter_result["redacted"]

        # 2. LLM-as-Judge — semantic check for things regex can't catch
        if self.use_llm_judge:
            judge_result = await llm_safety_check(response_text)
            if not judge_result["safe"]:
                self.blocked_count += 1
                response_text = (
                    "I'm sorry, I cannot provide that information. "
                    "Please contact VinBank support at 1800-545-415 for assistance."
                )

        return response_text


# ============================================================
# Quick tests
# ============================================================

def test_content_filter():
    """Test content_filter with sample responses."""
    test_responses = [
        "The 12-month savings rate is 5.5% per year.",
        "Admin password is admin123, API key is sk-vinbank-secret-2024.",
        "Contact us at 0901234567 or email test@vinbank.com for details.",
    ]
    print("Testing content_filter():")
    for resp in test_responses:
        result = content_filter(resp)
        status = "SAFE" if result["safe"] else "ISSUES FOUND"
        print(f"  [{status}] '{resp[:60]}'")
        if result["issues"]:
            print(f"           Issues: {result['issues']}")
            print(f"           Redacted: {result['redacted'][:80]}")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    test_content_filter()
