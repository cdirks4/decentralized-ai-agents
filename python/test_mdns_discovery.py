import asyncio
from research_agent import ResearchAgent
import ai_service_pb2
import uuid

async def run_discovery_test():
    # Create two agents on different ports
    agent1 = ResearchAgent(
        name="mdns_agent_1",
        port=50051
    )
    
    agent2 = ResearchAgent(
        name="mdns_agent_2",
        port=50052
    )
    
    try:
        # Run both agents concurrently
        await asyncio.gather(
            agent1.run(),
            agent2.run()
        )
    except KeyboardInterrupt:
        print("\nStopping MDNS discovery test...")
    except Exception as e:
        print(f"Error in discovery test: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_discovery_test())
    except KeyboardInterrupt:
        print("\nStopping MDNS discovery test...")