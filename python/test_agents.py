import asyncio
from research_agent import ResearchAgent
from coordinator_agent import CoordinatorAgent
from communication_agent import CommunicationAgent
from agent_topics import Topics
import json

async def test_agents():
    # Initialize agents
    research = ResearchAgent()
    coordinator = CoordinatorAgent()
    comm = CommunicationAgent()
    
    # Test research request
    await research.publish_message(
        Topics.RESEARCH["requests"],
        json.dumps({
            "data": "Analyze the impact of AI on healthcare",
            "priority": "high"
        })
    )
    
    # Test task coordination
    await coordinator.publish_message(
        Topics.COORDINATION["requests"],
        json.dumps({
            "task": "Schedule data analysis meeting",
            "deadline": "2024-03-01"
        })
    )
    
    # Test external communication
    await comm.publish_message(
        Topics.COMMUNICATION["external"],
        json.dumps({
            "message": "Request for collaboration",
            "from": "external_partner"
        })
    )
    
    # Keep the script running to receive responses
    await asyncio.sleep(10)  # Wait for 10 seconds to see responses

if __name__ == "__main__":
    asyncio.run(test_agents())