from __future__ import annotations

import unittest

from msgraph.generated.models.message import Message

from fabric_qa.adapters.graph_email import GraphEmailPort
from fabric_qa.models import Report


class FakeMessagesClient:
    def __init__(self, created_message_id: str = "msg-1") -> None:
        self._created_message_id = created_message_id
        self.draft_calls: list[tuple[str, Message]] = []
        self.send_calls: list[tuple[str, str]] = []

    async def create_draft(self, user_upn: str, message: Message) -> Message:
        self.draft_calls.append((user_upn, message))
        message.id = self._created_message_id
        return message

    async def send(self, user_upn: str, message_id: str) -> None:
        self.send_calls.append((user_upn, message_id))


class TestGraphEmailPort(unittest.TestCase):
    def test_draft_creates_a_message_addressed_to_the_configured_recipient(self) -> None:
        messages = FakeMessagesClient()
        port = GraphEmailPort(messages=messages, sender_upn="agent@arik-air.com", recipient="ops@arik-air.com")
        report = Report(summary="ENG-001 EGT margin has entered alarm range.")

        draft = port.draft(report)

        self.assertEqual(len(messages.draft_calls), 1)
        user_upn, message = messages.draft_calls[0]
        self.assertEqual(user_upn, "agent@arik-air.com")
        assert message.to_recipients is not None
        recipient_address = message.to_recipients[0].email_address
        assert recipient_address is not None
        self.assertEqual(recipient_address.address, "ops@arik-air.com")
        assert message.body is not None
        self.assertEqual(message.body.content, report.summary)
        self.assertIs(draft.report, report)

    def test_draft_never_sends(self) -> None:
        messages = FakeMessagesClient()
        port = GraphEmailPort(messages=messages, sender_upn="agent@arik-air.com", recipient="ops@arik-air.com")

        draft = port.draft(Report(summary="s"))

        self.assertFalse(draft.sent)
        self.assertEqual(messages.send_calls, [])

    def test_draft_stashes_the_graph_message_id_as_provider_ref(self) -> None:
        messages = FakeMessagesClient(created_message_id="msg-42")
        port = GraphEmailPort(messages=messages, sender_upn="agent@arik-air.com", recipient="ops@arik-air.com")

        draft = port.draft(Report(summary="s"))

        self.assertEqual(draft.provider_ref, "msg-42")

    def test_send_sends_the_previously_drafted_message_and_marks_it_sent(self) -> None:
        messages = FakeMessagesClient(created_message_id="msg-7")
        port = GraphEmailPort(messages=messages, sender_upn="agent@arik-air.com", recipient="ops@arik-air.com")
        draft = port.draft(Report(summary="s"))

        port.send(draft)

        self.assertTrue(draft.sent)
        self.assertEqual(messages.send_calls, [("agent@arik-air.com", "msg-7")])

    def test_send_refuses_a_draft_that_was_never_created_by_this_adapter(self) -> None:
        port = GraphEmailPort(
            messages=FakeMessagesClient(), sender_upn="agent@arik-air.com", recipient="ops@arik-air.com"
        )
        orphan_draft = port.draft(Report(summary="s"))
        orphan_draft.provider_ref = None  # simulate a draft with no known Graph message id

        with self.assertRaises(ValueError):
            port.send(orphan_draft)

    def test_email_subject_is_derived_from_the_first_line_of_the_summary(self) -> None:
        messages = FakeMessagesClient()
        port = GraphEmailPort(messages=messages, sender_upn="agent@arik-air.com", recipient="ops@arik-air.com")
        report = Report(summary="ENG-001 EGT margin has entered alarm range.\nMore detail below.")

        port.draft(report)

        _user_upn, message = messages.draft_calls[0]
        self.assertEqual(message.subject, "ENG-001 EGT margin has entered alarm range.")


if __name__ == "__main__":
    unittest.main()
