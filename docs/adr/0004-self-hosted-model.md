# Self-host our own model; do not use Foundry/cloud model APIs

We serve our own open-weights model (Qwen 3, via vLLM) instead of using Azure AI Foundry model catalog / serverless model APIs, because the customer requires hosting their own model. This keeps all data Azure-resident: Fabric, Azure AI Search, and the model's container all live in Azure, and inference data never leaves the container boundary. ACA serverless GPU is "bring your own model in your own container" and is distinct from Foundry's hosted models.
