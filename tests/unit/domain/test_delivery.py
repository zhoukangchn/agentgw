import pytest

from agentgw.domain.delivery.entities import Delivery, DeliveryStatus


def test_delivery_can_move_from_received_to_routed() -> None:
    delivery = Delivery.create(message_id="msg-1")

    delivery.mark_routed(agent_endpoint_id="agent-1")

    assert delivery.status is DeliveryStatus.ROUTED
    assert delivery.agent_endpoint_id == "agent-1"


def test_delivery_rejects_invalid_transition() -> None:
    delivery = Delivery.create(message_id="msg-1")

    with pytest.raises(ValueError, match="invalid delivery transition"):
        delivery.mark_succeeded("done")


def test_delivery_can_move_from_routed_to_succeeded() -> None:
    delivery = Delivery.create(message_id="msg-1")
    delivery.mark_routed(agent_endpoint_id="agent-1")
    delivery.mark_dispatching()
    delivery.mark_dispatched()
    before_updated_at = delivery.updated_at

    delivery.mark_succeeded("done")

    assert delivery.status is DeliveryStatus.SUCCEEDED
    assert delivery.reply_content == "done"
    assert delivery.updated_at >= before_updated_at


def test_delivery_rejects_invalid_constructor_state() -> None:
    with pytest.raises(ValueError, match="invalid delivery state"):
        Delivery(
            message_id="msg-1",
            agent_endpoint_id="agent-1",
            status=DeliveryStatus.RECEIVED,
        )


def test_delivery_rejects_failed_state_without_endpoint() -> None:
    with pytest.raises(ValueError, match="invalid delivery state"):
        Delivery(
            message_id="msg-1",
            status=DeliveryStatus.FAILED,
            last_error="boom",
        )
