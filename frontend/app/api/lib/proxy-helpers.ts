/**
 * Shared utilities for API route proxy handlers. Every browser-facing
 * route under app/api/* forwards to the FastAPI backend through these —
 * the browser never calls the backend directly.
 */

import { NextResponse } from "next/server";

export const BACKEND = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

const DEFAULT_TIMEOUT_MS = 30_000;

interface SafeFetchResult {
  response?: Response;
  error?: NextResponse;
}

/**
 * Fetch with an AbortController timeout. Returns the upstream Response
 * on success, or a pre-built NextResponse error on failure.
 */
export async function safeFetch(
  url: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<SafeFetchResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    return { response };
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return {
        error: NextResponse.json({ detail: "Backend request timed out" }, { status: 504 }),
      };
    }
    const message = err instanceof Error ? err.message : "Unknown error";
    return {
      error: NextResponse.json({ detail: `Backend unreachable: ${message}` }, { status: 502 }),
    };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Safely parse JSON from an upstream response.
 */
export async function safeJson(upstream: Response): Promise<{ data?: unknown; error?: NextResponse }> {
  try {
    const data = await upstream.json();
    return { data };
  } catch {
    return {
      error: NextResponse.json({ detail: "Invalid JSON from backend" }, { status: 502 }),
    };
  }
}

/**
 * One-shot proxy: fetch + parse + forward as a NextResponse with the
 * upstream's status code preserved.
 */
export async function proxyJson(url: string, init?: RequestInit, timeoutMs?: number): Promise<NextResponse> {
  const { response, error } = await safeFetch(url, init, timeoutMs);
  if (error) return error;

  const upstream = response!;
  const { data, error: jsonErr } = await safeJson(upstream);
  if (jsonErr) return jsonErr;

  return NextResponse.json(data, { status: upstream.status });
}
