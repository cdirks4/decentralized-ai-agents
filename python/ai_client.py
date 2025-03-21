import grpc
import ai_service_pb2
import ai_service_pb2_grpc
import uuid
import os
from groq import Groq
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
import asyncio
from typing import List, Dict, Optional

class AiNetworkAgent:
    def __init__(self, 
                 name: str = "network_agent",
                 host: str = "[::1]:50051",
                 groq_api_key: Optional[str] = None,
                 model: str = "mixtral-8x7b-32768"):
        try:
            # Create async channel with IPv6 support
            self.channel = grpc.aio.insecure_channel(
                host,
                options=[
                    ('grpc.enable_http_proxy', 0),
                    ('grpc.keepalive_time_ms', 10000),
                ]
            )
            self.stub = ai_service_pb2_grpc.AiServiceStub(self.channel)
            self.name = name
            
            # Initialize Groq client
            self.groq_client = Groq(
                api_key=groq_api_key or os.environ.get("GROQ_API_KEY")
            )
            
            # Initialize AutoGen agents with Groq
            config_list = [{
                "model": model,
                "api_key": groq_api_key or os.environ.get("GROQ_API_KEY"),
                "api_base": "https://api.groq.com/openai/v1",
                "api_type": "groq"
            }]

            self.assistant = AssistantAgent(
                name=f"{name}_assistant",
                llm_config={"config_list": config_list}
            )
            
            self.user_proxy = UserProxyAgent(
                name=f"{name}_proxy",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=3,
                code_execution_config=False
            )
            
            print(f"Agent {self.name} initialized and connected to {host}")
            
        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            raise

    async def process_task(self, task: str, parameters: Dict[str, str] = None) -> Optional[str]:
        """Process a task through the network"""
        print(f"Agent {self.name} processing task: {task}")
        request = ai_service_pb2.AiRequest(
            request_id=str(uuid.uuid4()),
            prompt=task,
            agent_type=self.name,
            parameters=parameters or {}
        )
        
        try:
            response = await self.stub.ProcessMessage(request)
            print(f"Task completed successfully")
            return response.response
        except grpc.RpcError as e:
            print(f"Task processing error: {e.details() if hasattr(e, 'details') else str(e)}")
            return None

    async def subscribe_to_events(self, topics: List[str] = None):
        """Subscribe to network events"""
        if topics is None:
            topics = ["ai-requests", "ai-responses"]
            
        request = ai_service_pb2.StreamRequest(
            agent_type=self.name,
            topics=topics
        )
        
        try:
            async for event in self.stub.StreamEvents(request):
                await self.handle_event(event)
        except grpc.RpcError as e:
            print(f"Event subscription error: {e}")

    async def handle_event(self, event: ai_service_pb2.AiEvent):
        """Handle incoming network events"""
        print(f"Agent {self.name} received event: {event.event_type}")
        print(f"Payload: {event.payload}")
        # Add custom event handling logic here

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.channel.close()

# Example usage
async def main():
    async with AiNetworkAgent(name="example_agent") as agent:
        # Process a task
        result = await agent.process_task("Analyze this data")
        print(f"Task result: {result}")
        
        # Subscribe to events
        await agent.subscribe_to_events()

if __name__ == "__main__":
    asyncio.run(main())