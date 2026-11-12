import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.deps import CurrentBuyer, DbSession
from app.core.logging import logger
from app.models.case import Case, CaseMessage
from app.schemas.buyer import CaseMessageItem
from app.services.agent.orchestrator import ResolutionOrchestrator

router = APIRouter(prefix="/cases", tags=["Resolution Chat & Streaming"])


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    client_message_id: str | None = Field(default=None, min_length=1, max_length=64)


@router.post("/{case_id}/chat", response_model=CaseMessageItem)
async def send_chat_message(
    case_id: str,
    data: ChatMessageRequest,
    buyer: CurrentBuyer,
    db: DbSession,
) -> CaseMessageItem:
    message = data.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message must not be blank.",
        )

    bind = db.get_bind()
    engine = bind if isinstance(bind, Engine) else bind.engine
    lock_connection = engine.connect()
    lock_key = f"buyer-case-chat:{case_id}"
    lock_acquired = False
    try:
        lock_connection.execute(
            text("SELECT pg_advisory_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": lock_key},
        )
        lock_connection.commit()
        lock_acquired = True

        case = (
            db.query(Case)
            .filter(Case.id == case_id, Case.buyer_id == buyer.id)
            .first()
        )
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied.",
            )

        buyer_msg = None
        if data.client_message_id:
            buyer_msg = (
                db.query(CaseMessage)
                .filter(
                    CaseMessage.case_id == case.id,
                    CaseMessage.sender_role == "buyer",
                    CaseMessage.client_message_id == data.client_message_id,
                )
                .first()
            )
            if buyer_msg and buyer_msg.message != message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This message ID was already used for a different message.",
                )

            if buyer_msg:
                completed_response = (
                    db.query(CaseMessage)
                    .filter(
                        CaseMessage.case_id == case.id,
                        CaseMessage.sender_role == "agent",
                        CaseMessage.client_message_id == data.client_message_id,
                    )
                    .first()
                )
                if completed_response:
                    return CaseMessageItem(
                        id=completed_response.id,
                        sender_role=completed_response.sender_role,
                        message=completed_response.message,
                        tool_calls=completed_response.tool_calls,
                        decision_badge=completed_response.decision_badge,
                        created_at=completed_response.created_at.isoformat(),
                    )

        if buyer_msg is None:
            buyer_msg = CaseMessage(
                case_id=case.id,
                sender_role="buyer",
                message=message,
                client_message_id=data.client_message_id,
            )
            db.add(buyer_msg)
            db.commit()

        orchestrator = ResolutionOrchestrator(db=db)
        if case.status in {"resolved", "rejected", "pending_approval"} or case.decision:
            agent_msg = await orchestrator.respond_to_follow_up(case_id=case.id)
        else:
            agent_msg = await orchestrator.process_case_resolution(case_id=case.id)

        agent_msg.client_message_id = data.client_message_id
        db.commit()
        db.refresh(agent_msg)

        return CaseMessageItem(
            id=agent_msg.id,
            sender_role=agent_msg.sender_role,
            message=agent_msg.message,
            tool_calls=agent_msg.tool_calls,
            decision_badge=agent_msg.decision_badge,
            created_at=agent_msg.created_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Customer chat processing failed for case %s", case_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The agent could not complete this message. Retry it with the same "
                "message ID to safely continue."
            ),
        ) from exc
    finally:
        if lock_acquired:
            lock_connection.execute(
                text("SELECT pg_advisory_unlock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )
            lock_connection.commit()
        lock_connection.close()


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
