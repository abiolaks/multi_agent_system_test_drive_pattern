/**
 * Proxy for POST /api/mail/cancel — discards a drafted email without
 * sending it.
 */

import { NextRequest, NextResponse } from "next/server";
import { BACKEND, proxyJson } from "../../lib/proxy-helpers";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  let payload: Record<string, unknown>;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ detail: "Request body must be valid JSON" }, { status: 400 });
  }

  if (typeof payload.run_id !== "string" || payload.run_id.trim() === "") {
    return NextResponse.json({ detail: "run_id must be a non-empty string" }, { status: 400 });
  }

  return proxyJson(`${BACKEND}/api/mail/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: payload.run_id }),
  });
}
