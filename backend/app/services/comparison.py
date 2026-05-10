import json
from typing import List, Dict
from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


def align_differences(old_text: str, new_text: str) -> List[Dict]:
    """Align and identify differences between two contract texts."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    system_prompt = """Compare two versions of a contract and identify all differences.

Return a JSON array of changes:
[
  {
    "id": "1",
    "location": "section name or clause number",
    "changeType": "modified|added|removed",
    "oldText": "original text (if modified/removed)",
    "newText": "new text (if modified/added)"
  },
  ...
]"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"OLD VERSION:\n\n{old_text[:5000]}\n\nNEW VERSION:\n\n{new_text[:5000]}")
    ]

    try:
        response = llm.invoke(messages)
        return json.loads(response.content)
    except Exception as e:
        logger.error("Difference alignment failed", error=str(e))
        return []


def analyze_change_risk(change: Dict) -> Dict:
    """Analyze the risk impact of a single change."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    system_prompt = """Analyze how a contract change affects risk. Determine if it improves, worsens, or is neutral.

Return a JSON object:
{
  "riskChange": "improved|worsened|unchanged|new",
  "analysis": "detailed explanation of the risk impact"
}"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Change location: {change.get('location')}\nType: {change.get('changeType')}\nOld: {change.get('oldText', 'N/A')}\nNew: {change.get('newText', 'N/A')}")
    ]

    try:
        response = llm.invoke(messages)
        return json.loads(response.content)
    except Exception as e:
        logger.error("Change risk analysis failed", error=str(e))
        return {"riskChange": "unchanged", "analysis": "Could not analyze this change."}


def detect_hidden_traps(changes: List[Dict]) -> List[Dict]:
    """Detect hidden traps - changes that appear different but are functionally the same."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    changes_summary = "\n\n".join([
        f"{i+1}. {c.get('location')}: {c.get('changeType')} - {c.get('oldText', 'N/A')[:200]} -> {c.get('newText', 'N/A')[:200]}"
        for i, c in enumerate(changes[:10])  # Limit to first 10
    ])

    system_prompt = """Analyze contract changes for "hidden traps" - changes that appear to modify terms but actually maintain the same legal effect (word games).

Return a JSON array:
[
  {
    "location": "where the trap is",
    "description": "explanation of the word game",
    "oldWording": "original wording",
    "newWording": "new wording"
  },
  ...
] or [] if no traps found."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Changes:\n\n{changes_summary}")
    ]

    try:
        response = llm.invoke(messages)
        return json.loads(response.content)
    except Exception as e:
        logger.error("Hidden trap detection failed", error=str(e))
        return []


def assemble_compare_report(changes: List[Dict], hidden_traps: List[Dict]) -> Dict:
    """Assemble final comparison report."""
    improved = sum(1 for c in changes if c.get('riskChange') == 'improved')
    worsened = sum(1 for c in changes if c.get('riskChange') == 'worsened')
    unchanged = sum(1 for c in changes if c.get('riskChange') == 'unchanged')
    new_items = sum(1 for c in changes if c.get('riskChange') == 'new')

    if worsened > improved:
        overall = "worsened"
    elif improved > worsened:
        overall = "improved"
    else:
        overall = "mixed"

    summary = f"Found {len(changes)} changes: {improved} improved, {worsened} worsened, {unchanged} unchanged, {new_items} new. {len(hidden_traps)} hidden traps detected."

    return {
        "summary": summary,
        "overallRiskChange": overall,
        "changes": changes,
        "hiddenTraps": hidden_traps,
    }
