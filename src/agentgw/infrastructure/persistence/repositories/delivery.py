from uuid import uuid4

from agentgw.domain.delivery.entities import Delivery, DeliveryStatus
from agentgw.domain.delivery.repositories import DeliveryRepository
from agentgw.infrastructure.persistence.base import SessionLocal, initialize_schema
from agentgw.infrastructure.persistence.models import DeliveryModel


class SqlAlchemyDeliveryRepository(DeliveryRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        initialize_schema()

    async def save(self, delivery: Delivery) -> Delivery:
        with self._session_factory() as session:
            if delivery.delivery_id is None:
                delivery.delivery_id = uuid4().hex

            row = session.get(DeliveryModel, delivery.delivery_id)
            if row is None:
                row = DeliveryModel(delivery_id=delivery.delivery_id, message_id=delivery.message_id)

            row.message_id = delivery.message_id
            row.agent_endpoint_id = delivery.agent_endpoint_id
            row.status = delivery.status.value
            row.attempt_count = delivery.attempt_count
            row.last_error = delivery.last_error
            row.reply_content = delivery.reply_content
            row.created_at = delivery.created_at
            row.updated_at = delivery.updated_at
            session.add(row)
            session.commit()

            return Delivery(
                delivery_id=row.delivery_id,
                message_id=row.message_id,
                agent_endpoint_id=row.agent_endpoint_id,
                status=DeliveryStatus(row.status),
                attempt_count=row.attempt_count,
                last_error=row.last_error,
                reply_content=row.reply_content,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    async def get_by_id(self, delivery_id: str) -> Delivery:
        with self._session_factory() as session:
            row = session.get(DeliveryModel, delivery_id)
            if row is None:
                raise LookupError(f"missing delivery: {delivery_id}")
            return Delivery(
                delivery_id=row.delivery_id,
                message_id=row.message_id,
                agent_endpoint_id=row.agent_endpoint_id,
                status=DeliveryStatus(row.status),
                attempt_count=row.attempt_count,
                last_error=row.last_error,
                reply_content=row.reply_content,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    async def list_pending(self, limit: int = 100) -> list[Delivery]:
        with self._session_factory() as session:
            rows = (
                session.query(DeliveryModel)
                .filter(
                    DeliveryModel.status.in_(
                        [
                            DeliveryStatus.RECEIVED.value,
                            DeliveryStatus.ROUTED.value,
                            DeliveryStatus.DISPATCHING.value,
                            DeliveryStatus.DISPATCHED.value,
                            DeliveryStatus.REPLYING.value,
                        ]
                    )
                )
                .limit(limit)
                .all()
            )
            return [
                Delivery(
                    delivery_id=row.delivery_id,
                    message_id=row.message_id,
                    agent_endpoint_id=row.agent_endpoint_id,
                    status=DeliveryStatus(row.status),
                    attempt_count=row.attempt_count,
                    last_error=row.last_error,
                    reply_content=row.reply_content,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]
