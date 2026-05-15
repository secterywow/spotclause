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


def _split_into_chunks(text: str, chunk_size: int = 12000, overlap: int = 600) -> List[str]:
    """Split long text into overlapping chunks at paragraph boundaries when possible."""
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Try to break at a paragraph boundary near the end of the window
        if end < len(text):
            window = text[start:end]
            break_pos = max(window.rfind('\n\n'), window.rfind('。\n'), window.rfind('. '))
            if break_pos > chunk_size * 0.6:
                end = start + break_pos + 1
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def structure_clauses(text: str) -> List[Dict]:
    """Structure contract into clauses using LLM. Processes the entire document via chunking."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    chunks = _split_into_chunks(text)

    system_prompt = """You are a contract clause extractor. Break down the contract into individual clauses.

Return a JSON array of clauses:
[
  {"id": "1", "title": "Confidentiality", "content": "full clause text", "category": "obligation"},
  ...
]

Categories: obligation, right, payment, termination, liability, dispute, general

Only return the JSON array — no prose, no markdown fences."""

    merged: List[Dict] = []
    seen_titles: set = set()

    for idx, chunk in enumerate(chunks):
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Contract text (part {idx + 1} of {len(chunks)}):\n\n{chunk}")
        ]
        try:
            response = llm.invoke(messages)
            content = response.content
            if isinstance(content, str):
                # Strip optional markdown fences
                content = content.strip()
                if content.startswith('```'):
                    content = content.split('```', 2)[1]
                    if content.startswith('json'):
                        content = content[4:]
                    content = content.rsplit('```', 1)[0].strip()
                clauses = json.loads(content)
            else:
                clauses = content

            if not isinstance(clauses, list):
                continue

            for c in clauses:
                title = (c.get('title') or '').strip().lower()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                merged.append(c)
        except Exception as e:
            logger.error("Clause structuring failed", error=str(e), chunk_index=idx)
            continue

    # Reassign sequential IDs
    for i, c in enumerate(merged, 1):
        c['id'] = str(i)

    return merged


def match_risk_rules(clauses: List[Dict], contract_type: str) -> Dict[str, List[Dict]]:
    """Match clauses against risk rules."""
    from app.database import SessionLocal
    from app.models.rule import RiskRule

    db = SessionLocal()
    try:
        # Fetch active rules then filter by contract_type in Python — the column is
        # JSON (not JSONB) so .contains() falls back to a LIKE that Postgres rejects.
        all_active = db.query(RiskRule).filter(RiskRule.is_active == True).all()
        rules = [r for r in all_active
                 if isinstance(r.contract_types, list) and contract_type in r.contract_types]

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


def _extract_json_block(content: str) -> str:
    """Strip optional markdown fences and isolate the JSON payload."""
    if not isinstance(content, str):
        return content
    s = content.strip()
    if s.startswith('```'):
        s = s.split('```', 2)[1]
        if s.startswith('json'):
            s = s[4:]
        s = s.rsplit('```', 1)[0].strip()
    # If the model wrapped JSON inside prose, slice from the first { to the last }
    first = s.find('{')
    last = s.rfind('}')
    if first != -1 and last != -1 and last > first:
        s = s[first:last + 1]
    return s


def analyze_contract_full(text: str, jurisdiction: str) -> Dict:
    """One-shot analysis: ship the entire contract to the LLM and get every field back.

    Returns a dict with: contractType, clauses (each with analysis fields), missingClauses, keyTerms.
    Raises on failure so the caller can fall back to the per-step pipeline.
    """
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    system_prompt = f"""You are an AI document assistant. Analyze the ENTIRE contract below and return ONE JSON object.

Return ONLY the JSON — no markdown fences, no prose before/after.

