import re
import json
from typing import List, Dict
from app.config import get_settings
from app.logger import get_logger
from app.services.file_parser import parse_file_sync

settings = get_settings()
logger = get_logger(__name__)


def detect_jurisdiction(text: str) -> str:
    """Detect contract jurisdiction from text."""
    text_lower = text.lower()

    # Language indicators
    chinese_chars = len(re.findall(r'[一-鿿]', text))
    if chinese_chars > 100:
        return "CN"

    # Currency indicators
    if '$' in text or 'usd' in text_lower or 'dollar' in text_lower:
        return "US"

    if '€' in text_lower or 'eur' in text_lower or 'euro' in text_lower:
        return "EU"

    if '£' in text or 'gbp' in text_lower or 'pound' in text_lower:
        return "GB"

    if '¥' in text or 'jpy' in text_lower or 'yen' in text_lower:
        return "JP"

    # Jurisdiction keywords
    if 'governing law' in text_lower or 'jurisdiction' in text_lower:
        if 'california' in text_lower or 'new york' in text_lower or 'delaware' in text_lower:
            return "US"
        if 'england' in text_lower or 'wales' in text_lower:
            return "GB"
        if 'germany' in text_lower or 'bundesrepublik' in text_lower:
            return "DE"

    return "US"  # Default


def identify_contract_type(text: str) -> str:
    """Identify contract type using LLM."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    preview = text[:3000]

    system_prompt = """You are a contract type classifier. Analyze the contract and return ONLY a JSON object with the type field.

Possible types: nda, service, lease, employment, investment, partnership, sales, other

Response format: {"type": "service"}"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Contract text (first 3000 chars):\n\n{preview}")
    ]

    try:
        response = llm.invoke(messages)
        result = json.loads(response.content)
        return result.get('type', 'other')
    except Exception as e:
        logger.error("Contract type identification failed", error=str(e))
        return "other"


def structure_clauses(text: str) -> List[Dict]:
    """Structure contract into clauses using LLM."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    # Truncate if too long
    truncated = text[:8000]

    system_prompt = """You are a contract clause extractor. Break down the contract into individual clauses.

Return a JSON array of clauses:
[
  {"id": "1", "title": "Confidentiality", "content": "full clause text", "category": "obligation"},
  ...
]

Categories: obligation, right, payment, termination, liability, dispute, general"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Contract text:\n\n{truncated}")
    ]

    try:
        response = llm.invoke(messages)
        clauses = json.loads(response.content)
        if isinstance(clauses, list):
            return clauses
        return []
    except Exception as e:
        logger.error("Clause structuring failed", error=str(e))
        return []


def match_risk_rules(clauses: List[Dict], contract_type: str) -> Dict[str, List[Dict]]:
    """Match clauses against risk rules."""
    from app.database import SessionLocal
    from app.models.rule import RiskRule

    db = SessionLocal()
    try:
        rules = db.query(RiskRule).filter(
            RiskRule.is_active == True,
            RiskRule.contract_types.contains([contract_type])
        ).all()

        matched = {}
        for clause in clauses:
            clause_text = clause.get('content', '').lower()
            clause_matches = []
            for rule in rules:
                keywords = rule.keywords or []
                if any(kw.lower() in clause_text for kw in keywords):
                    clause_matches.append({
                        'rule_id': rule.rule_id,
                        'title': rule.title,
                        'description': rule.description,
                        'severity': rule.severity,
                        'standard_practice': rule.standard_practice,
                        'suggested_alternative': rule.suggested_alternative,
                        'legal_basis': rule.legal_basis,
                    })
            matched[clause['id']] = clause_matches

        return matched
    finally:
        db.close()


def analyze_clause(clause: Dict, rules: List[Dict], jurisdiction: str) -> Dict:
    """Analyze a single clause for risks using LLM."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    rules_text = "\n\n".join([
        f"Rule {i+1}: {r['title']} (Severity: {r['severity']})\n{r['description']}"
        for i, r in enumerate(rules[:3])  # Limit to top 3 rules
    ]) if rules else "No specific rules matched."

    system_prompt = f"""You are a contract risk analyst. Analyze the clause for potential risks.
Jurisdiction: {jurisdiction}

Return a JSON object:
{{
  "riskLevel": "high|medium|low",
  "explanation": "plain language explanation",
  "legalBasis": "relevant law",
  "solution": "suggested fix",
  "negotiationScript": {{
    "yourOpening": "what to say",
    "theirRebuttal": "likely counter",
    "yourResponse": "how to respond"
  }},
  "fairnessScore": 0-100
}}"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Clause: {clause['title']}\n\nContent: {clause['content']}\n\nMatched Rules:\n{rules_text}")
    ]

    try:
        response = llm.invoke(messages)
        return json.loads(response.content)
    except Exception as e:
        logger.error("Clause analysis failed", error=str(e), clause_id=clause.get('id'))
        return {
            "riskLevel": "low",
            "explanation": "Could not analyze this clause.",
            "legalBasis": "",
            "solution": "",
            "negotiationScript": {"yourOpening": "", "theirRebuttal": "", "yourResponse": ""},
            "fairnessScore": 50,
        }


