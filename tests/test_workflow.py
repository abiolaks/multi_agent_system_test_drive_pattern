from __future__ import annotations

import unittest

from fabric_qa.agent_chat import FakeChatClient
from fabric_qa.diagnosis import DiagnosisOutput, RecommendationOutput
from fabric_qa.models import AssetReadings, EmailDraft, FabricResult, MaintenanceRecord, Reading, Report
from fabric_qa.router_agent import RouterOutput
from fabric_qa.workflow import ask


def unused_fetch_readings(asset_id: str) -> AssetReadings:
    raise AssertionError(f"fetch_readings should not have been called for asset_id={asset_id!r}")


def unused_fetch(question: str) -> FabricResult:
    raise AssertionError(f"fetch should not have been called for question={question!r}")


def unused_fetch_maintenance_history(asset_id: str) -> list[MaintenanceRecord]:
    raise AssertionError(f"fetch_maintenance_history should not have been called for asset_id={asset_id!r}")


def unused_retrieve_guidance(asset_model: str) -> str:
    raise AssertionError(f"retrieve_guidance should not have been called for asset_model={asset_model!r}")


def unused_web_search(query: str) -> str:
    raise AssertionError(f"web_search should not have been called for query={query!r}")


def unused_schedule(interval: str, callback) -> None:
    raise AssertionError(f"schedule should not have been called for interval={interval!r}")


def make_diagnosis_output(
    fault_signature: str = "f", next_step: str = "n", citation: str = "cite"
) -> DiagnosisOutput:
    return DiagnosisOutput(
        summary="s",
        what_data_shows="d",
        what_guidance_says="g",
        combined_finding="c",
        recommendation=RecommendationOutput(fault_signature=fault_signature, next_step=next_step, citation=citation),
        caveats="cav",
    )


class TestGeneralDataFlow(unittest.IsolatedAsyncioTestCase):
    async def test_returns_report_with_llm_summary(self) -> None:
        chat_client = FakeChatClient(
            response_text="Revenue rose 12% quarter over quarter.",
            structured_values={RouterOutput: RouterOutput(topic="general_data")},
        )
        drafted: list[EmailDraft] = []

        def fetch(question: str) -> FabricResult:
            return FabricResult(data={"revenue": [100, 112]})

        def email_draft(report: Report) -> EmailDraft:
            draft = EmailDraft(report=report)
            drafted.append(draft)
            return draft

        report = await ask(
            "how did revenue trend this quarter?",
            chat_client=chat_client,
            fetch=fetch,
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=email_draft,
            schedule=unused_schedule,
        )

        self.assertEqual(report.summary, "Revenue rose 12% quarter over quarter.")
        self.assertEqual(len(drafted), 1)
        self.assertIs(drafted[0].report, report)
        self.assertFalse(drafted[0].sent)

    async def test_images_are_empty_when_the_fetch_tool_is_never_invoked(self) -> None:
        chat_client = FakeChatClient(
            response_text="General answer, no data needed.",
            structured_values={RouterOutput: RouterOutput(topic="general_data")},
        )

        report = await ask(
            "what day is it?",
            chat_client=chat_client,
            fetch=lambda q: FabricResult(data="unused"),
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=unused_schedule,
        )

        self.assertEqual(report.images, [])


class TestAssetHealthNormalFlow(unittest.IsolatedAsyncioTestCase):
    async def test_normal_only_returns_verdicts_narrated_by_the_llm_no_diagnosis(self) -> None:
        chat_client = FakeChatClient(
            response_text="Everything looks normal.",
            structured_values={RouterOutput: RouterOutput(topic="asset_health", asset_id="ENG-002")},
        )
        readings = AssetReadings(
            asset_id="ENG-002",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],  # Normal
        )
        drafted: list[EmailDraft] = []

        def email_draft(report: Report) -> EmailDraft:
            draft = EmailDraft(report=report)
            drafted.append(draft)
            return draft

        report = await ask(
            "what is the health status of ENG-002?",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=lambda asset_id: readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=email_draft,
            schedule=unused_schedule,
        )

        self.assertEqual(report.summary, "Everything looks normal.")
        self.assertEqual(len(report.verdicts), 1)
        self.assertEqual(report.verdicts[0].parameter, "egt_margin_c")
        self.assertEqual(report.verdicts[0].health, "Normal")
        self.assertIsNone(report.diagnosis)
        self.assertEqual(len(drafted), 1)
        self.assertFalse(drafted[0].sent)

    async def test_a_general_data_question_never_touches_fetch_readings(self) -> None:
        chat_client = FakeChatClient(
            response_text="s", structured_values={RouterOutput: RouterOutput(topic="general_data")}
        )

        report = await ask(
            "how did revenue trend?",
            chat_client=chat_client,
            fetch=lambda q: FabricResult(data="d"),
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=unused_schedule,
        )

        self.assertEqual(report.verdicts, [])

    async def test_an_asset_health_question_never_touches_the_fabric_fetch_tool(self) -> None:
        chat_client = FakeChatClient(
            response_text="s",
            structured_values={RouterOutput: RouterOutput(topic="asset_health", asset_id="ENG-002")},
        )
        readings = AssetReadings(
            asset_id="ENG-002",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],  # Normal
        )

        report = await ask(
            "what is the health status of ENG-002?",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=lambda asset_id: readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=unused_schedule,
        )

        self.assertEqual(report.images, [])


