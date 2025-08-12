import asyncio
from job_analysis_agent import AIJobAgent

# Initialiser l'agent
agent = AIJobAgent("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")

# Lancer l'analyse
results = asyncio.run(agent.run_full_analysis())