import grpc
import ai_service_pb2
import ai_service_pb2_grpc
import uuid
import os
from groq import Groq
from autogen import AssistantAgent, UserProxyAgent
from typing import List, Dict, Optional
import asyncio
from datetime import datetime


class BaseNetworkAgent:
    def __init__(self, 
                 name: str,
                 topics: List[str],
                 host: str = "[::1]:50051",
                 groq_api_key: Optional[str] = None,
                 model: str = "mixtral-8x7b-32768"):
        self.name = name
        self.topics = topics
        self.host = host
        
        # Initialize network connection
        self.channel = grpc.aio.insecure_channel(
            host,
            options=[
                ('grpc.enable_http_proxy', 0),
                ('grpc.keepalive_time_ms', 10000),
            ]
        )
        self.stub = ai_service_pb2_grpc.AiServiceStub(self.channel)
        
        # Initialize AI components
        self.groq_client = Groq(
            api_key=groq_api_key or os.environ.get("GROQ_API_KEY")
        )
        
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

    async def check_connection(self) -> dict:
        """Check connection status with the network"""
        try:
            # Track discovered peers
            self._discovered_peers = set()
            
            stream_request = ai_service_pb2.StreamRequest(
                agent_type=self.name,
                topics=self.topics
            )
            
            async for event in self.stub.StreamEvents(stream_request):
                if event.event_type == "peer_update":
                    peers = [p.strip() for p in event.payload.split("\n") if p.strip()]
                    valid_peers = [p for p in peers if p.startswith("12D3KooW")]
                    
                    if valid_peers:
                        self._discovered_peers.update(valid_peers)
                        return {"connected_peers": len(self._discovered_peers)}
                        
                elif hasattr(event, 'peers'):
                    valid_peers = [p for p in event.peers if p.startswith("12D3KooW")]
                    if valid_peers:
                        self._discovered_peers.update(valid_peers)
                        return {"connected_peers": len(self._discovered_peers)}
                
                break  # Only check first event
            
            return {"connected_peers": len(self._discovered_peers)}
                
        except Exception as e:
            print(f"Connection check failed: {e}")
            return {"connected_peers": 0, "error": str(e)}

    async def run(self):
        """Main agent loop"""
        request = ai_service_pb2.StreamRequest(
            agent_type=self.name,
            topics=self.topics
        )
        
        while True:
            try:
                print(f"Agent {self.name} starting to listen on topics: {self.topics}")
                async for event in self.stub.StreamEvents(request):
                    if event.event_type == "peer_update":
                        peers = event.payload.split("\n")
                        peer_count = sum(1 for p in peers if p.strip().startswith("12D3KooW"))
                        print(f"Connected peers count: {peer_count}")
                    await self.handle_event(event)
            except grpc.RpcError as e:
                print(f"Stream error for {self.name}: {e}")
                await asyncio.sleep(1)  # Wait before reconnecting

    async def publish_message(self, topic: str, content: str, metadata: Dict[str, str] = None):
        try:
            # Ensure peer connection
            status = await self.check_connection()
            if status.get("connected_peers", 0) == 0:
                print("No peers connected, attempting to establish connection...")
                # Send discovery request
                await self.stub.ProcessMessage(ai_service_pb2.AiRequest(
                    request_id=str(uuid.uuid4()),
                    prompt="peer_discovery",
                    agent_type=self.name,
                    parameters={"action": "connect"}
                ))
                await asyncio.sleep(2)  # Wait for connection
                
            # Add message routing metadata
            full_metadata = {
                "source_peer": self.name,
                "timestamp": str(datetime.now()),
                "topic": topic,
                "route": "p2p",  # Indicate peer-to-peer routing
                **(metadata or {})
            }
            
            request = ai_service_pb2.AiRequest(
                request_id=str(uuid.uuid4()),
                prompt=content,
                agent_type=self.name,
                parameters=full_metadata
            )
            
            print(f"Publishing message to topic {topic} with peer routing")
            print(f"Content: {content[:100]}...")
            
            response = await self.stub.ProcessMessage(request)
            print(f"Message published, response: {response}")
            return response
            
        except Exception as e:
            print(f"Error publishing message: {str(e)}")
            raise

    async def handle_event(self, event: ai_service_pb2.AiEvent):
        """Override this method in specialized agents"""
        print(f"Base agent received event: {event.event_type}")
        print(f"Event payload: {event.payload[:100]}...")  # Print first 100 chars

class LibP2PClient:
    def __init__(self, server_address='localhost:50051'):
        self.server_address = server_address
        
    async def connect_and_listen(self):
        async with grpc.aio.insecure_channel(self.server_address) as channel:
            stub = ai_service_pb2_grpc.AiServiceStub(channel)
            
            # Stream events from the Rust node
            stream_request = ai_service_pb2.StreamRequest()
            try:
                async for event in stub.stream_events(stream_request):
                    if event.event_type == "mdns":
                        print("Other event: Behaviour(Mdns(()))")
                    elif event.event_type == "peers":
                        print("\n/peers")
                        print("Connected peers:")
                        for peer_id in event.peers:
                            print(f"  {peer_id}")
            except grpc.RpcError as e:
                print(f"Stream error: {e}")

async def main():
    client = LibP2PClient()
    await client.connect_and_listen()

if __name__ == "__main__":
    asyncio.run(main())