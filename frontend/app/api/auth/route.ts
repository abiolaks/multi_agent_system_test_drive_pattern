/**
 * Returns the current user identity from ACA Easy Auth headers.
 *
 * Decoded here, in the frontend, rather than proxied to the FastAPI
 * backend: only this container is public-facing behind Easy Auth (the
 * backend is proxied through app/api/* and never reached directly by
 * the browser), so this is the only place these headers ever land. See
 * docs/adr/0011-easy-auth-on-aca.md.
 *
 * Returns 204 when not behind Easy Auth (local dev).
 */

import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

interface ClientPrincipal {
  claims: Array<{ typ: string; val: string }>;
}

export async function GET(request: NextRequest) {
  const principalHeader = request.headers.get("x-ms-client-principal");
  const principalName = request.headers.get("x-ms-client-principal-name");

  if (!principalHeader) {
    return new NextResponse(null, { status: 204 });
  }

  try {
    const decoded = Buffer.from(principalHeader, "base64").toString("utf-8");
    const principal: ClientPrincipal = JSON.parse(decoded);
    const claims = principal.claims ?? [];

    const name =
      claims.find((c) => c.typ === "name")?.val ??
      claims.find((c) => c.typ === "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")?.val ??
      "";
    const email =
      claims.find((c) => c.typ === "preferred_username")?.val ??
      claims.find((c) => c.typ === "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")?.val ??
      principalName ??
      "";

    return NextResponse.json({ name: name || email, email });
  } catch {
    return NextResponse.json({ name: principalName ?? "User", email: principalName ?? "" });
  }
}
