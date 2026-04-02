class WeLinkClient:
    def __init__(self):
        self.sent_group_messages: list[tuple[str, str]] = []

    async def send_group_message(self, group_id: str, content: str) -> None:
        self.sent_group_messages.append((group_id, content))