def detect_missing_clauses(contract_type: str, existing_clauses: List[Dict]) -> List[Dict]:
    """Detect missing clauses based on contract type."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    existing_titles = [c.get('title', '') for c in existing_clauses]

    system_prompt = """You are a contract completeness checker. Identify important clauses that should be present but are missing.

Return a JSON array:
[
  {"id": "1", "severity": "high|medium|low", "title": "clause name", "description": "why it's important", "suggestedText": "sample text"},
  ...
]"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Contract type: {contract_type}\n\nExisting clauses: {', '.join(existing_titles)}")
    ]

    try:
        response = llm.invoke(messages)
        return json.loads(response.content)
    except Exception as e:
        logger.error("Missing clause detection failed", error=str(e))
        return []


def extract_key_terms(text: str) -> List[Dict]:
    """Extract key legal terms from contract."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    system_prompt = """Extract key legal/professional terms from the contract and explain them in plain language.

Return a JSON array:
[
  {"term": "term name", "plainMeaning": "simple explanation"},
  ...
]"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=text[:5000])
    ]

    try:
        response = llm.invoke(messages)
        return json.loads(response.content)
    except Exception as e:
        logger.error("Key term extraction failed", error=str(e))
        return []


def extract_dates(text: str) -> List[Dict]:
    """Extract dates from contract text using regex."""
    import dateutil.parser as parser
    from datetime import datetime

    # Date patterns
    patterns = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        r'\b(\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})\b',
        r'\b\d{4}年\d{1,2}月\d{1,2}日\b',
    ]

    dates = []
    seen = set()

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_str = match.group(1) if match.groups() else match.group(0)
            if date_str in seen:
                continue
            seen.add(date_str)

            try:
                parsed = parser.parse(date_str)
                days_remaining = None
                if parsed.date() > datetime.now().date():
                    days_remaining = (parsed.date() - datetime.now().date()).days

                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()

                dates.append({
                    "description": context,
                    "originalText": date_str,
                    "date": parsed.strftime("%Y-%m-%d"),
                    "daysRemaining": days_remaining,
                })
            except:
                continue

    return dates[:20]  # Limit to 20 dates


def assemble_report(contract_type: str, jurisdiction: str,
                   clauses: List[Dict], analysis_results: List[Dict],
                   missing_clauses: List[Dict], key_terms: List[Dict],
                   key_dates: List[Dict]) -> Dict:
    """Assemble final analysis report."""
    # Calculate overall score
    fairness_scores = [r.get('fairnessScore', 50) for r in analysis_results if 'fairnessScore' in r]
    overall_score = round(sum(fairness_scores) / len(fairness_scores)) if fairness_scores else 50

    # Risk breakdown
    high_risk = sum(1 for r in analysis_results if r.get('riskLevel') == 'high')
    medium_risk = sum(1 for r in analysis_results if r.get('riskLevel') == 'medium')
    low_risk = sum(1 for r in analysis_results if r.get('riskLevel') == 'low')

    # Summary
    total = high_risk + medium_risk + low_risk
    if high_risk > 0:
        summary = f"Found {high_risk} high-risk, {medium_risk} medium-risk, and {low_risk} low-risk clauses out of {total} total clauses analyzed."
    elif medium_risk > 0:
        summary = f"Found {medium_risk} medium-risk and {low_risk} low-risk clauses. No high-risk issues detected."
    else:
        summary = f"Found {low_risk} low-risk items. The contract appears relatively safe."

    # Risky clauses
    risky_clauses = []
    for clause, analysis in zip(clauses, analysis_results):
        if analysis.get('riskLevel') in ['high', 'medium']:
            risky_clauses.append({
                "id": clause.get('id'),
                "severity": analysis.get('riskLevel'),
                "clauseTitle": clause.get('title'),
                "location": f"Clause {clause.get('id')}",
                "originalText": clause.get('content', '')[:500],
                "plainExplanation": analysis.get('explanation'),
                "legalBasis": analysis.get('legalBasis'),
                "solution": analysis.get('solution'),
                "negotiationScript": analysis.get('negotiationScript', {}),
            })

    return {
        "contractType": contract_type,
        "jurisdiction": jurisdiction,
        "overallScore": overall_score,
        "summary": summary,
        "riskBreakdown": {
            "high": high_risk,
            "medium": medium_risk,
            "low": low_risk,
        },
        "riskyClauses": risky_clauses,
        "missingClauses": missing_clauses,
        "keyTerms": key_terms,
        "keyDates": key_dates,
    }
