"""Interactive entrypoint wiring all real adapters into fabric_qa.workflow.ask().

Requires vLLM serving locally (see start_vllm_server.sh) and the KB_*/
FABRIC_AGENT_*/WEB_SEARCH_*/EMAIL_* env vars in .env (see .env.example
and docs/kb-setup.md).

Usage:
    uv run python main.py
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from fabric_qa.adapters.azure_search import AzureSearchKnowledgeBasePort
from fabric_qa.adapters.fabric_agent import FabricDataAgentPort
from fabric_qa.adapters.graph_email import GraphEmailPort
from fabric_qa.adapters.llm_client import build_vllm_chat_client
from fabric_qa.adapters.scheduler import APSchedulerPort
from fabric_qa.adapters.web_search import BraveWebSearchPort
from fabric_qa.models import EmailDraft, Report
from fabric_qa.workflow import ask

load_dotenv()


async def main() -> None:
    chat_client = build_vllm_chat_client()
    fabric = FabricDataAgentPort.from_env()
    knowledge_base = AzureSearchKnowledgeBasePort.from_env()
    web_search = BraveWebSearchPort.from_env()
    email = GraphEmailPort.from_env()
    scheduler = APSchedulerPort.from_env()

    print("Fabric Data Q&A - type a question, or 'exit' to quit.")
    while True:
        try:
            question = input("\n> ").strip()
        except EOFError:
            break
        if not question or question.lower() in {"exit", "quit"}:
            break

        # captures the EmailDraft ask() produces internally - ask() only
        # returns the Report, so this is how the caller gets a handle on
        # the draft to act on the ADR 0009 approval gate below
        drafted: list[EmailDraft] = []

        def email_draft(report: Report) -> EmailDraft:
            draft = email.draft(report)
            drafted.append(draft)
            return draft

        try:
            report = await ask(
                question,
                chat_client=chat_client,
                fetch=fabric.fetch,
                fetch_readings=fabric.fetch_readings,
                fetch_maintenance_history=fabric.fetch_maintenance_history,
                retrieve_guidance=knowledge_base.retrieve,
                web_search=web_search.search,
                email_draft=email_draft,
                schedule=scheduler.schedule,
            )
        except Exception as exc:  # surfaced to the operator, loop continues
            print(f"Error: {exc}")
            continue

        print(f"\n{report.summary}")

        # ADR 0009: drafting is automatic, sending never is
        if drafted:
            approve = input("\nSend this email now? [y/N] ").strip().lower()
            if approve == "y":
                email.send(drafted[-1])
                print("Sent.")
            else:
                print("Not sent (still drafted).")


if __name__ == "__main__":
    asyncio.run(main())
