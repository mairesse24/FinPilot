"""Presentation only: format selected, verified statements without changing facts."""
import re

SECTIONS = {
    "get_accounts_summary": "Your finances",
    "get_health_score": "Health score",
    "get_forecast": "Forecast",
    "get_guardian_alerts": "Risk",
    "run_simulation": "Scenario comparison",
}
FINANCIAL_NUMBER = re.compile(
    r"\$-?\d[\d,]*(?:\.\d+)?|\b\d+(?:\.\d+)?(?:%|/100)|\b\d+(?:\.\d+)?(?= out of 100)"
)


def emphasize(text: str) -> str:
    return FINANCIAL_NUMBER.sub(lambda match: f"**{match.group()}**", text)


def format_reply(selected: list[tuple[str, str]], next_step: str, note: str) -> str:
    groups: dict[str, list[str]] = {}
    actions: list[str] = []
    for section, fact in selected:
        # The marker comes from the server's Guardian evidence renderer.
        body, marker, action = fact.partition("Action to explore: ")
        if marker and action.strip():
            actions.append(action.strip())
        # Break complete sentences into readable bullets without splitting decimals.
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", body.strip())
        groups.setdefault(section, []).extend(sentence for sentence in sentences if sentence)
    blocks = [f"### {section}\n\n" + "\n".join(f"- {emphasize(fact)}" for fact in dict.fromkeys(facts))
              for section, facts in groups.items() if facts]
    if actions or next_step:
        block = "### Actions to explore"
        if actions:
            block += "\n\n" + "\n".join(f"- {emphasize(action)}" for action in dict.fromkeys(actions))
        if next_step:
            block += "\n\n" + next_step
        blocks.append(block)
    blocks.append(note)
    return "\n\n".join(blocks)
