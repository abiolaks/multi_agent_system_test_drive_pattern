Agentic design Pattern for this project- which one of the two below fit this and why
1. Routing via llm as router
2. Sequential ( prompt chaining)
TOOLS:
1. Fabric Data Agent mcp with code interpreter attached for generating visualization
2. web search tool 
3. Email sender funtion tool
4. Knowledge Base (Azure AI Search)
5. for cron jobs( scheduling event)


Deployment: Self Hosted
1. Model??
2. Code/Agent 

PromptTemplate
1. Reporting prompt
2. Router prompt
3.



Agent needs:
1. Prompt
2. llm
3. tool

Framework
Microsoft Agentic Framework

User Stories
1. user should be able to ask questions such as "what is the health status of my assets" - this should
pull information from the Fabric workspace Data agent via MCP and then make a report (detailed summary) and then make recommendations too.
the orchestrator agent should be able to cross reference the readings coming from the fabric data agent and cross reference
them against threshold data(information about the assets readings) coming from the knowledge base to get a feel

2. User should be able to set up schedule for reporting  

