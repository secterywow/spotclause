from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.config import get_settings
from app.services.file_parser import validate_file, save_temp_file, parse_file_sync
from app.models.contract import ContractRecord
from app.logger import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import asyncio
import os
import queue
import threading
import time
import urllib.parse
from typing import Optional

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter(prefix="/api/contracts", tags=["contracts"])


# ---------------------------------------------------------------------------
# Usage limit helpers
# ---------------------------------------------------------------------------

_PLAN_LIMITS = {
    "free": {"analyze": 1, "compare": 1},
    "standard": {"analyze": 20, "compare": 20},
    "pro": {"analyze": 100, "compare": 100},
}


def _get_current_month() -> str:
    return time.strftime("%Y-%m")


def _check_usage_limit(db: Session, user_id: int, action: str) -> tuple[bool, str, dict]:
    """Check if user has quota for the action. Returns (allowed, message, usage_info).

    action: 'analyze' | 'compare'
    """
    from app.models.user import User
    from app.models.usage import UsageTracking

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User not found", {}

    plan = user.plan or "free"
    limit = _PLAN_LIMITS.get(plan, _PLAN_LIMITS["free"]).get(action, 0)

    # Free plan uses lifetime limits (not monthly)
    if plan == "free":
        total_used = db.query(func.count(ContractRecord.id)).filter(
            ContractRecord.user_id == user_id,
            ContractRecord.record_type == ("analysis" if action == "analyze" else "comparison"),
        ).scalar() or 0

        remaining = max(0, limit - total_used)
        if remaining <= 0:
            return False, f"您已用完免费的{limit}次{'合同审查' if action == 'analyze' else '合同对比'}机会，请升级会员以继续使用。", {
                "plan": plan,
                "limit": limit,
                "used": total_used,
                "remaining": 0,
            }
        return True, "", {
            "plan": plan,
            "limit": limit,
            "used": total_used,
            "remaining": remaining,
        }

    # Paid plans use monthly limits
    month = _get_current_month()
    usage = db.query(UsageTracking).filter(
        UsageTracking.user_id == user_id,
        UsageTracking.month == month,
    ).first()

    used = getattr(usage, f"{action}_count", 0) if usage else 0
    remaining = max(0, limit - used)

    if remaining <= 0:
        return False, f"本月{'合同审查' if action == 'analyze' else '合同对比'}次数已用完（{limit}次/月），请升级套餐或次月再试。", {
            "plan": plan,
            "limit": limit,
            "used": used,
            "remaining": 0,
        }
    return True, "", {
        "plan": plan,
        "limit": limit,
        "used": used,
        "remaining": remaining,
    }


def _increment_usage(db: Session, user_id: int, action: str) -> None:
    """Increment usage counter for paid plans. Free plans are tracked by record count."""
    from app.models.user import User
    from app.models.usage import UsageTracking

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.plan == "free":
        return

    month = _get_current_month()
    usage = db.query(UsageTracking).filter(
        UsageTracking.user_id == user_id,
        UsageTracking.month == month,
    ).first()

    if usage:
        setattr(usage, f"{action}_count", getattr(usage, f"{action}_count", 0) + 1)
    else:
        usage = UsageTracking(
            user_id=user_id,
            month=month,
            **{f"{action}_count": 1},
        )
        db.add(usage)
    db.commit()


# ---------------------------------------------------------------------------
# In-process progress bus
# ---------------------------------------------------------------------------
# The analysis runs in a thread pool (FastAPI BackgroundTasks executes sync
# functions in a worker thread). The SSE handler is async. We bridge the two
# with a per-record threading.Queue. The queue is created BEFORE the response
# to /analyze is sent, so the frontend's SSE GET can never race ahead and miss
# events. After the pipeline emits its terminal event, we leave the queue in
# the channel for 60s so a late-arriving client can still drain it, then we
# clean up.
# ---------------------------------------------------------------------------

_progress_lock = threading.Lock()
_progress: dict[int, dict] = {}

_QUEUE_TTL_SECONDS = 60