Schema (exact field names, exact shape):
{{
  "contractType": "nda|service|lease|employment|investment|partnership|sales|other",
  "clauses": [
    {{
      "id": "1",
      "title": "short clause name (≤ 40 chars)",
      "content": "verbatim or near-verbatim clause text from the contract",
      "category": "obligation|right|payment|termination|liability|dispute|general",
      "riskLevel": "high|medium|low",
      "explanation": "plain-language explanation anyone can follow (1-3 sentences)",
      "riskReason": "concrete reason WHY this clause deserves attention, citing relevant document standards or practices where applicable. Empty string if no concern.",
      "solution": "actionable suggested fix for the user. Empty string if no fix needed.",
      "negotiationScript": {{
        "yourOpening": "what the user should say to push back",
        "theirRebuttal": "the likely counter from the other side",
        "yourResponse": "how the user should respond to that counter"
      }}
    }}
  ],
  "missingClauses": [
    {{"id":"1","severity":"high|medium|low","title":"clause name","description":"why it matters","suggestedText":"sample wording to insert"}}
  ],
  "keyTerms": [
    {{"term":"legal/professional term","plainMeaning":"plain-language explanation"}}
  ],
  "keyDates": [
    {{"date":"YYYY-MM-DD","milestone":"short label for what this date is (e.g. 'Contract effective date', '首付款截止日', 'IP transfer deadline')"}}
  ]
}}

Hard rules — follow them literally to keep output STABLE across runs of the same contract:

1. CLAUSE EXTRACTION (deterministic order + granularity)
   - Walk the document strictly TOP-TO-BOTTOM. Emit clauses in the exact order they appear.
   - One clause object per discrete numbered section, lettered subsection, or titled paragraph that creates a right, obligation, condition, or definition.
   - DO NOT lump multiple sections together. DO NOT skip "boilerplate" — still emit it (with riskLevel="low" and empty riskReason/solution).
   - The "title" field MUST come from the section heading in the contract verbatim if one exists; otherwise pick the first noun phrase of the clause.

2. RISK RUBRIC (apply literally — these anchors define the levels)
   - "high"   = the clause materially shifts financial, IP, liability, termination, or remedy rights against the user, OR represents an unusual or non-standard practice in {jurisdiction}. Examples: uncapped indemnity, perpetual non-compete, unilateral price changes, waiver of important rights, blanket IP assignment with no carve-outs.
   - "medium" = the clause is one-sided, ambiguous, or below standard market practice but does not by itself create a catastrophic exposure. Examples: short cure periods, broad confidentiality with no time limit, vague acceptance criteria, counterparty-favorable jurisdiction without dispute-forum carve-out.
   - "low"    = the clause is market-standard, mutually balanced, purely definitional, or administrative boilerplate. ALSO use "low" for clauses you have no specific concern about.
   - When uncertain between two levels, pick the LOWER one.

3. SEVERITY FOR missingClauses
   - "high" only if the clause's absence creates a significant concern (e.g. missing IP ownership, missing limitation of liability in a service contract).
   - Otherwise "medium" or "low" per the same rubric.

4. FIXED COUNTS (to remove run-to-run variance on subjective inclusion calls)
   - keyTerms: include EXACTLY 10 entries. Pick the 10 most jargon-heavy terms in document order. If fewer than 10 jargon terms exist, pad with the next most useful defined terms.
   - missingClauses: include AT MOST 8 entries, ranked by severity then importance.

5. KEY DATES — every individual date that creates an obligation gets its own entry
   - Emit one entry per distinct date that creates an obligation, deadline, milestone, term start/end, payment due, notice period trigger, or other time-bound event.
   - If a single sentence mentions multiple dates (e.g. "首付款于 2026-05-15 支付,尾款于 2026-08-15 支付"), emit ONE entry per date.
   - "date" must be a real ISO date YYYY-MM-DD. If the contract gives a relative date ("30 days after signing"), and a signing date is fixed elsewhere, compute the absolute date. Otherwise OMIT that entry.
   - "milestone" is a short noun-phrase label (≤ 12 chars in Chinese / ≤ 30 chars in English) describing WHAT the date is, e.g. "签订日 / Effective date", "首付款 / First payment", "项目验收 / Acceptance milestone". DO NOT put the original sentence here.
   - Order keyDates chronologically (earliest first).
   - If no dates are present, return an empty array.

