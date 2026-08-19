# In-process scheduler for POV, durable scheduler for production

Scheduling uses an in-process scheduler (APScheduler) for the POV, knowingly to be replaced with a durable scheduler (a queue + worker, or a persistent job store) before production. In-memory jobs are lost on restart and duplicate across replicas — acceptable while proving the flow — but a Scheduled Report must not be silently missed or duplicated in production.