def _init_progress(record_id: int) -> None:
    with _progress_lock:
        _progress[record_id] = {
            "queue": queue.Queue(),
            "done": False,
        }


def _emit_progress(record_id: int, event: dict) -> None:
    with _progress_lock:
        ch = _progress.get(record_id)
    if ch is None:
        return
    try:
        ch["queue"].put_nowait(event)
    except queue.Full:
        logger.warning("Progress queue full; dropping event",
                       record_id=record_id, event_type=event.get("type"))


def _close_progress(record_id: int) -> None:
    """Mark the channel as terminated. Cleanup is deferred via a timer so a
    late-arriving SSE consumer (slow browser, retried connection) can still
    drain the queue."""
    with _progress_lock:
        ch = _progress.get(record_id)
    if ch is None:
        return
    ch["done"] = True
    try:
        ch["queue"].put_nowait({"type": "__close__"})
    except queue.Full:
        pass

    def _cleanup():
        with _progress_lock:
            _progress.pop(record_id, None)

    threading.Timer(_QUEUE_TTL_SECONDS, _cleanup).start()


def _get_progress_channel(record_id: int):
    with _progress_lock:
        return _progress.get(record_id)


# ---------------------------------------------------------------------------
# Analysis pipeline (streaming)
# ---------------------------------------------------------------------------

