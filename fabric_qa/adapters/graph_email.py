from __future__ import annotations

import os
from typing import Protocol

from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient

from fabric_qa.adapters.async_bridge import run_sync
from fabric_qa.models import EmailDraft, Report

GRAPH_SCOPE = "https://graph.microsoft.com/.default"


class MessagesClient(Protocol):
    async def create_draft(self, user_upn: str, message: Message) -> Message: ...
    async def send(self, user_upn: str, message_id: str) -> None: ...


class GraphMessagesClient:
    def __init__(self, client: GraphServiceClient) -> None:
        self._client = client

    async def create_draft(self, user_upn: str, message: Message) -> Message:
        created = await self._client.users.by_user_id(user_upn).messages.post(message)
        if created is None or created.id is None:
            raise RuntimeError("Graph did not return a message id for the created draft")
        return created

    async def send(self, user_upn: str, message_id: str) -> None:
        await self._client.users.by_user_id(user_upn).messages.by_message_id(message_id).send.post()


class GraphEmailPort:
    def __init__(self, messages: MessagesClient, sender_upn: str, recipient: str) -> None:
        self._messages = messages
        self._sender_upn = sender_upn
        self._recipient = recipient

    @classmethod
    def from_env(cls) -> "GraphEmailPort":
        credential = ClientSecretCredential(
            tenant_id=os.environ["EMAIL_TENANT_ID"],
            client_id=os.environ["EMAIL_CLIENT_ID"],
            client_secret=os.environ["EMAIL_CLIENT_SECRET"],
        )
        client = GraphServiceClient(credentials=credential, scopes=[GRAPH_SCOPE])
        return cls(
            messages=GraphMessagesClient(client),
            sender_upn=os.environ["EMAIL_SENDER_UPN"],
            recipient=os.environ["EMAIL_RECIPIENT"],
        )

    def draft(self, report: Report) -> EmailDraft:
        message = Message(
            subject=_subject_for(report),
            body=ItemBody(content_type=BodyType.Text, content=report.summary),
            to_recipients=[Recipient(email_address=EmailAddress(address=self._recipient))],
        )
        created = run_sync(self._messages.create_draft(self._sender_upn, message))
        return EmailDraft(report=report, provider_ref=created.id)

    def send(self, draft: EmailDraft) -> None:
        if draft.provider_ref is None:
            raise ValueError(
                "cannot send an EmailDraft with no provider_ref - was it created by this adapter's draft()?"
            )
        run_sync(self._messages.send(self._sender_upn, draft.provider_ref))
        draft.sent = True


def _subject_for(report: Report) -> str:
    first_line = report.summary.splitlines()[0] if report.summary else "Fabric Data Q&A Report"
    return first_line[:78]
