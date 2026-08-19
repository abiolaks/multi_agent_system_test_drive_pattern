# Fabric Data Q&A

A multi-agent system that answers questions about data in the user's Fabric workspace, produces reports and recommendations, and supports scheduled reporting. Asset health — predictive maintenance for oil & gas equipment — is one topic among many.

## Language

### Core

**Report**:
The detailed written summary produced in response to a question.
_Avoid_: answer, output

**Scheduled Report**:
A Report drafted automatically at a recurring interval and sent after the user approves it, because the user asked to keep receiving it.
_Avoid_: subscription, recurring report

### Asset Health

**Asset Model**:
The make/model of an Asset (e.g. Emerson CSER-2000) that determines which Guidance — its threshold tables and Fault Signatures — applies to it.
_Avoid_: model type, equipment type

**Asset**:
A single physical machine or unit whose telemetry readings are monitored against thresholds to determine health. Atomic — one machine, one asset (e.g. a high-pressure gas compressor).
_Avoid_: machine, device, equipment

**Site**:
A grouping of Assets (plant, line, fleet, or an oil mining lease / OML) used to roll up health. Has no thresholds of its own.
_Avoid_: plant, line, facility, fleet, lease

**Reading**:
A single telemetry measurement from an Asset (e.g. temperature, vibration) at a point in time.
_Avoid_: metric, measurement, telemetry

**Threshold**:
A known limit for a Reading, in two tiers: an Advisory Threshold (investigate) and an Alarm Threshold (act). A Reading beyond one indicates a health problem.
_Avoid_: limit, baseline, boundary

**Guidance**:
A document (typically PDF, e.g. a maintenance manual) in the knowledge base containing threshold tables and Fault Signatures for an Asset Model. There is one per model; Readings are cross-referenced against the relevant one.
_Avoid_: manual, SOP, reference

**Fault Signature**:
A known failure mode with its characteristic pattern across Readings and a recommended action, defined in the Guidance.
_Avoid_: symptom, failure pattern, anomaly

**Health**:
The state of an Asset — Normal, Advisory, or Alarm — determined by comparing Readings to their Thresholds.
_Avoid_: status, condition

**Recommendation**:
A prescriptive action suggested when an Asset's Readings cross a Threshold. Asset-health only.
_Avoid_: suggestion, insight, advice
