from __future__ import annotations

import base64
import unittest

from fastapi.testclient import TestClient

from fabric_qa.agent_chat import FakeChatClient
from fabric_qa.api import Adapters, _to_report_out, app, get_adapters
from fabric_qa.fakes import (
    FakeEmailPort,
    FakeFabricPort,
    FakeKnowledgeBasePort,
    FakeSchedulerPort,
    FakeWebSearchPort,
)
from fabric_qa.models import AssetReadings, FabricResult, Report
from fabric_qa.router_agent import RouterOutput


def make_adapters(
    *,
    chat_client: FakeChatClient | None = None,
    fabric: FakeFabricPort | None = None,
    knowledge_base: FakeKnowledgeBasePort | None = None,
    web_search: FakeWebSearchPort | None = None,
    email: FakeEmailPort | None = None,
    scheduler: FakeSchedulerPort | None = None,
) -> Adapters:
    return Adapters(
        chat_client=chat_client
        if chat_client is not None
        else FakeChatClient(
            response_text="fake summary",
            structured_values={RouterOutput: RouterOutput(topic="general_data")},
        ),
        fabric=fabric if fabric is not None else FakeFabricPort(FabricResult(data={"revenue": [100, 112]})),
        knowledge_base=knowledge_base if knowledge_base is not None else FakeKnowledgeBasePort(),
        web_search=web_search if web_search is not None else FakeWebSearchPort(),
        email=email if email is not None else FakeEmailPort(),
        scheduler=scheduler if scheduler is not None else FakeSchedulerPort(),
    )


class TestApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.addCleanup(app.dependency_overrides.clear)

    def override(self, adapters: Adapters) -> None:
        app.dependency_overrides[get_adapters] = lambda: adapters


class TestRun(TestApiTestCase):
    def test_returns_report_and_a_run_id(self) -> None:
        self.override(make_adapters())

        response = self.client.post("/api/run", json={"question": "how did revenue trend?"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["report"]["summary"], "fake summary")
        self.assertTrue(body["run_id"])
        self.assertTrue(body["email_pending"])  # ADR 0009: every report is drafted

    def test_blank_question_is_rejected(self) -> None:
        self.override(make_adapters())

        response = self.client.post("/api/run", json={"question": ""})

        self.assertEqual(response.status_code, 422)

    def test_workflow_error_surfaces_as_500(self) -> None:
        # asset_health routes fetch_readings deterministically (unlike
        # general_data's fetch, which is an LLM tool call FakeChatClient
        # never chooses to invoke) - the reliable way to force ask() to
        # raise through a fake
        class BoomFabricPort(FakeFabricPort):
            def fetch_readings(self, asset_id: str) -> AssetReadings:
                raise RuntimeError("fabric is down")

        chat_client = FakeChatClient(
            structured_values={RouterOutput: RouterOutput(topic="asset_health", asset_id="ENG-001")},
        )
        self.override(make_adapters(chat_client=chat_client, fabric=BoomFabricPort()))

        response = self.client.post("/api/run", json={"question": "what is the health of ENG-001?"})

        self.assertEqual(response.status_code, 500)
        self.assertIn("fabric is down", response.json()["detail"])


class TestToReportOut(unittest.TestCase):
    def test_images_are_base64_encoded(self) -> None:
        chart = b"fake-chart-png-bytes"
        report = Report(summary="s", images=[chart])

        report_out = _to_report_out(report)

        self.assertEqual(base64.b64decode(report_out.images[0]), chart)


class TestMailConfirmAndCancel(TestApiTestCase):
    def test_confirm_sends_the_pending_draft(self) -> None:
        email = FakeEmailPort()
        self.override(make_adapters(email=email))
        run_id = self.client.post("/api/run", json={"question": "q"}).json()["run_id"]

        response = self.client.post("/api/mail/confirm", json={"run_id": run_id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sent": True})
        self.assertEqual(len(email.sent), 1)

    def test_confirm_twice_404s_the_second_time(self) -> None:
        email = FakeEmailPort()
        self.override(make_adapters(email=email))
        run_id = self.client.post("/api/run", json={"question": "q"}).json()["run_id"]
        self.client.post("/api/mail/confirm", json={"run_id": run_id})

        response = self.client.post("/api/mail/confirm", json={"run_id": run_id})

        self.assertEqual(response.status_code, 404)

    def test_confirm_unknown_run_id_404s(self) -> None:
        self.override(make_adapters())

        response = self.client.post("/api/mail/confirm", json={"run_id": "no-such-run"})

        self.assertEqual(response.status_code, 404)

    def test_cancel_discards_the_draft_without_sending(self) -> None:
        email = FakeEmailPort()
        self.override(make_adapters(email=email))
        run_id = self.client.post("/api/run", json={"question": "q"}).json()["run_id"]

        response = self.client.post("/api/mail/cancel", json={"run_id": run_id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sent": False})
        self.assertEqual(email.sent, [])

        # cancelling again 404s - the draft is gone either way
        self.assertEqual(self.client.post("/api/mail/cancel", json={"run_id": run_id}).status_code, 404)


class TestAuth(TestApiTestCase):
    def test_returns_204_when_no_easy_auth_headers_present(self) -> None:
        response = self.client.get("/api/auth")

        self.assertEqual(response.status_code, 204)

    def test_decodes_the_client_principal_header(self) -> None:
        principal = base64.b64encode(
            b'{"claims": [{"typ": "name", "val": "Ada Lovelace"}, '
            b'{"typ": "preferred_username", "val": "ada@example.com"}]}'
        ).decode("ascii")

        response = self.client.get("/api/auth", headers={"x-ms-client-principal": principal})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"name": "Ada Lovelace", "email": "ada@example.com"})

    def test_falls_back_to_principal_name_header_on_malformed_principal(self) -> None:
        response = self.client.get(
            "/api/auth",
            headers={"x-ms-client-principal": "not-valid-base64-json!!", "x-ms-client-principal-name": "ada@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"name": "ada@example.com", "email": "ada@example.com"})


if __name__ == "__main__":
    unittest.main()
