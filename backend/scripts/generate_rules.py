"""
Generate ~300 risk rules using the configured LLM (LLM_MODEL via LLM_API_BASE)
and insert them into the risk_rules table.

Usage:
    cd backend
    python -m scripts.generate_rules            # generate + insert
    python -m scripts.generate_rules --dry-run  # generate only, print first 5
    python -m scripts.generate_rules --reset    # delete existing rows first
"""
from __future__ import annotations

import argparse
import functools
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from sqlalchemy import delete

from app.database import SessionLocal
from app.models.rule import RiskRule

print = functools.partial(print, flush=True)  # type: ignore
_lock = threading.Lock()


# Distribution: 300 rules across 8 contract types.
PLAN: List[Dict] = [
    {"contract_type": "nda",         "count": 40, "language_hint": "中文为主，英文关键词兼容"},
    {"contract_type": "service",     "count": 50, "language_hint": "中文为主，英文关键词兼容"},
    {"contract_type": "lease",       "count": 40, "language_hint": "中文为主，英文关键词兼容"},
    {"contract_type": "employment",  "count": 40, "language_hint": "中文为主，英文关键词兼容"},
    {"contract_type": "investment",  "count": 35, "language_hint": "中文为主，英文关键词兼容"},
    {"contract_type": "partnership", "count": 35, "language_hint": "中文为主，英文关键词兼容"},
    {"contract_type": "sales",       "count": 35, "language_hint": "中文为主，英文关键词兼容"},
    {"contract_type": "other",       "count": 25, "language_hint": "通用合同条款，覆盖多种合同类型"},
]

BATCH_SIZE = 20  # rules per LLM call (larger = fewer round-trips)
MAX_WORKERS = 4  # parallel contract-type generation


SYSTEM_PROMPT = """You are a senior commercial-contract lawyer producing a structured risk-rule library used by an AI contract-review system.

Each rule describes a SPECIFIC clause-level risk that frequently appears in real contracts. The reviewer will match user contracts against these rules to flag problems.

Return ONLY a JSON array. No prose, no markdown fences, no commentary. Each element must follow this exact schema:

{
  "rule_id": "<slug like nda-payment-001 — globally unique, kebab-case, ≤50 chars>",
  "contract_types": ["nda" | "service" | "lease" | "employment" | "investment" | "partnership" | "sales" | "other"],
  "category": "<short Chinese phrase, e.g. 保密范围, 付款条款, 违约责任>",
  "title": "<≤80 chars Chinese title describing the risk, e.g. 单方面变更条款无通知>",
  "description": "<2-3 Chinese sentences explaining what the risky clause looks like and why it's risky>",
  "standard_practice": "<2-3 Chinese sentences describing what a fair / standard version of this clause should look like>",
  "suggested_alternative": "<a concrete Chinese clause draft the user can use instead, written as if pasted into the contract>",
  "legal_basis": "<≤400 chars Chinese description of relevant law / principle, ideally citing a statute or commonly accepted commercial principle>",
  "severity": "high" | "medium" | "low",
  "keywords": ["3-8 keywords (mix Chinese and English) that the matcher can substring-search against clause text"]
}

Rules:
- Do not duplicate risks already covered.
- Use realistic legal references (e.g. 《中华人民共和国民法典》, 《合同法》, 《劳动合同法》, common-law concepts).
- keywords MUST be unique per rule, lowercase where alphabetic, short (1-4 tokens each), and chosen so a substring match in a clause body actually fires for this risk.
- severity should reflect how harmful the clause is to the weaker party.
- rule_id must include the contract-type prefix.
"""


USER_PROMPT_TEMPLATE = """Generate {batch} brand-new risk rules for contract type "{contract_type}".

Already-used rule_ids (avoid duplicates and avoid overlapping risks): {existing_ids}

Already-used Chinese titles (avoid duplicates / near-duplicates): {existing_titles}

Constraints:
- All {batch} rules MUST be distinct from each other and from the ones above.
- Cover diverse aspects: scope, duration, payment, IP, liability, termination, dispute resolution, governing law, indemnity, force majeure, data, confidentiality, non-compete, change control, audit, warranty, etc. — whatever is most relevant to {contract_type}.
- {language_hint}.
- Start rule_id numbering from {start_index} and increment (e.g. {contract_type}-{start_index:03d}).

Return ONLY the JSON array."""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().lower().startswith("json"):
            text = text.split("\n", 1)[1] if "\n" in text else text[4:]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _call_llm(system: str, user: str) -> List[Dict]:
    """Invoke the configured LLM and parse a JSON array out of the response."""
    from app.agent.llms import llm
    from langchain_core.messages import SystemMessage, HumanMessage

    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = response.content if isinstance(response.content, str) else str(response.content)
    content = _strip_fences(content)
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError(f"LLM did not return a JSON array (got {type(data).__name__})")
    return data


