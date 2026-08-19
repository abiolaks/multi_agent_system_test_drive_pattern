# Split deployment: agent on ACA CPU, model on ACA serverless GPU

The agent service runs on Azure Container Apps (CPU, scale-to-zero) and the model runs on ACA serverless GPU (A100, scale-to-zero, pay-per-second). The two workloads are split because their cost profiles are opposite: the agent is tiny and mostly idle, while the GPU is expensive and bursty. Scale-to-zero is acceptable because Scheduled Reports tolerate the ~30–60s cold start; a warm dedicated GPU is only justified if interactive latency becomes a requirement.
