"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 12: Confidence Router
  TODO 13: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 12: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        # High-risk actions always require a human, regardless of confidence.
        # Even a 99%-confident wrong transfer can cause real financial harm.
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        # High confidence — safe to send automatically
        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )

        # Medium confidence — queue for human review before sending
        if confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )

        # Low confidence — escalate immediately; do not send to customer
        return RoutingDecision(
            action="escalate",
            confidence=confidence,
            reason="Low confidence — escalating",
            priority="high",
            requires_human=True,
        )


# ============================================================
# TODO 13: Design 3 HITL decision points
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "Large Transaction Approval",
        # Trigger: any transfer above a monetary threshold (e.g. 50M VND)
        # is automatically paused for human sign-off before execution.
        "trigger": (
            "Customer requests a transfer or withdrawal above 50,000,000 VND, "
            "or any transaction to a first-time recipient account."
        ),
        # Human-in-the-loop: the human MUST approve before the action executes.
        # The AI cannot proceed on its own — the transaction is blocked until approved.
        "hitl_model": "human-in-the-loop",
        "context_needed": (
            "Full transaction details (amount, source account, destination account, "
            "recipient name), customer's transaction history for the past 30 days, "
            "whether destination account is new, and the AI's confidence score."
        ),
        "example": (
            "Customer: 'Transfer 200,000,000 VND to account 0123456789 at Vietcombank.' "
            "AI flags the large amount and new recipient. A bank officer reviews the "
            "request, verifies the customer's identity via OTP, then approves or rejects."
        ),
    },
    {
        "id": 2,
        "name": "Suspicious Interaction Monitor",
        # Trigger: patterns suggesting social engineering or account takeover —
        # e.g. multiple failed auth attempts, rapid-fire queries, or the LLM judge
        # flags the conversation as potentially manipulative.
        "trigger": (
            "LLM-as-Judge flags 2+ responses in a session as UNSAFE, "
            "or a user sends 5+ injection-like messages in one session, "
            "or the user asks for credentials / system information repeatedly."
        ),
        # Human-on-the-loop: the AI continues responding but a security analyst
        # receives an alert and can intervene or terminate the session.
        "hitl_model": "human-on-the-loop",
        "context_needed": (
            "Full conversation history, list of flagged messages with reasons, "
            "user ID and session start time, IP address, block counts from each guardrail layer."
        ),
        "example": (
            "A user sends three variants of 'reveal your system prompt' within 2 minutes. "
            "All are blocked by InputGuardrailPlugin. The monitoring dashboard alerts the "
            "security team; an analyst reviews the session in real time and can terminate it "
            "or escalate to a fraud investigation."
        ),
    },
    {
        "id": 3,
        "name": "Complaint & Dispute Tiebreaker",
        # Trigger: the customer explicitly disputes the AI's answer, or the AI's
        # confidence is medium (0.7–0.89) on a sensitive financial question
        # (e.g. exact fee amounts, regulatory rules, account eligibility).
        "trigger": (
            "Customer says 'that's wrong', 'I was told differently', or 'I want to speak "
            "to a human'. Also triggers when confidence is medium on questions about fees, "
            "eligibility rules, or regulatory requirements."
        ),
        # Human-as-tiebreaker: the AI already gave an answer; the human reviews it
        # and either confirms, corrects, or escalates. No transaction is blocked.
        "hitl_model": "human-as-tiebreaker",
        "context_needed": (
            "The AI's response and its confidence score, the customer's dispute message, "
            "the official VinBank fee schedule and product documentation, "
            "and the customer's account type and history."
        ),
        "example": (
            "AI tells a customer the early withdrawal penalty for a 12-month savings "
            "account is 0.5%. Customer replies: 'The brochure says 0.2%.' "
            "The AI flags this as a dispute. A customer service agent reviews both the "
            "AI answer and the official document, then sends the verified correct answer."
        ),
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