def _validate_rule(rule: Dict, contract_type: str) -> bool:
    required = {"rule_id", "contract_types", "category", "title", "description",
                "standard_practice", "suggested_alternative", "legal_basis",
                "severity", "keywords"}
    if not required.issubset(rule.keys()):
        return False
    if rule["severity"] not in ("high", "medium", "low"):
        return False
    if not isinstance(rule["contract_types"], list) or contract_type not in rule["contract_types"]:
        rule["contract_types"] = [contract_type]
    if not isinstance(rule["keywords"], list) or not rule["keywords"]:
        return False
    if len(rule["rule_id"]) > 50 or len(rule["title"]) > 200:
        return False
    return True


def generate_for_type(plan_entry: Dict, existing_ids: set, existing_titles: set) -> List[Dict]:
    contract_type = plan_entry["contract_type"]
    needed = plan_entry["count"]
    hint = plan_entry["language_hint"]

    print(f"[{contract_type}] target {needed} rules — start")

    collected: List[Dict] = []
    attempts = 0
    start_index = 1

    while len(collected) < needed and attempts < needed * 2:
        attempts += 1
        batch = min(BATCH_SIZE, needed - len(collected))

        with _lock:
            recent_ids = sorted(existing_ids)[-30:]
            recent_titles = sorted(existing_titles)[-30:]

        user_prompt = USER_PROMPT_TEMPLATE.format(
            batch=batch,
            contract_type=contract_type,
            existing_ids=", ".join(recent_ids) or "(none yet)",
            existing_titles=", ".join(recent_titles) or "(none yet)",
            language_hint=hint,
            start_index=start_index,
        )

        try:
            rules = _call_llm(SYSTEM_PROMPT, user_prompt)
        except Exception as exc:
            print(f"[{contract_type}] attempt {attempts}: LLM call failed: {exc}")
            time.sleep(2)
            continue

        accepted = 0
        for r in rules:
            if not _validate_rule(r, contract_type):
                continue
            rid = r["rule_id"].strip().lower()
            title_key = r["title"].strip().lower()
            with _lock:
                if rid in existing_ids or title_key in existing_titles:
                    continue
                existing_ids.add(rid)
                existing_titles.add(title_key)
            r["rule_id"] = rid
            collected.append(r)
            accepted += 1
            if len(collected) >= needed:
                break

        start_index = len(collected) + 1
        print(f"[{contract_type}] attempt {attempts}: +{accepted} (total {len(collected)}/{needed})")

    print(f"[{contract_type}] done — produced {len(collected)} rules")
    return collected


def insert_rules(rules: List[Dict]) -> int:
    db = SessionLocal()
    inserted = 0
    try:
        for r in rules:
            existing = db.query(RiskRule).filter(RiskRule.rule_id == r["rule_id"]).first()
            if existing:
                continue
            obj = RiskRule(
                rule_id=r["rule_id"],
                contract_types=r["contract_types"],
                category=r["category"],
                title=r["title"],
                description=r["description"],
                standard_practice=r["standard_practice"],
                suggested_alternative=r["suggested_alternative"],
                legal_basis=r["legal_basis"][:500],
                severity=r["severity"],
                keywords=r["keywords"],
                is_active=True,
            )
            db.add(obj)
            inserted += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return inserted


def reset_rules() -> int:
    db = SessionLocal()
    try:
        result = db.execute(delete(RiskRule))
        db.commit()
        return result.rowcount or 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and seed risk rules via LLM")
    parser.add_argument("--dry-run", action="store_true", help="Generate only; do not insert")
    parser.add_argument("--reset", action="store_true", help="Delete existing rules before inserting")
    args = parser.parse_args()

    if args.reset and not args.dry_run:
        deleted = reset_rules()
        print(f"Deleted {deleted} existing rules.")

    existing_ids: set = set()
    existing_titles: set = set()
    if not args.dry_run:
        db = SessionLocal()
        try:
            for row in db.query(RiskRule.rule_id, RiskRule.title).all():
                existing_ids.add(row.rule_id.lower())
                existing_titles.add(row.title.strip().lower())
        finally:
            db.close()

    all_rules: List[Dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(generate_for_type, entry, existing_ids, existing_titles): entry["contract_type"]
            for entry in PLAN
        }
        for fut in as_completed(futures):
            ctype = futures[fut]
            try:
                chunk = fut.result()
                all_rules.extend(chunk)
            except Exception as exc:
                print(f"[{ctype}] generation failed: {exc}")

    print(f"\nGenerated total: {len(all_rules)} rules in {time.time() - t0:.1f}s")

    if args.dry_run:
        for r in all_rules[:5]:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    inserted = insert_rules(all_rules)
    print(f"Inserted {inserted} rules into risk_rules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
