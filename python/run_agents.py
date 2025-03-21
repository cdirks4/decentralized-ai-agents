import asyncio
from research_agent import ResearchAgent
from coordinator_agent import CoordinatorAgent
from communication_agent import CommunicationAgent

async def main():
    # Create agent instances
    research_agent = ResearchAgent()
    coordinator_agent = CoordinatorAgent()
    communication_agent = CommunicationAgent()
    
    # Run all agents concurrently
    await asyncio.gather(
        research_agent.run(),
        coordinator_agent.run(),
        communication_agent.run()
    )

if __name__ == "__main__":
    asyncio.run(main())