def run_analysis_pipeline_streaming(file_path: str, mime_type: str,
                                     user_id: int, contract_record_id: int) -> None:
    """Phase-aware analysis pipeline. Emits progress events to the in-process
    progress bus as each phase completes, then persists the assembled report.

    Phases:
      parse        — file → text (fast, regex-only)
      structure    — 1 LLM call: contractType + clauses skeleton
      analyze      — N LLM calls in parallel: per-clause risk + side-info
                     (missing/terms/dates pass piggybacks on the same pool)
      assemble     — merge clauses+analysis, save to DB, emit complete event
    """
    db = SessionLocal()
    try:
        t0 = time.time()
        logger.info("Streaming analysis starting", contract_record_id=contract_record_id)
        _emit_progress(contract_record_id, {"type": "phase", "name": "parse"})

        parsed = parse_file_sync(file_path, mime_type)
        raw_text = parsed["text"]

        if not raw_text or len(raw_text) < 50:
            raise ValueError("Could not extract sufficient text from file")

        from app.services.analysis import (
            detect_jurisdiction,
            extract_structure_pass,
            analyze_single_clause,
            extract_side_info,
            extract_dates,
            assemble_report,
        )

        jurisdiction = detect_jurisdiction(raw_text)

        # ---- Phase 1: structure ----
        _emit_progress(contract_record_id, {
            "type": "phase",
            "name": "structure",
        })
        structure = extract_structure_pass(raw_text, jurisdiction)
        clauses = structure["clauses"]
        contract_type = structure["contractType"]
        _emit_progress(contract_record_id, {
            "type": "structure_done",
            "clauseCount": len(clauses),
            "contractType": contract_type,
            "jurisdiction": jurisdiction,
        })
        logger.info("Structure pass complete",
                    contract_record_id=contract_record_id,
                    clause_count=len(clauses),
                    elapsed_s=round(time.time() - t0, 2))

        # ---- Phase 2: parallel per-clause risk + side-info ----
        _emit_progress(contract_record_id, {
            "type": "phase",
            "name": "analyze",
            "total": len(clauses),
        })

        analyzed: list = [None] * len(clauses)
        side_info_result: dict = {"value": None}
        completed_clauses = 0
        analyze_t0 = time.time()

        # Pool size = clauses + 1 (side-info worker), capped at 10 so we don't
        # hammer the upstream LLM endpoint when there are many clauses.
        pool_workers = min(10, max(2, len(clauses) + 1))

        with ThreadPoolExecutor(max_workers=pool_workers) as pool:
            futures = {}
            for i, c in enumerate(clauses):
                fut = pool.submit(analyze_single_clause, c, contract_type, jurisdiction)
                futures[fut] = ("clause", i)
            titles = [c.get("title", "") for c in clauses]
            side_fut = pool.submit(extract_side_info, raw_text, contract_type,
                                    jurisdiction, titles)
            futures[side_fut] = ("side", -1)

            for fut in as_completed(futures):
                kind, idx = futures[fut]
                try:
                    result = fut.result()
                except Exception as e:
                    logger.error("Pipeline worker failed", error=str(e),
                                 kind=kind, idx=idx)
                    result = None
                if kind == "clause":
                    if result is None:
                        result = {
                            "riskLevel": "low",
                            "explanation": "",
                            "riskReason": "",
                            "solution": "",
                            "negotiationScript": {
                                "yourOpening": "",
                                "theirRebuttal": "",
                                "yourResponse": "",
                            },
                        }
                    analyzed[idx] = result
                    completed_clauses += 1
                    _emit_progress(contract_record_id, {
                        "type": "clause_progress",
                        "completed": completed_clauses,
                        "total": len(clauses),
                    })
                else:
                    side_info_result["value"] = result or {
                        "missingClauses": [],
                        "keyTerms": [],
                        "keyDates": [],
                    }
                    side = side_info_result["value"]
                    _emit_progress(contract_record_id, {
                        "type": "side_info_done",
                        "missingCount": len(side.get("missingClauses") or []),
                        "termCount": len(side.get("keyTerms") or []),
                        "dateCount": len(side.get("keyDates") or []),
                    })

        # Backfill any clause whose analysis returned None (defensive — handled above)
        for i, a in enumerate(analyzed):
            if a is None:
                analyzed[i] = {
                    "riskLevel": "low",
                    "explanation": "",
                    "riskReason": "",
                    "solution": "",
                    "negotiationScript": {
                        "yourOpening": "",
                        "theirRebuttal": "",
                        "yourResponse": "",
                    },
                }

        side = side_info_result["value"] or {
            "missingClauses": [], "keyTerms": [], "keyDates": []
        }

        logger.info("Analyze phase complete",
                    contract_record_id=contract_record_id,
                    clauses_completed=completed_clauses,
                    clauses_total=len(clauses),
                    analyze_elapsed_s=round(time.time() - analyze_t0, 2))

        # Date fallback: if the side-info LLM returned no dates (Chinese contracts
        # sometimes trip the model up on date formats), use the regex extractor.
        if not side.get("keyDates"):
            side["keyDates"] = extract_dates(raw_text)

        # ---- Phase 3: assemble + save ----
        _emit_progress(contract_record_id, {"type": "phase", "name": "assemble"})
        report = assemble_report(
            contract_type=contract_type,
            jurisdiction=jurisdiction,
            clauses=clauses,
            analysis_results=analyzed,
            missing_clauses=side["missingClauses"],
            key_terms=side["keyTerms"],
            key_dates=side["keyDates"],
        )

        record = db.query(ContractRecord).filter(ContractRecord.id == contract_record_id).first()
        if record:
            record.contract_type = contract_type
            record.jurisdiction = jurisdiction
            record.high_risk_count = report["riskBreakdown"]["high"]
            record.medium_risk_count = report["riskBreakdown"]["medium"]
            record.low_risk_count = report["riskBreakdown"]["low"]
            record.report_json = json.dumps(report)
            db.commit()

        elapsed = round(time.time() - t0, 2)
        logger.info("Streaming analysis complete",
                    contract_record_id=contract_record_id,
                    elapsed_s=elapsed,
                    clause_count=len(clauses))

        _emit_progress(contract_record_id, {
            "type": "complete",
            "report": report,
            "contract_record_id": contract_record_id,
            "elapsed_s": elapsed,
        })

        # Increment usage for paid plans after successful analysis
        _increment_usage(db, user_id, "analyze")

    except Exception as e:
        logger.error("Streaming analysis failed",
                     error=str(e), contract_record_id=contract_record_id)
        _emit_progress(contract_record_id, {
            "type": "error",
            "message": str(e),
        })
        try:
            record = db.query(ContractRecord).filter(ContractRecord.id == contract_record_id).first()
            if record:
                record.report_json = json.dumps({"error": str(e)})
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
        _close_progress(contract_record_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


# Legacy alias kept for any callers/imports still pointing at the old name.
def run_analysis_pipeline(file_path: str, mime_type: str, user_id: int, contract_record_id: int):
    return run_analysis_pipeline_streaming(file_path, mime_type, user_id, contract_record_id)


def run_compare_pipeline(old_path: str, old_mime: str, new_path: str, new_mime: str, user_id: int):
    """Run contract comparison pipeline synchronously."""
    try:
        logger.info("Starting comparison")
        t0 = time.time()
        old_parsed = parse_file_sync(old_path, old_mime)
        new_parsed = parse_file_sync(new_path, new_mime)

        from app.services.comparison import (
            align_differences, analyze_change_risk,
            detect_hidden_traps, assemble_compare_report,
            check_contract_relatedness,
        )

        is_related, similarity = check_contract_relatedness(
            old_parsed['text'], new_parsed['text'], threshold=0.30
        )
        if not is_related:
            return {
                "error": "这两份合同看起来不是同一个文件的不同版本，无法进行对比分析。请上传同一份合同的旧版和新版。",
                "similarity": round(similarity, 2),
            }

        changes = align_differences(old_parsed['text'], new_parsed['text'])

        # Parallelize per-change risk analysis. Each call is an independent
        # LLM round-trip (~5-10s), so serial loops on contracts with many
        # changes blow past two minutes. A small pool keeps upstream load
        # reasonable while cutting wall-clock time by ~10x.
        if changes:
            pool_workers = min(8, max(2, len(changes)))
            with ThreadPoolExecutor(max_workers=pool_workers) as pool:
                futures = {pool.submit(analyze_change_risk, c): i for i, c in enumerate(changes)}
                for fut in as_completed(futures):
                    i = futures[fut]
                    try:
                        analysis = fut.result()
                    except Exception as e:
                        logger.error("Change risk analysis failed", error=str(e), idx=i)
                        analysis = {"riskChange": "unchanged", "analysis": ""}
                    changes[i].update(analysis)

        hidden_traps = detect_hidden_traps(changes)
        report = assemble_compare_report(changes, hidden_traps)
        logger.info("Comparison complete",
                    elapsed_s=round(time.time() - t0, 2),
                    change_count=len(changes),
                    trap_count=len(hidden_traps))

        return report

    except Exception as e:
        logger.error("Comparison failed", error=str(e))
        return {"error": str(e)}
    finally:
        for path in [old_path, new_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass


@router.post("/analyze")
async def analyze_contract_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Upload a contract. Returns a record_id immediately; clients should open
    the `/analyze/{id}/stream` SSE endpoint to watch progress.

    Cache hit: the prior report is cloned into a fresh record and returned
    synchronously (`cached: true`). The stream endpoint will dump the cached
    payload as a single complete event so the same frontend flow works."""
    import hashlib

    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found. Please login again.")

    # Check usage limit
    allowed, msg, usage_info = _check_usage_limit(db, user_id, "analyze")
    if not allowed:
        raise HTTPException(status_code=403, detail=msg)

    file_data = await file.read()

    is_valid, error = validate_file(file_data, file.content_type or 'application/pdf')
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    file_hash = hashlib.sha256(file_data).hexdigest()

    filename = file.filename or 'contract.pdf'
    file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'unknown'
    file_ext = file_ext[:20]

    cached = (
        db.query(ContractRecord)
        .filter(ContractRecord.file_hash == file_hash)
        .filter(ContractRecord.report_json.is_not(None))
        .order_by(ContractRecord.created_at.desc())
        .first()
    )
    cache_payload = None
    if cached and cached.report_json:
        try:
            parsed = json.loads(cached.report_json)
            if isinstance(parsed, dict) and 'error' not in parsed:
                cache_payload = parsed
        except Exception:
            cache_payload = None

    if cache_payload is not None:
        record = ContractRecord(
            user_id=user_id,
            file_name=filename,
            file_type=file_ext,
            file_hash=file_hash,
            contract_type=cached.contract_type,
            jurisdiction=cached.jurisdiction,
            high_risk_count=cached.high_risk_count,
            medium_risk_count=cached.medium_risk_count,
            low_risk_count=cached.low_risk_count,
            report_json=cached.report_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info("Analysis cache hit — reused prior report",
                    file_hash=file_hash[:12], record_id=record.id,
                    source_record_id=cached.id)
        _increment_usage(db, user_id, "analyze")
        return {
            "contract_record_id": record.id,
            "cached": True,
            "message": "Analysis complete (cached).",
        }

    temp_path = save_temp_file(file_data, file.content_type or 'application/pdf')

    record = ContractRecord(
        user_id=user_id,
        file_name=filename,
        file_type=file_ext,
        file_hash=file_hash,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Init the progress channel BEFORE the response is sent so the stream
    # endpoint can never race ahead of the producer.
    _init_progress(record.id)

    background_tasks.add_task(
        run_analysis_pipeline_streaming,
        temp_path,
        file.content_type or 'application/pdf',
        user_id,
        record.id,
    )

    return {
        "contract_record_id": record.id,
        "cached": False,
        "message": "Analysis started. Open /analyze/{id}/stream for progress.",
    }


@router.get("/analyze/{contract_record_id}/stream")
async def analyze_stream(contract_record_id: int, db: Session = Depends(get_db)):
    """Server-Sent Events stream of analysis progress for a given record.

    Behavior:
      • If the record already has a saved report (cache hit or already finished),
        emit a single `complete` event and close.
      • Otherwise attach to the in-process progress channel and forward events
        as the background pipeline emits them. Heartbeat comments are sent every
        ~15s so proxies don't close the connection.
    """
    record = db.query(ContractRecord).filter(ContractRecord.id == contract_record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Contract not found")

    record_id_local = record.id
    initial_report_json = record.report_json

    async def gen():
        # Fast path: report already in DB
        if initial_report_json:
            try:
                parsed = json.loads(initial_report_json)
                if isinstance(parsed, dict) and 'error' in parsed:
                    yield f"data: {json.dumps({'type': 'error', 'message': parsed['error']})}\n\n"
                elif isinstance(parsed, dict):
                    yield f"data: {json.dumps({'type': 'complete', 'report': parsed, 'contract_record_id': record_id_local, 'cached': True})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid stored report'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        ch = _get_progress_channel(record_id_local)
        if ch is None:
            # The pipeline isn't running and the DB has no report. This happens
            # if the user reloads the page mid-analysis after the queue TTL has
            # passed. Fall back to a short DB poll loop.
            yield f"data: {json.dumps({'type': 'phase', 'name': 'parse'})}\n\n"
            for _ in range(120):  # 60 s
                await asyncio.sleep(0.5)
                fresh_db = SessionLocal()
                try:
                    fresh = fresh_db.query(ContractRecord).filter(ContractRecord.id == record_id_local).first()
                    if fresh and fresh.report_json:
                        parsed = json.loads(fresh.report_json)
                        if isinstance(parsed, dict) and 'error' in parsed:
                            yield f"data: {json.dumps({'type': 'error', 'message': parsed['error']})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'complete', 'report': parsed, 'contract_record_id': record_id_local})}\n\n"
                        return
                finally:
                    fresh_db.close()
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream timed out'})}\n\n"
            return

        q: queue.Queue = ch["queue"]
        idle_seconds = 0.0
        while True:
            try:
                evt = await asyncio.to_thread(q.get, True, 1.0)
            except queue.Empty:
                idle_seconds += 1.0
                # SSE comment lines act as a keep-alive without producing a data frame
                if idle_seconds >= 15:
                    idle_seconds = 0.0
                    yield ": heartbeat\n\n"
                continue
            idle_seconds = 0.0
            evt_type = evt.get("type")
            if evt_type == "__close__":
                return
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            if evt_type in {"complete", "error"}:
                return

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/analyze/{contract_record_id}/status")
def get_analysis_status(contract_record_id: int, db: Session = Depends(get_db)):
    """Get analysis status and report. Kept for back-compat (older clients poll
    this endpoint). New clients should use /analyze/{id}/stream."""
    record = db.query(ContractRecord).filter(ContractRecord.id == contract_record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Contract not found")

    report = None
    if record.report_json:
        try:
            report = json.loads(record.report_json)
        except:
            report = None

    return {
        "contract_record_id": record.id,
        "file_name": record.file_name,
        "record_type": record.record_type,
        "contract_type": record.contract_type,
        "jurisdiction": record.jurisdiction,
        "overall_score": record.overall_score,
        "report": report,
        "created_at": record.created_at,
    }


# ---------------------------------------------------------------------------
# Report exports
# ---------------------------------------------------------------------------

@router.get("/{contract_record_id}/export")
def export_report(contract_record_id: int, format: str = "pdf",
                  user_id: int = 0, db: Session = Depends(get_db)):
    """Generate a PDF or DOCX of the saved analysis report.

    `format`: `pdf` (default) or `docx`. The returned response carries a
    Content-Disposition header so the browser saves it with the contract's
    filename, transliterated/sanitized."""
    fmt = (format or "pdf").lower()
    if fmt not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="format must be 'pdf' or 'docx'")

    record = db.query(ContractRecord).filter(ContractRecord.id == contract_record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Only the owner may export their own report.
    if user_id and record.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your contract")

    if not record.report_json:
        raise HTTPException(status_code=409, detail="Analysis not yet complete")

    try:
        report = json.loads(record.report_json)
    except Exception:
        raise HTTPException(status_code=500, detail="Stored report is malformed")
    if isinstance(report, dict) and "error" in report:
        raise HTTPException(status_code=409, detail=f"Analysis failed: {report['error']}")

    from app.services.export import (
        generate_pdf_bytes, generate_docx_bytes, sanitize_filename, ascii_filename,
    )
    utf8_name = sanitize_filename(record.file_name or "contract")
    safe_name = ascii_filename(record.file_name or "contract")

    if fmt == "pdf":
        data = generate_pdf_bytes(report, file_name=record.file_name or "contract")
        media = "application/pdf"
        ext = "pdf"
    else:
        data = generate_docx_bytes(report, file_name=record.file_name or "contract")
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"

    # Latin-1 only header value with an RFC 5987 extension that carries the
    # full UTF-8 filename for browsers that understand it (every modern one).
    ascii_disposition = f"{safe_name}-report.{ext}"
    quoted = urllib.parse.quote(f"{utf8_name}-report.{ext}")
    return Response(
        content=data,
        media_type=media,
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_disposition}\"; filename*=UTF-8''{quoted}",
            "Cache-Control": "no-store",
        },
    )


@router.post("/compare")
async def compare_contracts_endpoint(
    background_tasks: BackgroundTasks,
    old_file: UploadFile = File(...),
    new_file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Upload two contracts for comparison."""
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found. Please login again.")

    # Check usage limit
    allowed, msg, usage_info = _check_usage_limit(db, user_id, "compare")
    if not allowed:
        raise HTTPException(status_code=403, detail=msg)

    old_data = await old_file.read()
    new_data = await new_file.read()

    for fdata, ftype, fname in [(old_data, old_file.content_type, 'old'), (new_data, new_file.content_type, 'new')]:
        is_valid, error = validate_file(fdata, ftype or 'application/pdf')
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"{fname}: {error}")

    old_path = save_temp_file(old_data, old_file.content_type or 'application/pdf')
    new_path = save_temp_file(new_data, new_file.content_type or 'application/pdf')

    # For now, run sync (can be improved with task queue later)
    report = run_compare_pipeline(
        old_path, old_file.content_type or 'application/pdf',
        new_path, new_file.content_type or 'application/pdf',
        user_id
    )

    # If the contracts are unrelated, return the error immediately without
    # persisting a record.
    if report.get("error"):
        return {"report": report}

    # Persist comparison so it appears in "My Contracts" alongside reviews.
    old_name = old_file.filename or 'old_contract'
    new_name = new_file.filename or 'new_contract'
    display_name = f"{old_name} vs {new_name}"

    record = ContractRecord(
        user_id=user_id,
        file_name=display_name,
        file_type='compare',
        record_type='comparison',
        report_json=json.dumps(report),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    _increment_usage(db, user_id, "compare")

    return {
        "report": report,
        "contract_record_id": record.id,
    }


def _get_contract_status(record: ContractRecord) -> Optional[str]:
    """Determine display status for a contract record.

    - None      → completed successfully (no status badge shown)
    - 'pending' → analysis still running
    - 'failed'  → analysis/comparison encountered an error
    """
    if record.report_json is None:
        return "pending"
    try:
        parsed = json.loads(record.report_json)
        if isinstance(parsed, dict) and parsed.get("error"):
            return "failed"
    except Exception:
        pass
    return None  # success → no badge


@router.get("/my")
def get_my_contracts(
    user_id: int,
    record_type: str = "",  # empty = all; 'analysis' | 'comparison'
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get user's contract history (both analysis and comparison records)."""
    base_q = db.query(ContractRecord).filter(ContractRecord.user_id == user_id)

    if record_type in {"analysis", "comparison"}:
        base_q = base_q.filter(ContractRecord.record_type == record_type)

    records = base_q.order_by(
        ContractRecord.created_at.desc()
    ).offset(skip).limit(limit).all()

    # Type counts for the filter tabs
    counts = (
        db.query(ContractRecord.record_type, func.count(ContractRecord.id))
        .filter(ContractRecord.user_id == user_id)
        .group_by(ContractRecord.record_type)
        .all()
    )
    counts_dict = {row[0]: row[1] for row in counts}
    total_analysis = counts_dict.get("analysis", 0)
    total_comparison = counts_dict.get("comparison", 0)

    return {
        "contracts": [
            {
                "id": r.id,
                "file_name": r.file_name,
                "record_type": r.record_type,
                "contract_type": r.contract_type,
                "jurisdiction": r.jurisdiction,
                "overall_score": r.overall_score,
                "status": _get_contract_status(r),
                "created_at": r.created_at,
            }
            for r in records
        ],
        "total": base_q.count(),
        "counts": {
            "all": total_analysis + total_comparison,
            "analysis": total_analysis,
            "comparison": total_comparison,
        },
    }


@router.delete("/{contract_record_id}")
def delete_contract(contract_record_id: int, user_id: int, db: Session = Depends(get_db)):
    """Delete a contract record."""
    record = db.query(ContractRecord).filter(
        ContractRecord.id == contract_record_id,
        ContractRecord.user_id == user_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Contract not found")

    db.delete(record)
    db.commit()

    return {"message": "Contract deleted"}


@router.get("/usage/{user_id}")
def get_usage(user_id: int, db: Session = Depends(get_db)):
    """Return current usage stats for the user."""
    from app.models.user import User
    from app.models.usage import UsageTracking

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan = user.plan or "free"
    limits = _PLAN_LIMITS.get(plan, _PLAN_LIMITS["free"])
    month = _get_current_month()

    # Free plan: count total records
    if plan == "free":
        analyze_used = db.query(func.count(ContractRecord.id)).filter(
            ContractRecord.user_id == user_id,
            ContractRecord.record_type == "analysis",
        ).scalar() or 0
        compare_used = db.query(func.count(ContractRecord.id)).filter(
            ContractRecord.user_id == user_id,
            ContractRecord.record_type == "comparison",
        ).scalar() or 0
    else:
        usage = db.query(UsageTracking).filter(
            UsageTracking.user_id == user_id,
            UsageTracking.month == month,
        ).first()
        analyze_used = usage.analyze_count if usage else 0
        compare_used = usage.compare_count if usage else 0

    return {
        "plan": plan,
        "month": month,
        "analyze": {
            "limit": limits["analyze"],
            "used": analyze_used,
            "remaining": max(0, limits["analyze"] - analyze_used),
        },
        "compare": {
            "limit": limits["compare"],
            "used": compare_used,
            "remaining": max(0, limits["compare"] - compare_used),
        },
    }
