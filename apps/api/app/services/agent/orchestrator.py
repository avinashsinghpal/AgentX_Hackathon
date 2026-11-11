"""Chat orchestrator.

All consequential work is delegated to :class:`ResolutionService`; this class
only adapts the service to the existing chat endpoint contracts.  Both the
streaming and non-streaming paths therefore share one implementation of policy
evaluation, authorization, action execution and verification.

The orchestrator also exposes a small, read-mostly tool surface for multi-turn
LLM interactions.  Financial actions are never executed from LLM arguments:
mutating tools delegate to the authoritative ResolutionService and existing
approval/action services.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.orm import Session

from app.models.case import Case, CaseMessage
from app.models.order import Order
from app.services.agent.tool_schemas import TOOL_INPUT_SCHEMAS, validate_tool_arguments
from app.services.agent.tools import ResolutionTools
from app.services.approvals import ApprovalService
from app.services.llm.client import LLMClient, get_llm_client
from app.services.policy.evaluator import PolicyEvaluationService
from app.services.resolution import ResolutionService
from app.services.risk import RiskEvaluationService


class ResolutionOrchestrator:
    MAX_TOOL_CALLS = 6

    def __init__(self, db: Session | None = None, llm_client: LLMClient | None = None):
        self.db = db
        self.llm = llm_client or get_llm_client()
        self.service = ResolutionService(llm_client=self.llm)

    def available_tools(self) -> list[dict[str, Any]]:
        """Describe the tools available to the LLM without exposing internals."""
        return [
            {
                "name": "lookup_order",
                "description": "Retrieve trusted order details for the case's order.",
                "arguments": {"order_id": "optional order id; defaults to the case order"},
            },
            {
                "name": "lookup_shipment",
                "description": "Retrieve trusted shipment and tracking details for the case's order.",
                "arguments": {"order_id": "optional order id; defaults to the case order"},
            },
            {
                "name": "get_case",
                "description": "Retrieve the current case status, decision, narrative and outcome details.",
                "arguments": {},
            },
            {
                "name": "evaluate_policy_rules",
                "description": "Run the deterministic policy engine in read-only mode.",
                "arguments": {},
            },
            {
                "name": "evaluate_risk",
                "description": "Run the deterministic risk engine and return advisory findings.",
                "arguments": {},
            },
            {
                "name": "get_conversation_history",
                "description": "Retrieve recent conversation messages for this case.",
                "arguments": {"limit": "optional number of messages"},
            },
            {
                "name": "resolve_case",
                "description": "Run the authoritative resolution workflow for an unresolved case.",
                "arguments": {},
            },
            {
                "name": "escalate_to_human",
                "description": "Create or reuse a seller approval request for a high-risk or policy-escalated case.",
                "arguments": {"reason": "optional explanation"},
            },
        ]

    @property
    def tool_declarations(self) -> list[dict[str, Any]]:
        declarations: list[dict[str, Any]] = []
        for tool in self.available_tools():
            name = tool["name"]
            schema_cls = TOOL_INPUT_SCHEMAS.get(name)
            parameters = {"type": "object", "properties": {}, "additionalProperties": False}
            if schema_cls is not None:
                parameters = schema_cls.model_json_schema()
            declarations.append(
                {
                    "name": name,
                    "description": tool["description"],
                    "parameters": parameters,
                }
            )
        return declarations

    def load_conversation_history(
        self,
        db: Session,
        case_id: str,
        limit: int = 20,
    ) -> list[CaseMessage]:
        messages = (
            db.query(CaseMessage)
            .filter(CaseMessage.case_id == case_id)
            .order_by(CaseMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        messages.reverse()
        return messages

    async def execute_tool(
        self,
        db: Session,
        case_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        arguments = arguments or {}
        arguments = validate_tool_arguments(tool_name, arguments)
        case = db.query(Case).filter(Case.id == case_id).first()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        order = db.query(Order).filter(Order.id == case.order_id).first()
        if order is None:
            raise ValueError(f"Order {case.order_id} not found")

        requested_case_id = arguments.get("case_id")
        if requested_case_id is not None and str(requested_case_id) != str(case_id):
            raise ValueError("Tool case_id does not match the current case")

        requested_order_id = arguments.get("order_id")
        if requested_order_id is not None and str(requested_order_id) != str(case.order_id):
            raise ValueError("Tool order_id does not match the authenticated case order")

        if tool_name == "lookup_order":
            return ResolutionTools.lookup_order(db, order.id) or {}

        if tool_name == "lookup_shipment":
            return ResolutionTools.lookup_shipment(db, order.id) or {}

        if tool_name == "get_case":
            return {
                "id": case.id,
                "case_number": case.case_number,
                "status": case.status,
                "decision": case.decision,
                "issue_category": case.issue_category,
                "customer_narrative": case.customer_narrative,
                "outcome_details": case.outcome_details,
                "evidence_urls": case.evidence_urls,
            }

        if tool_name == "evaluate_policy_rules":
            evaluation = PolicyEvaluationService().evaluate_case(db, case, persist=False)
            return evaluation.result.model_dump(mode="json")

        if tool_name == "evaluate_risk":
            result = RiskEvaluationService().evaluate_case(db, case)
            return result.model_dump(mode="json")

        if tool_name == "get_conversation_history":
            limit = int(arguments.get("limit") or 20)
            limit = max(1, min(limit, 100))
            messages = self.load_conversation_history(db, case_id, limit=limit)
            return [
                {
                    "sender_role": message.sender_role,
                    "message": message.message,
                    "created_at": message.created_at.isoformat(),
                }
                for message in messages
            ]

        if tool_name == "resolve_case":
            if case.status in {"resolved", "rejected", "pending_approval"}:
                return {
                    "status": case.status,
                    "decision": case.decision,
                    "message": "Case is already resolved, rejected or pending approval; no new action was executed.",
                }
            outcome = await self.service.resolve_case(db, case.id)
            return {
                "status": outcome.case.status,
                "decision": outcome.case.decision,
                "badge": outcome.badge,
                "evaluation_id": outcome.evaluation_id,
            }

        if tool_name == "escalate_to_human":
            evaluation = PolicyEvaluationService().evaluate_case(db, case, persist=True)
            risk_result = RiskEvaluationService().evaluate_case(db, case)
            high_risk = any(flag.severity == "high" for flag in risk_result.flags)
            if (
                evaluation.result.decision not in {"needs_approval", "manual_review"}
                and not high_risk
            ):
                return {
                    "escalated": False,
                    "reason": "Policy does not require human approval and no high-risk flag was found.",
                }
            approval = ApprovalService(self.service.actions).request_for_evaluation(
                db,
                case=case,
                evaluation=evaluation.result,
                evaluation_id=evaluation.record.id if evaluation.record is not None else None,
            )
            return {
                "escalated": True,
                "approval_id": approval.id,
                "status": approval.status,
            }

        raise ValueError(f"Unknown tool: {tool_name}")

    async def process_case_resolution(
        self,
        case_id: str,
        *,
        db: Session | None = None,
        user_message: str | None = None,
        max_tool_calls: int | None = None,
        enable_tools: bool = True,
    ) -> CaseMessage:
        db = db or self.db
        if db is None:
            raise ValueError("A database session is required")

        history = self.load_conversation_history(db, case_id)
        if user_message:
            last = history[-1] if history else None
            if not (last is not None and last.sender_role == "buyer" and last.message == user_message.strip()):
                history = list(history) + [
                    CaseMessage(
                        case_id=case_id,
                        sender_role="buyer",
                        message=user_message,
                    )
                ]

        tool_executor = None
        if enable_tools:
            async def tool_executor(tool_name: str, arguments: dict[str, Any]) -> Any:
                return await self.execute_tool(db, case_id, tool_name, arguments)

        calls = self.MAX_TOOL_CALLS if max_tool_calls is None else max_tool_calls
        outcome = await self.service.resolve_case(
            db,
            case_id,
            conversation_history=history,
            tool_executor=tool_executor,
            max_tool_calls=calls,
            tool_declarations=self.tool_declarations,
        )
        if outcome.message is None:  # pragma: no cover - persist_message defaults True
            raise RuntimeError("Resolution did not persist an agent message")
        return outcome.message

    async def stream_case_resolution(
        self,
        case_id: str,
        *,
        db: Session | None = None,
        conversation_history: list[CaseMessage] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        db = db or self.db
        if db is None:
            raise ValueError("A database session is required")
        history = conversation_history
        if history is None:
            history = self.load_conversation_history(db, case_id)
        async for item in self.service.stream_case(
            db, case_id, conversation_history=history
        ):
            yield item

    # Backward/alternative names for callers and tests.
    async def process_case(self, *args: Any, **kwargs: Any) -> CaseMessage:
        return await self.process_case_resolution(*args, **kwargs)

    async def run_case_resolution(self, *args: Any, **kwargs: Any) -> CaseMessage:
        return await self.process_case_resolution(*args, **kwargs)

    async def handle_case(self, *args: Any, **kwargs: Any) -> CaseMessage:
        return await self.process_case_resolution(*args, **kwargs)

    async def chat_turn(self, *args: Any, **kwargs: Any) -> CaseMessage:
        return await self.process_case_resolution(*args, **kwargs)

    async def run(self, *args: Any, **kwargs: Any) -> CaseMessage:
        return await self.process_case_resolution(*args, **kwargs)
