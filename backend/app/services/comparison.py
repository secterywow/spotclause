import json
import re
from typing import List, Dict, Set, Tuple
from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Common Chinese legal stop-words that appear in almost every contract.
_CHINESE_STOP_WORDS = set(
    "的之一是在了和与为甲方乙方合同协议双方约定条款签署"
    "本日年月日期限届满终止解除违约赔偿责任"
    "人民币元整佰仟万拾付款支付"
)


def _clean_text(text: str) -> str:
    """Remove punctuation, whitespace, and common stop-words."""
    # Keep CJK unified ideographs + alphanumeric
    cleaned = re.sub(r"[^一-鿿\w]", "", text)
    # Strip common stop-words (each character)
    return "".join(ch for ch in cleaned if ch not in _CHINESE_STOP_WORDS)


def _ngrams(text: str, n: int = 3) -> Set[str]:
    """Return a set of n-grams from the text."""
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _text_similarity(a: str, b: str) -> float:
    """Jaccard similarity over 3-grams after cleaning.

    SequenceMatcher (char-level LCS) inflates similarity for Chinese
    because unrelated contracts share many common characters.
    Jaccard on cleaned 3-grams avoids that false signal.
    """
    ca = _clean_text(a)
    cb = _clean_text(b)

    if not ca or not cb:
        return 0.0

    ga = _ngrams(ca, 3)
    gb = _ngrams(cb, 3)

    if not ga or not gb:
        return 0.0

    intersection = ga & gb
    union = ga | gb
    return len(intersection) / len(union)


def check_contract_relatedness(
    old_text: str, new_text: str, threshold: float = 0.20
) -> Tuple[bool, float]:
    """Check whether two texts are likely versions of the same contract.

    Returns (is_related, similarity).
    """
    similarity = _text_similarity(old_text, new_text)
    is_related = similarity >= threshold
    logger.info(
        "Contract similarity check",
        similarity=round(similarity, 4),
        threshold=threshold,
        is_related=is_related,
        old_len=len(old_text),
        new_len=len(new_text),
    )
    return is_related, similarity


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
]

IMPORTANT: All textual VALUES (location, oldText, newText) must be in the SAME LANGUAGE as the contract text. If the contract is in Chinese, write location names in Chinese. JSON keys stay English."""

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
}

IMPORTANT: Write the `analysis` field in the SAME LANGUAGE as the change text below. If the change text is Chinese, write the analysis in Chinese. The `riskChange` enum value stays English."""

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
] or [] if no traps found.

IMPORTANT: All textual values (location, description, oldWording, newWording) must be in the SAME LANGUAGE as the contract text. If the changes are in Chinese, respond in Chinese. JSON keys stay English."""

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

    # Structured counts so the frontend can render a localized summary
    # sentence; the `summary` string is kept as an English fallback.
    breakdown = {
        "changes": len(changes),
        "improved": improved,
        "worsened": worsened,
        "unchanged": unchanged,
        "new": new_items,
        "traps": len(hidden_traps),
    }
    summary = (
        f"Found {breakdown['changes']} changes: {improved} improved, "
        f"{worsened} worsened, {unchanged} unchanged, {new_items} new. "
        f"{len(hidden_traps)} hidden traps detected."
    )

    return {
        "summary": summary,
        "breakdown": breakdown,
        "overallRiskChange": overall,
        "changes": changes,
        "hiddenTraps": hidden_traps,
    }
