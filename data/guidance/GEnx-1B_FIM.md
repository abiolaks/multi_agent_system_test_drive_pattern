# GEnx-1B — Fault Isolation Manual (Excerpt)
## Section 72-61: Fan Module — N2 Core Vibration

### Symptom
Rising N2 (core) vibration trend over successive flights. May show a
step-change reduction immediately after a fan trim balance, followed by a
resumed upward trend within weeks.

### Applicable thresholds
- Advisory: N2 vibration > 2.0 IPS
- Alarm: N2 vibration > 4.0 IPS

### Probable causes (ranked)
1. **Fan/LPC blade imbalance** from FOD or blade erosion — the typical
   first-occurrence cause, and the one a trim balance is expected to fix.
2. **Bearing wear (No. 1 or No. 2 main shaft bearing) or a developing
   crack** — indicated when vibration returns and continues climbing
   *after* a trim balance has already been performed. A recurrence
   pattern after balancing is a mechanical-fault signature, not a
   re-balanceable imbalance.
3. **Rotor rub** — check for a correlated oil temperature or debris-monitor
   signal before ruling this in.

### Diagnostic procedure
If vibration improves after a trim balance but resumes an upward trend
within roughly 4–6 weeks, do not repeat the trim balance. Escalate directly
to bearing/rotor inspection — repeated balancing against a mechanical fault
masks the underlying condition rather than correcting it.

### Recommended action
- **Advisory, first occurrence** (vibration 2.0–4.0 IPS, no prior balance
  on record): perform a fan trim balance per task 72-61-00.
- **Advisory recurring after a prior balance, or Alarm** (vibration >
  4.0 IPS): remove and inspect the fan module bearings per task 72-61-20.
  Do not dispatch beyond the alarm threshold without engineering
  disposition.

### Caveats
Vibration readings can be affected by strut/mount accelerometer
calibration drift. Cross-check against the redundant accelerometer channel
before condemning the engine or scheduling bearing removal.
