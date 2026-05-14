from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.contract import ContractRecord, ContractMessage
from app.models.user import User
from app.agent.graph import follow_up_app, compress_context
from app.utils.security import decode_access_token
from langchain_core.messages import HumanMessage, AIMessage
import json
import asyncio

router = APIRouter(prefix="/api/follow-up", tags=["follow-up"])


@router.get("/messages/{contract_record_id}")
def get_messages(
    contract_record_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    """Return the chat history + remaining-rounds count for a contract record.
    Called when the user re-opens a previously analyzed contract so the chat
    panel can hydrate before they send a new question."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = int(payload["sub"])
    record = db.query(ContractRecord).filter(
        ContractRecord.id == contract_record_id,
        ContractRecord.user_id == user_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Contract not found")

    msgs = db.query(ContractMessage).filter(
        ContractMessage.contract_record_id == contract_record_id,
    ).order_by(ContractMessage.round, ContractMessage.id).all()

    user_count = sum(1 for m in msgs if m.role == "user")
    return {
        "messages": [{"role": m.role, "content": m.content} for m in msgs],
        "remaining_rounds": max(0, 10 - user_count),
    }


@router.post("/chat/{contract_record_id}")
async def follow_up_chat(
    contract_record_id: int,
    question: str,
    token: str,
    db: Session = Depends(get_db),
):
    """Stream follow-up chat response using LangGraph Agent."""
    # Verify user
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get contract record
    record = db.query(ContractRecord).filter(
        ContractRecord.id == contract_record_id,
        ContractRecord.user_id == user_id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Check follow-up permission
    if user.plan == "free":
        raise HTTPException(status_code=403, detail="Follow-up is available for paid users only")

    # Count existing messages
    existing_count = db.query(ContractMessage).filter(
        ContractMessage.contract_record_id == contract_record_id,
        ContractMessage.role == "user",
    ).count()

    if existing_count >= 10:
        raise HTTPException(status_code=403, detail="Follow-up limit reached (10 rounds)")

    # Get report data
    report = json.loads(record.report_json) if record.report_json else {}
    contract_summary = f"Contract Type: {record.contract_type or 'Unknown'}. Jurisdiction: {record.jurisdiction or 'Unknown'}."
    report_highlights = report.get("summary", "No report available.")

    # Get existing messages
    existing_messages = db.query(ContractMessage).filter(
        ContractMessage.contract_record_id == contract_record_id,
    ).order_by(ContractMessage.round).all()

    # Build message history
    messages = []
    for msg in existing_messages:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))

    # Compress if needed
    messages = compress_context(messages)

    # Add current question
    messages.append(HumanMessage(content=question))

    # Save user message
    user_msg = ContractMessage(
        contract_record_id=contract_record_id,
        round=existing_count + 1,
        role="user",
        content=question,
    )
    db.add(user_msg)
    db.commit()

    # Run LangGraph agent
    state = {
        "messages": messages,
        "contract_summary": contract_summary,
        "report_highlights": report_highlights,
        "remaining_rounds": 10 - existing_count - 1,
        "user_id": user_id,
        "contract_record_id": contract_record_id,
    }

    result = follow_up_app.invoke(state)
    assistant_message = result["messages"][-1]

    # Save assistant message
    assistant_msg = ContractMessage(
        contract_record_id=contract_record_id,
        round=existing_count + 1,
        role="assistant",
        content=assistant_message.content,
        token_output=len(assistant_message.content.split()),
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "response": assistant_message.content,
        "remaining_rounds": 10 - existing_count - 1,
    }


@router.post("/chat/{contract_record_id}/stream")
async def follow_up_chat_stream(
    contract_record_id: int,
    question: str,
    token: str,
    db: Session = Depends(get_db),
):
    """Stream follow-up chat response with SSE."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = int(payload["sub"])
    record = db.query(ContractRecord).filter(
        ContractRecord.id == contract_record_id,
        ContractRecord.user_id == user_id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Check permission
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.plan == "free":
        raise HTTPException(status_code=403, detail="Follow-up is available for paid users only")

    existing_count = db.query(ContractMessage).filter(
        ContractMessage.contract_record_id == contract_record_id,
        ContractMessage.role == "user",
    ).count()

    if existing_count >= 10:
        raise HTTPException(status_code=403, detail="Follow-up limit reached")

    report = json.loads(record.report_json) if record.report_json else {}
    contract_summary = f"Contract Type: {record.contract_type or 'Unknown'}. Jurisdiction: {record.jurisdiction or 'Unknown'}."
    report_highlights = report.get("summary", "No report available.")

    existing_messages = db.query(ContractMessage).filter(
        ContractMessage.contract_record_id == contract_record_id,
    ).order_by(ContractMessage.round).all()

    messages = []
    for msg in existing_messages:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))

    messages = compress_context(messages)
    messages.append(HumanMessage(content=question))

    # Save user message
    user_msg = ContractMessage(
        contract_record_id=contract_record_id,
        round=existing_count + 1,
        role="user",
        content=question,
    )
    db.add(user_msg)
    db.commit()

    async def event_generator():
        full_response = ""
        try:
            state = {
                "messages": messages,
                "contract_summary": contract_summary,
                "report_highlights": report_highlights,
                "remaining_rounds": 10 - existing_count - 1,
                "user_id": user_id,
                "contract_record_id": contract_record_id,
            }

            result = follow_up_app.invoke(state)
            assistant_message = result["messages"][-1]
            full_response = assistant_message.content

            # Stream word by word
            words = full_response.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'stream', 'content': chunk})}\n\n"
                await asyncio.sleep(0.02)

            yield f"data: {json.dumps({'type': 'done', 'remaining_rounds': 10 - existing_count - 1})}\n\n"

            # Save assistant message
            assistant_msg = ContractMessage(
                contract_record_id=contract_record_id,
                round=existing_count + 1,
                role="assistant",
                content=full_response,
                token_output=len(words),
            )
            db.add(assistant_msg)
            db.commit()

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