class TestAssetHealthDiagnosisFlow(unittest.IsolatedAsyncioTestCase):
    async def test_abnormal_verdict_produces_a_full_diagnosis_with_citation(self) -> None:
        diagnosis_output = DiagnosisOutput(
            summary="ENG-001 EGT margin has entered alarm range.",
            what_data_shows="EGT margin is 14.0C, below the 20C alarm floor.",
            what_guidance_says="CFM56-7B26 FIM 72-31: margin erosion indicates hot-section wear.",
            combined_finding="Hot-section erosion is the probable cause.",
            recommendation=RecommendationOutput(
                fault_signature="Hot-section erosion",
                next_step="Borescope inspection within 14 days per task 72-31-00.",
                citation="CFM56-7B26 FIM Section 72-31",
            ),
            caveats="Verify compressor wash history before confirming hot-section wear.",
        )
        chat_client = FakeChatClient(
            structured_values={
                RouterOutput: RouterOutput(topic="asset_health", asset_id="ENG-001"),
                DiagnosisOutput: diagnosis_output,
            },
        )
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=14.0)],  # Alarm
        )
        kb_calls: list[str] = []

        def retrieve_guidance(asset_model: str) -> str:
            kb_calls.append(asset_model)
            return "<CFM56-7B26 FIM text>"

        report = await ask(
            "what is the health status of ENG-001?",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=lambda asset_id: readings,
            fetch_maintenance_history=lambda asset_id: [],
            retrieve_guidance=retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=unused_schedule,
        )

        self.assertEqual(report.summary, diagnosis_output.summary)
        self.assertEqual(len(report.verdicts), 1)
        self.assertEqual(report.verdicts[0].health, "Alarm")
        assert report.diagnosis is not None
        self.assertEqual(report.diagnosis.recommendation.citation, "CFM56-7B26 FIM Section 72-31")

    async def test_recurrence_after_prior_balance_is_escalated_not_re_recommended(self) -> None:
        # ENG-003's N2 vibration returning after the fan trim balance in
        # maintenance_history.csv (per the GEnx-1B FIM's escalation
        # guidance) - proof the maintenance history genuinely reaches the
        # Diagnosis Agent's prompt, not that the fake LLM reasons about it
        prior_balance = [
            MaintenanceRecord(
                work_order_id="WO-1003",
                date="2026-03-08",
                finding="Fan blade balancing performed after N2 vibration advisory",
                parts_replaced="balance weights",
            ),
        ]
        escalated_diagnosis = DiagnosisOutput(
            summary="ENG-003 N2 vibration has recurred and is now in alarm range.",
            what_data_shows="N2 vibration is 4.9 IPS, above the 4.0 IPS alarm ceiling.",
            what_guidance_says="GEnx-1B FIM 72-61: vibration recurring after a prior trim "
            "balance is a mechanical-fault signature (bearing wear).",
            combined_finding="Recurrence after WO-1003's trim balance indicates bearing wear.",
            recommendation=RecommendationOutput(
                fault_signature="Bearing wear (recurrence after balance)",
                next_step="Remove and inspect fan module bearings per task 72-61-20.",
                citation="GEnx-1B FIM Section 72-61",
            ),
            caveats="Cross-check against the redundant accelerometer.",
        )
        chat_client = FakeChatClient(
            structured_values={
                RouterOutput: RouterOutput(topic="asset_health", asset_id="ENG-003"),
                DiagnosisOutput: escalated_diagnosis,
            },
        )
        readings = AssetReadings(
            asset_id="ENG-003",
            asset_model="GEnx-1B",
            readings=[Reading(parameter="vibration_n2_ips", value=4.9)],  # Alarm
        )
        history_calls: list[str] = []

        def fetch_maintenance_history(asset_id: str) -> list[MaintenanceRecord]:
            history_calls.append(asset_id)
            return prior_balance

        report = await ask(
            "what is the health status of ENG-003?",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=lambda asset_id: readings,
            fetch_maintenance_history=fetch_maintenance_history,
            retrieve_guidance=lambda asset_model: "<GEnx-1B FIM text>",
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=unused_schedule,
        )

        # the orchestrator must actually hand the prior maintenance history
        # to the Diagnosis Agent - without it, no diagnosis step could ever
        # distinguish first-occurrence from recurrence
        self.assertEqual(history_calls, ["ENG-003"])
        assert report.diagnosis is not None
        self.assertNotIn("trim balance", report.diagnosis.recommendation.next_step.lower())
        self.assertEqual(report.diagnosis.recommendation.fault_signature, "Bearing wear (recurrence after balance)")

    async def test_web_search_guardrail_holds_through_the_full_workflow(self) -> None:
        # the question itself names the asset - the realistic leak vector
        # this guardrail exists to catch
        search_calls: list[str] = []

        def web_search(query: str) -> str:
            search_calls.append(query)
            return "search result"

        chat_client = FakeChatClient(
            structured_values={
                RouterOutput: RouterOutput(topic="asset_health", asset_id="ENG-003"),
                DiagnosisOutput: make_diagnosis_output(),
            },
        )
        readings = AssetReadings(
            asset_id="ENG-003",
            asset_model="GEnx-1B",
            readings=[Reading(parameter="vibration_n2_ips", value=4.9)],  # Alarm
        )

        await ask(
            "what is the health status of ENG-003?",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=lambda asset_id: readings,
            fetch_maintenance_history=lambda asset_id: [],
            retrieve_guidance=lambda asset_model: "guidance",
            web_search=web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=unused_schedule,
        )

        # not every test run necessarily calls the tool (the fake LLM never
        # genuinely decides to) - this just proves that *if* it's wired in
        # and called, sanitize_query has already run (see test_diagnosis.py
        # for the direct, unconditional guardrail proof)
        for query in search_calls:
            self.assertNotIn("ENG-003", query)
            self.assertNotIn("4.9", query)


if __name__ == "__main__":
    unittest.main()
