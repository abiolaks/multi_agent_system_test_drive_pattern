"use client";

import { useEffect, useState } from "react";
import { ChatForm } from "@/components/chat-form";
import { EmailConfirmCard } from "@/components/email-confirm-card";
import { ReportView } from "@/components/report-view";
import type { ApiError, AuthIdentity, RunResponse } from "@/lib/types";

type Status = "idle" | "loading" | "error" | "done";

export default function ChatPage() {
  const [identity, setIdentity] = useState<AuthIdentity | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState<RunResponse | null>(null);
  const [emailDismissed, setEmailDismissed] = useState(false);

  useEffect(() => {
    fetch("/api/auth")
      .then((res) => (res.status === 204 ? null : res.json()))
      .then((data: AuthIdentity | null) => setIdentity(data))
      .catch(() => setIdentity(null));
  }, []);

  const handleSubmit = async (question: string) => {
    setStatus("loading");
    setError("");
    setResult(null);
    setEmailDismissed(false);

    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const body = await res.json().catch(() => ({}) as ApiError | RunResponse);
      if (!res.ok) {
        throw new Error((body as ApiError).detail || `HTTP ${res.status}`);
      }
      setResult(body as RunResponse);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setStatus("error");
    }
  };

  return (
    <main>
      <h1>Fabric Data Q&amp;A</h1>
      <p className="identity">{identity ? `Signed in as ${identity.name || identity.email}` : ""}</p>

      <ChatForm onSubmit={handleSubmit} disabled={status === "loading"} />

      {status === "loading" && <p className="loading">Working on it…</p>}
      {status === "error" && <p className="error-banner">{error}</p>}

      {result && (
        <>
          <ReportView report={result.report} />
          {result.email_pending && !emailDismissed && (
            <EmailConfirmCard runId={result.run_id} onDismiss={() => setEmailDismissed(true)} />
          )}
        </>
      )}
    </main>
  );
}
