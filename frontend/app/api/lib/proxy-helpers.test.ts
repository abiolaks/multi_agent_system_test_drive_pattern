import { afterEach, describe, expect, it, vi } from "vitest";
import { proxyJson, safeFetch, safeJson } from "./proxy-helpers";

describe("safeFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the upstream response on success", async () => {
    const upstream = new Response("{}", { status: 200 });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => upstream),
    );

    const { response, error } = await safeFetch("http://backend.test/x");

    expect(error).toBeUndefined();
    expect(response).toBe(upstream);
  });

  it("returns a 502 when the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("ECONNREFUSED");
      }),
    );

    const { error, response } = await safeFetch("http://backend.test/x");

    expect(response).toBeUndefined();
    expect(error?.status).toBe(502);
    const body = await error!.json();
    expect(body.detail).toContain("ECONNREFUSED");
  });

  it("returns a 504 when the request times out", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) => {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        });
      }),
    );

    const { error, response } = await safeFetch("http://backend.test/x", undefined, 10);

    expect(response).toBeUndefined();
    expect(error?.status).toBe(504);
  });
});

describe("safeJson", () => {
  it("parses a valid JSON body", async () => {
    const { data, error } = await safeJson(new Response('{"ok": true}'));
    expect(error).toBeUndefined();
    expect(data).toEqual({ ok: true });
  });

  it("returns a 502 for a non-JSON body", async () => {
    const { data, error } = await safeJson(new Response("not json"));
    expect(data).toBeUndefined();
    expect(error?.status).toBe(502);
  });
});

describe("proxyJson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("preserves the upstream status code and body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "No pending email draft" }), { status: 404 })),
    );

    const result = await proxyJson("http://backend.test/api/mail/confirm", { method: "POST" });

    expect(result.status).toBe(404);
    const body = await result.json();
    expect(body).toEqual({ detail: "No pending email draft" });
  });
});
