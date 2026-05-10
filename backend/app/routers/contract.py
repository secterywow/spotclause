from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.services.file_parser import validate_file, save_temp_file
from app.models.contract import ContractRecord
from app.tasks.analyze import analyze_contract
from app.tasks.compare import compare_contracts
import json
import asyncio

settings = get_settings()
router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.post("/analyze")
async def analyze_contract_endpoint(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Upload and analyze a contract."""
    # Read file
    file_data = await file.read()

    # Validate
    is_valid, error = validate_file(file_data, file.content_type or 'application/pdf')
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Save temp file
    temp_path = save_temp_file(file_data, file.content_type or 'application/pdf')

    # Create record
    record = ContractRecord(
        user_id=user_id,
        file_name=file.filename or 'contract.pdf',
        file_type=file.content_type,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Start Celery task
    task = analyze_contract.delay(temp_path, file.content_type or 'application/pdf', user_id, record.id)

    return {
        "contract_record_id": record.id,
        "task_id": task.id,
        "message": "Analysis started",
    }


@router.get("/analyze/{contract_record_id}/status")
def get_analysis_status(contract_record_id: int, db: Session = Depends(get_db)):
    """Get analysis status and report."""
    record = db.query(ContractRecord).filter(ContractRecord.id == contract_record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {
        "contract_record_id": record.id,
        "file_name": record.file_name,
        "contract_type": record.contract_type,
        "jurisdiction": record.jurisdiction,
        "overall_score": record.overall_score,
        "report": json.loads(record.report_json) if record.report_json else None,
        "created_at": record.created_at,
    }


@router.post("/compare")
async def compare_contracts_endpoint(
    old_file: UploadFile = File(...),
    new_file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Upload two contracts for comparison."""
    old_data = await old_file.read()
    new_data = await new_file.read()

    # Validate
    for fdata, ftype, fname in [(old_data, old_file.content_type, 'old'), (new_data, new_file.content_type, 'new')]:
        is_valid, error = validate_file(fdata, ftype or 'application/pdf')
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"{fname}: {error}")

    old_path = save_temp_file(old_data, old_file.content_type or 'application/pdf')
    new_path = save_temp_file(new_data, new_file.content_type or 'application/pdf')

    # Start comparison task
    task = compare_contracts.delay(
        old_path, old_file.content_type or 'application/pdf',
        new_path, new_file.content_type or 'application/pdf',
        user_id, 0  # compare_record_id placeholder
    )

    return {
        "task_id": task.id,
        "message": "Comparison started",
    }


@router.get("/task/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE stream for task progress."""
    from app.celery_app import celery_app

    async def event_generator():
        while True:
            result = celery_app.AsyncResult(task_id)
            if result.ready():
                yield f"data: {json.dumps({'type': 'result', 'data': result.result})}\n\n"
                break
            elif result.info:
                yield f"data: {json.dumps({'type': 'progress', 'data': result.info})}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/my")
def get_my_contracts(user_id: int, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Get user's contract history."""
    records = db.query(ContractRecord).filter(
        ContractRecord.user_id == user_id
    ).order_by(ContractRecord.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "contracts": [
            {
                "id": r.id,
                "file_name": r.file_name,
                "contract_type": r.contract_type,
                "jurisdiction": r.jurisdiction,
                "overall_score": r.overall_score,
                "created_at": r.created_at,
            }
            for r in records
        ],
        "total": db.query(ContractRecord).filter(ContractRecord.user_id == user_id).count(),
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