6. LANGUAGE
   - All human-readable fields (title, explanation, riskReason, solution, negotiationScript.*, description, suggestedText, plainMeaning, milestone) MUST be written in the SAME language as the contract body.

7. JURISDICTION
   - Assess every clause against the laws of jurisdiction code: {jurisdiction}.

8. OUTPUT FORMAT
   - Valid JSON. No trailing commas. No markdown fences. No commentary."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Contract jurisdiction: {jurisdiction}\n\nContract text:\n\n{text}"),
    ]

    # The output JSON can be large — many clauses × ~6 fields each. Lift the output cap
    # so the model can finish in one shot instead of getting truncated mid-array.
    try:
        big_llm = llm.bind(max_tokens=16000)
        response = big_llm.invoke(messages)
    except Exception:
        # If the underlying provider rejects max_tokens, fall back to the default config.
        response = llm.invoke(messages)
    raw = response.content
    payload = json.loads(_extract_json_block(raw))

    if not isinstance(payload, dict):
        raise ValueError("Mega-analysis response was not a JSON object")

    clauses = payload.get('clauses') or []
    if not isinstance(clauses, list) or not clauses:
        raise ValueError("Mega-analysis returned no clauses")

    # Reassign sequential string ids so the rest of the pipeline can rely on them
    for i, c in enumerate(clauses, 1):
        c['id'] = str(i)
        c.setdefault('title', f'Clause {i}')
        c.setdefault('content', '')
        c.setdefault('category', 'general')
        c.setdefault('riskLevel', 'low')
        c.setdefault('explanation', '')
        c.setdefault('riskReason', '')
        c.setdefault('solution', '')
        # The downstream assembler reads `legalBasis` — mirror riskReason into it so the
        # frontend (which renders this field as "风险原因 / Risk Reason") keeps working.
        c['legalBasis'] = c.get('riskReason', '') or c.get('legalBasis', '')
        ns = c.get('negotiationScript') or {}
        if not isinstance(ns, dict):
            ns = {}
        ns.setdefault('yourOpening', '')
        ns.setdefault('theirRebuttal', '')
        ns.setdefault('yourResponse', '')
        c['negotiationScript'] = ns

    missing = payload.get('missingClauses') or []
    if not isinstance(missing, list):
        missing = []
    for i, m in enumerate(missing, 1):
        m['id'] = str(i)
        m.setdefault('severity', 'medium')
        m.setdefault('title', '')
        m.setdefault('description', '')
        m.setdefault('suggestedText', '')

    key_terms = payload.get('keyTerms') or []
    if not isinstance(key_terms, list):
        key_terms = []
    key_terms = [
        {'term': t.get('term', ''), 'plainMeaning': t.get('plainMeaning', '')}
        for t in key_terms if isinstance(t, dict) and t.get('term')
    ]

    key_dates = _normalize_key_dates(payload.get('keyDates') or [])

    contract_type = payload.get('contractType', 'other')
    if contract_type not in {'nda', 'service', 'lease', 'employment',
                             'investment', 'partnership', 'sales', 'other'}:
        contract_type = 'other'

    return {
        'contractType': contract_type,
        'clauses': clauses,
        'missingClauses': missing,
        'keyTerms': key_terms,
        'keyDates': key_dates,
    }


def _normalize_key_dates(raw: List) -> List[Dict]:
    """Normalize LLM-returned key dates into {date, milestone, daysRemaining}.

    - Drops entries with malformed dates.
    - Computes daysRemaining against today's date.
    - Sorts chronologically.
    - Dedups by (date, milestone).
    """
    from datetime import datetime, date as date_cls

    today = datetime.now().date()
    out: List[Dict] = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        iso = str(item.get('date') or '').strip()
        if not re.fullmatch(r'\d{4}-\d{1,2}-\d{1,2}', iso):
            continue
        try:
            y, mo, d = iso.split('-')
            obj = date_cls(int(y), int(mo), int(d))
        except (ValueError, TypeError):
            continue
        iso_clean = obj.strftime('%Y-%m-%d')
        milestone = str(item.get('milestone') or '').strip()
        key = (iso_clean, milestone)
        if key in seen:
            continue
        seen.add(key)
        days = (obj - today).days if obj >= today else None
        out.append({
            'date': iso_clean,
            'milestone': milestone,
            'daysRemaining': days,
        })
    out.sort(key=lambda x: x['date'])
    return out


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
    """Extract key legal terms from contract. Processes the entire document via chunking."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    chunks = _split_into_chunks(text)

    system_prompt = """Extract key legal/professional terms from the contract and explain them in plain language.

