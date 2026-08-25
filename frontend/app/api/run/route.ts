/**
 * Proxy for POST /api/run — forwards a question to the FastAPI backend
 * and waits for the completed Report (no streaming yet, ADR 0012).
 */

import { NextRequest, NextResponse } from "next/server";
import { BACKEND, proxyJson } from "../lib/proxy-helpers";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  let payload: Record<string, unknown>;
  try {
    payload = await request.json();
    if (payload === null || Array.isArray(payload) || typeof payload !== "object") {
      throw new Error("Invalid payload");
    }
  } catch {
    return NextResponse.json({ detail: "Request body must be valid JSON" }, { status: 400 });
  }

  if (typeof payload.question !== "string" || payload.question.trim() === "") {
    return NextResponse.json({ detail: "question must be a non-empty string" }, { status: 400 });
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const principalName = request.headers.get("x-ms-client-principal-name");
  if (principalName) {
    headers["X-MS-CLIENT-PRINCIPAL-NAME"] = principalName;
  }

  // a run can take a while - the workflow has no progress events to
  // report yet (ADR 0012), so the whole request just blocks
  return proxyJson(
    `${BACKEND}/api/run`,
    { method: "POST", headers, body: JSON.stringify({ question: payload.question }) },
    120_000,
  );
}
