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
