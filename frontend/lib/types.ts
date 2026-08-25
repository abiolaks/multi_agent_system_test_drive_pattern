/**
 * Mirrors the Pydantic response models in fabric_qa/api.py. Keep in sync
 * by hand — no shared schema generation exists yet (v1 scope, ADR 0012).
 */

export interface Verdict {
  parameter: string;
  value: number;
  health: string;
}

export interface Recommendation {
  fault_signature: string;
  next_step: string;
  citation: string;
}

export interface Diagnosis {
  summary: string;
  what_data_shows: string;
  what_guidance_says: string;
  combined_finding: string;
  recommendation: Recommendation;
  caveats: string;
}

export interface Report {
  summary: string;
  images: string[]; // base64-encoded
  verdicts: Verdict[];
  diagnosis: Diagnosis | null;
}

export interface RunResponse {
  run_id: string;
  report: Report;
  email_pending: boolean;
}

export interface MailActionResponse {
  sent: boolean;
}

export interface AuthIdentity {
  name: string;
  email: string;
}

export interface ApiError {
  detail: string;
}
