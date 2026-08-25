"use client";

import { useState } from "react";
import type { ApiError, MailActionResponse } from "@/lib/types";

interface EmailConfirmCardProps {
  runId: string;
  onDismiss: () => void;
}

type CardState = "idle" | "sending" | "sent" | "cancelled" | "error";

export function EmailConfirmCard({ runId, onDismiss }: EmailConfirmCardProps) {
  const [state, setState] = useState<CardState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const post = async (path: string): Promise<MailActionResponse | null> => {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId }),
    });
    const body = await res.json().catch(() => ({}) as ApiError | MailActionResponse);
    if (!res.ok) {
      throw new Error((body as ApiError).detail || `HTTP ${res.status}`);
    }
    return body as MailActionResponse;
  };

  const handleConfirm = async () => {
    setState("sending");
    try {
      await post("/api/mail/confirm");
      setState("sent");
      setTimeout(onDismiss, 2500);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Could not reach the backend.");
      setState("error");
    }
  };

  const handleCancel = async () => {
    setState("cancelled");
    await post("/api/mail/cancel").catch(() => {});
    setTimeout(onDismiss, 1000);
  };

  return (
    <div className="email-confirm-card">
      <div className="email-confirm-header">This report was drafted as an email — send it?</div>

      {state === "sent" && <p className="email-confirm-status email-confirm-status-sent">Email sent.</p>}
      {state === "cancelled" && <p className="email-confirm-status email-confirm-status-cancelled">Not sent.</p>}
      {state === "error" && <p className="email-confirm-status email-confirm-status-error">Failed: {errorMsg}</p>}

      {state === "idle" && (
        <div className="email-confirm-actions">
          <button type="button" className="secondary-button" onClick={handleCancel}>
            Don&rsquo;t send
          </button>
          <button type="button" className="action-button" onClick={handleConfirm}>
            Send email
          </button>
        </div>
      )}

      {state === "sending" && (
        <div className="email-confirm-actions">
          <button type="button" className="action-button" disabled>
            Sending…
          </button>
        </div>
      )}
    </div>
  );
}