Return a JSON array (no prose, no markdown fences):
[
  {"term": "term name", "plainMeaning": "simple explanation"},
  ...
]"""

    merged: List[Dict] = []
    seen_terms: set = set()

    for idx, chunk in enumerate(chunks):
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Contract text (part {idx + 1} of {len(chunks)}):\n\n{chunk}")
        ]
        try:
            response = llm.invoke(messages)
            content = response.content
            if isinstance(content, str):
                content = content.strip()
                if content.startswith('```'):
                    content = content.split('```', 2)[1]
                    if content.startswith('json'):
                        content = content[4:]
                    content = content.rsplit('```', 1)[0].strip()
                terms = json.loads(content)
            else:
                terms = content

            if not isinstance(terms, list):
                continue

            for t in terms:
                term = (t.get('term') or '').strip()
                key = term.lower()
                if not term or key in seen_terms:
                    continue
                seen_terms.add(key)
                merged.append(t)
        except Exception as e:
            logger.error("Key term extraction failed", error=str(e), chunk_index=idx)
            continue

    return merged


def extract_dates(text: str) -> List[Dict]:
    """Regex-based date extraction — fallback when the LLM mega-call produced no keyDates.

    Output shape matches the LLM path: {date, milestone, daysRemaining}. We have no
    semantic milestone label here (regex can't infer that), so milestone is left empty
    and the frontend renders a placeholder.

    Two layers:
      1. Numeric formats (ISO, slash, CJK 年月日) — we capture y/m/d directly and
         build the date with `datetime(y, m, d)`. dateutil can't parse CJK tokens
         and silently dies inside `except Exception`, which is why Chinese
         contracts came back with zero dates.
      2. English month-name formats (e.g. "May 12, 2026") — still dateutil.

    `\\b` is intentionally avoided around digit groups: in Python regex `\\b`
    only fires at ASCII-word-character boundaries, so something like
    "2026-05-12到2027-05-12" yields zero hits because both ends are Chinese.
    `(?<!\\d)` / `(?!\\d)` work regardless of surrounding script.
    """
    import dateutil.parser as parser
    from datetime import datetime, date

    today = datetime.now().date()
    dates: List[Dict] = []
    seen_keys = set()  # dedup by iso string

    def _emit(date_obj: date):
        iso = date_obj.strftime("%Y-%m-%d")
        if iso in seen_keys:
            return
        seen_keys.add(iso)
        days_remaining = (date_obj - today).days if date_obj >= today else None
        dates.append({
            "date": iso,
            "milestone": "",
            "daysRemaining": days_remaining,
        })

    # --- Numeric patterns with captured year/month/day ---
    numeric_patterns = [
        # 2026年5月15日 — Chinese
        re.compile(r'(?<!\d)(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日'),
        # 2026年5月15號 / 號 (Traditional)
        re.compile(r'(?<!\d)(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})號'),
        # 2026/05/15 or 2026-05-15 (ISO-ish, 4-digit year first)
        re.compile(r'(?<!\d)(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?!\d)'),
    ]
    for pat in numeric_patterns:
        for m in pat.finditer(text):
            try:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                obj = date(y, mo, d)
            except (ValueError, TypeError):
                continue
            _emit(obj)

    # Day-first or month-first 2-digit-year style: 12/31/26, 31-12-2026 etc.
    # Ambiguous so try multiple interpretations and pick the first that parses.
    for m in re.finditer(r'(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})(?!\d)', text):
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if c < 100:
            c += 2000  # 26 → 2026
        # Try month/day/year first (US default), then day/month/year fallback.
        for y_, mo_, d_ in [(c, a, b), (c, b, a)]:
            try:
                obj = date(y_, mo_, d_)
                _emit(obj)
                break
            except (ValueError, TypeError):
                continue

    # --- English month-name patterns (still need dateutil for ordinals/commas) ---
    english_patterns = [
        # 1 January 2026 / 1st January 2026 / 1st of January 2026 / 1st day of January 2026
        re.compile(r'(?<!\w)(\d{1,2}(?:st|nd|rd|th)?\s+(?:(?:day\s+)?of\s+)?'
                   r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
                   r'[\s,]+\d{4})(?!\w)', re.IGNORECASE),
        # January 1st, 2026 / January 1 2026
        re.compile(r'(?<!\w)((?:January|February|March|April|May|June|July|August|September|October|November|December)'
                   r'\s+\d{1,2}(?:st|nd|rd|th)?[\s,]+\d{4})(?!\w)', re.IGNORECASE),
    ]
    for pat in english_patterns:
        for m in pat.finditer(text):
            raw = m.group(1)
            cleaned = re.sub(r'(?<=\d)(st|nd|rd|th)\b', '', raw, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s+day\s+of\s+', ' ', cleaned, flags=re.IGNORECASE)
            try:
                parsed = parser.parse(cleaned, fuzzy=False, dayfirst=False).date()
            except Exception:
                continue
            _emit(parsed)

    dates.sort(key=lambda d: d['date'])
    return dates[:20]


_STRUCTURE_SYSTEM_PROMPT = """You are an AI document assistant. Your only job here is to STRUCTURE the contract — list every distinct clause, top to bottom — and identify the contract type.

Return ONLY a JSON object (no markdown fences, no prose).

Schema:
{
  "contractType": "nda|service|lease|employment|investment|partnership|sales|other",
  "clauses": [
    {
      "id": "1",
      "title": "short clause name (≤ 40 chars), verbatim from the section heading if one exists",
      "content": "verbatim or near-verbatim clause text",
      "category": "obligation|right|payment|termination|liability|dispute|general"
    }
  ]
}

Hard rules:
1. Walk the document strictly TOP-TO-BOTTOM. Emit clauses in document order.
2. One clause per discrete numbered section, lettered subsection, or titled paragraph that creates a right, obligation, condition, or definition. DO NOT merge sections.
3. DO NOT skip "boilerplate" — still emit it (with category="general").
4. The "title" field MUST come from the section heading in the contract verbatim if one exists; otherwise pick the first noun phrase of the clause.
5. "title" and any human-readable text MUST be in the SAME language as the contract body.
6. Output valid JSON. No trailing commas. No commentary."""


def extract_structure_pass(text: str, jurisdiction: str) -> Dict:
    """Phase 1: structure pass. One LLM round-trip returns contractType + clauses skeleton.

    Returns:
        {"contractType": "...", "clauses": [{id, title, content, category}, ...]}
    """
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    messages = [
        SystemMessage(content=_STRUCTURE_SYSTEM_PROMPT),
        HumanMessage(content=f"Contract jurisdiction: {jurisdiction}\n\nContract text:\n\n{text}"),
    ]
    try:
        big_llm = llm.bind(max_tokens=12000)
        response = big_llm.invoke(messages)
    except Exception:
        response = llm.invoke(messages)
    payload = json.loads(_extract_json_block(response.content))
    if not isinstance(payload, dict):
        raise ValueError("Structure pass returned non-object")

    contract_type = payload.get('contractType', 'other')
    if contract_type not in {'nda', 'service', 'lease', 'employment',
                             'investment', 'partnership', 'sales', 'other'}:
        contract_type = 'other'

    raw_clauses = payload.get('clauses') or []
    if not isinstance(raw_clauses, list) or not raw_clauses:
        raise ValueError("Structure pass returned no clauses")

    clauses: List[Dict] = []
    for i, c in enumerate(raw_clauses, 1):
        if not isinstance(c, dict):
            continue
        clauses.append({
            'id': str(i),
            'title': str(c.get('title') or f'Clause {i}'),
            'content': str(c.get('content') or ''),
            'category': str(c.get('category') or 'general'),
        })

    return {'contractType': contract_type, 'clauses': clauses}


_RISK_SYSTEM_PROMPT_TEMPLATE = """You are an AI document assistant analyzing ONE clause from a {contract_type} contract under {jurisdiction} law.

Return ONLY a JSON object (no markdown fences, no prose, no extra fields).

Schema:
{{
  "riskLevel": "high|medium|low",
  "explanation": "plain-language explanation anyone can follow (1-3 sentences)",
  "riskReason": "concrete reason WHY this clause deserves attention, citing relevant document standards or practices. Empty string if not noteworthy.",
  "solution": "actionable suggested fix. Empty string if no fix needed.",
  "negotiationScript": {{
    "yourOpening": "what the user should say to push back",
    "theirRebuttal": "the likely counter from the other side",
    "yourResponse": "how the user should respond"
  }}
}}

Risk rubric (apply literally):
- "high"   = materially shifts financial / IP / liability / termination / remedy rights AGAINST the user, OR represents an unusual or non-standard practice in {jurisdiction}.
- "medium" = one-sided, ambiguous, or below standard market practice but not catastrophic.
- "low"    = market-standard, mutually balanced, definitional, or administrative boilerplate. ALSO use "low" if you have no specific complaint.
- When uncertain between two levels, pick the LOWER one.

All human-readable fields MUST be in the SAME language as the clause text below."""


def analyze_single_clause(clause: Dict, contract_type: str, jurisdiction: str) -> Dict:
    """Phase 2 worker: analyze a single clause for risk under {jurisdiction} law.

    Returns the risk-related fields only (riskLevel, explanation, riskReason,
    solution, negotiationScript) — the structural fields (id, title, content,
    category) belong to the caller's clause dict.
    """
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    system_prompt = _RISK_SYSTEM_PROMPT_TEMPLATE.format(
        contract_type=contract_type or 'other',
        jurisdiction=jurisdiction or 'US',
    )
    user_content = (
        f"Clause title: {clause.get('title', '')}\n"
        f"Clause category: {clause.get('category', 'general')}\n\n"
        f"Clause text:\n{clause.get('content', '')}"
    )
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]

    try:
        response = llm.invoke(messages)
        data = json.loads(_extract_json_block(response.content))
        if not isinstance(data, dict):
            raise ValueError("non-object")
    except Exception as e:
        logger.warning("Per-clause risk analysis failed; using neutral fallback",
                       error=str(e), clause_id=clause.get('id'))
        data = {}

    ns = data.get('negotiationScript') or {}
    if not isinstance(ns, dict):
        ns = {}
    return {
        'riskLevel': data.get('riskLevel') if data.get('riskLevel') in {'high', 'medium', 'low'} else 'low',
        'explanation': str(data.get('explanation') or ''),
        'riskReason': str(data.get('riskReason') or ''),
        'solution': str(data.get('solution') or ''),
        'negotiationScript': {
            'yourOpening': str(ns.get('yourOpening') or ''),
            'theirRebuttal': str(ns.get('theirRebuttal') or ''),
            'yourResponse': str(ns.get('yourResponse') or ''),
        },
    }


_SIDE_INFO_SYSTEM_PROMPT = """You are an AI document assistant reviewing a {contract_type} contract under {jurisdiction} law.

Given the contract text below and the list of clause titles already identified, produce three side-channel outputs:
  • missingClauses — clauses that SHOULD be present but are absent (max 8)
  • keyTerms — exactly 10 jargon-heavy or load-bearing defined terms
  • keyDates — every distinct date that creates an obligation, deadline, or milestone

Return ONLY a JSON object (no fences, no prose):
{{
  "missingClauses": [
    {{"id":"1","severity":"high|medium|low","title":"clause name","description":"why it matters","suggestedText":"sample wording"}}
  ],
  "keyTerms": [
    {{"term":"legal/professional term","plainMeaning":"plain-language explanation"}}
  ],
  "keyDates": [
    {{"date":"YYYY-MM-DD","milestone":"short label (≤ 12 CN chars / ≤ 30 EN chars)"}}
  ]
}}

Hard rules:
- missingClauses: AT MOST 8, ranked by severity then importance under {jurisdiction}. "high" only if the absence creates a significant concern.
- keyTerms: EXACTLY 10. Pick the most jargon-heavy / defined terms in document order. If fewer than 10 exist, pad with the next most useful defined terms.
- keyDates: one entry per distinct date. ISO YYYY-MM-DD. If the contract gives a relative date and a signing date is fixed elsewhere, compute the absolute date; otherwise omit. Chronological order. If a single sentence mentions multiple dates, emit one entry per date.
- All human-readable fields in the SAME language as the contract body.
- Valid JSON. No trailing commas."""


def extract_side_info(text: str, contract_type: str, jurisdiction: str,
                       clause_titles: List[str]) -> Dict:
    """Phase 2 worker: get missing clauses, key terms, key dates in one round-trip."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    system_prompt = _SIDE_INFO_SYSTEM_PROMPT.format(
        contract_type=contract_type or 'other',
        jurisdiction=jurisdiction or 'US',
    )
    titles_str = " | ".join(t for t in clause_titles if t) or "(none yet)"
    user_content = (
        f"Existing clause titles: {titles_str}\n\n"
        f"Contract text:\n\n{text}"
    )
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]

    try:
        big_llm = llm.bind(max_tokens=6000)
        response = big_llm.invoke(messages)
    except Exception:
        response = llm.invoke(messages)

    try:
        payload = json.loads(_extract_json_block(response.content))
    except Exception as e:
        logger.warning("Side-info pass failed; returning empty side info", error=str(e))
        return {'missingClauses': [], 'keyTerms': [], 'keyDates': []}

    if not isinstance(payload, dict):
        return {'missingClauses': [], 'keyTerms': [], 'keyDates': []}

    missing = payload.get('missingClauses') or []
    if not isinstance(missing, list):
        missing = []
    out_missing: List[Dict] = []
    for i, m in enumerate(missing, 1):
        if not isinstance(m, dict):
            continue
        out_missing.append({
            'id': str(i),
            'severity': m.get('severity') if m.get('severity') in {'high', 'medium', 'low'} else 'medium',
            'title': str(m.get('title') or ''),
            'description': str(m.get('description') or ''),
            'suggestedText': str(m.get('suggestedText') or ''),
        })

    key_terms = payload.get('keyTerms') or []
    if not isinstance(key_terms, list):
        key_terms = []
    out_terms = [
        {'term': str(t.get('term', '')), 'plainMeaning': str(t.get('plainMeaning', ''))}
        for t in key_terms if isinstance(t, dict) and t.get('term')
    ]

    out_dates = _normalize_key_dates(payload.get('keyDates') or [])

    return {
        'missingClauses': out_missing,
        'keyTerms': out_terms,
        'keyDates': out_dates,
    }


def assemble_report(contract_type: str, jurisdiction: str,
                   clauses: List[Dict], analysis_results: List[Dict],
                   missing_clauses: List[Dict], key_terms: List[Dict],
                   key_dates: List[Dict]) -> Dict:
    """Assemble final analysis report."""
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

    # Risky clauses — sorted high → medium → low. We append in document order
    # then stable-sort, so within a severity tier the natural top-to-bottom
    # order is preserved.
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
                "legalBasis": analysis.get('legalBasis') or analysis.get('riskReason') or '',
                "solution": analysis.get('solution'),
                "negotiationScript": analysis.get('negotiationScript', {}),
            })
    _SEVERITY_RANK = {'high': 0, 'medium': 1, 'low': 2}
    risky_clauses.sort(key=lambda r: _SEVERITY_RANK.get(r.get('severity'), 99))

    return {
        "contractType": contract_type,
        "jurisdiction": jurisdiction,
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
