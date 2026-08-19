# CFM56-7B26 — Fault Isolation Manual (Excerpt)
## Section 72-31: Turbine Section — EGT Margin Erosion

### Symptom
Progressive decrease in EGT margin (measured EGT approaching redline at a
given N1/power setting) trending downward over multiple flight cycles, with
no corresponding abnormal change in N1, N2, fuel flow, or oil parameters.

### Applicable thresholds
- Advisory: EGT margin < 40°C
- Alarm: EGT margin < 20°C

### Probable causes (ranked)
1. **Hot-section erosion / wear** — turbine blade tip clearance increase or
   nozzle guide vane distress. The most common cause of a gradual,
   monotonic margin decline with all other parameters nominal.
2. **Compressor fouling or erosion** — usually accompanied by a fuel-flow
   increase at constant N1; rule out before concluding hot-section wear.
3. **VBV/VSV schedule drift** — check for abnormal N1/N2 relationship
   before proceeding to borescope.
4. **Instrumentation drift** — cross-check against the redundant EGT probe;
   a single-channel-only decline suggests a sensor issue, not engine wear.

### Diagnostic procedure
Trend EGT margin over the last 90 days. A gradual decline (greater than
roughly 1°C/week average) with N1, N2, fuel flow, oil pressure, and
vibration all remaining within normal range is consistent with hot-section
erosion and should be dispositioned as such absent evidence for causes 2–4.

### Recommended action
- **Advisory range** (margin 20–40°C): schedule a borescope inspection of
  the HPT/LPT within the next 2 A-checks per task 72-31-00.
- **Alarm range** (margin < 20°C): borescope inspection within 14 days per
  task 72-31-00. If erosion is confirmed beyond limits, schedule hot-section
  module replacement at the next heavy maintenance visit. Continued
  dispatch below alarm threshold requires engineering disposition.

### Caveats
Margin loss can also follow a miscalibrated compressor water-wash cycle.
Verify wash history before concluding the cause is hot-section wear.
