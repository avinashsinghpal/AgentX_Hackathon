"""Chat orchestrator.

All consequential work is delegated to :class:`ResolutionService`; this class
only adapts the service to the existing chat endpoint contracts.  Both the
streaming and non-streaming paths therefore share one implementation of policy
evaluation, authorization, action execution and verification.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.orm import Session

from app.models.case import CaseMessage
from app.services.llm.client import LLMClient, get_llm_client
from app.services.resolution import ResolutionService


class ResolutionOrchestrator:
    def __init__(self, db: Session, llm_client: LLMClient | None = None):
        self.db = db
        self.llm = llm_client or get_llm_client()
        self.service = ResolutionService(llm_client=self.llm)

    async def process_case_resolution(self, case_id: str) -> CaseMessage:
        outcome = await self.service.resolve_case(self.db, case_id)
        if outcome.message is None:  # pragma: no cover - persist_message defaults True
            raise RuntimeError("Resolution did not persist an agent message")
        return outcome.message

    async def stream_case_resolution(
        self,
        case_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streams real-time events for SSE chat endpoints."""
        async for event in self.service.stream_case(self.db, case_id):
            yield event
