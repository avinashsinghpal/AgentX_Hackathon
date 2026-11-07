import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentBuyer, DbSession
from app.models.case import Case, CaseMessage
from app.schemas.buyer import CaseMessageItem
from app.services.agent.orchestrator import ResolutionOrchestrator

router = APIRouter(prefix="/cases", tags=["Resolution Chat & Streaming"])


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


@router.post("/{case_id}/chat", response_model=CaseMessageItem)
async def send_chat_message(
    case_id: str,
    data: ChatMessageRequest,
    buyer: CurrentBuyer,
    db: DbSession,
) -> CaseMessageItem:
    case = db.query(Case).filter(Case.id == case_id, Case.buyer_id == buyer.id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or access denied.",
        )

    # 1. Save customer message turn
    buyer_msg = CaseMessage(
        case_id=case.id,
        sender_role="buyer",
        message=data.message.strip(),
    )
    db.add(buyer_msg)
    db.commit()

    # 2. Run Orchestrator
    orchestrator = ResolutionOrchestrator(db=db)
    agent_msg = await orchestrator.process_case_resolution(case_id=case.id)

    return CaseMessageItem(
        id=agent_msg.id,
        sender_role=agent_msg.sender_role,
        message=agent_msg.message,
        tool_calls=agent_msg.tool_calls,
        decision_badge=agent_msg.decision_badge,
        created_at=agent_msg.created_at.isoformat(),
    )


@router.get("/{case_id}/chat/stream")
async def stream_chat_resolution(
    case_id: str,
    buyer: CurrentBuyer,
    db: DbSession,
) -> StreamingResponse:
    case = db.query(Case).filter(Case.id == case_id, Case.buyer_id == buyer.id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or access denied.",
        )

    orchestrator = ResolutionOrchestrator(db=db)

    async def event_generator() -> AsyncGenerator[str, None]:
        async for item in orchestrator.stream_case_resolution(case_id=case.id):
            event_name = item["event"]
            payload = json.dumps(item["data"])
            yield f"event: {event_name}\ndata: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
