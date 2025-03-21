from base_agent import BaseNetworkAgent
from agent_topics import Topics
import ai_service_pb2
import asyncio
from typing import Dict, Any
import uuid
class ResearchAgent(BaseNetworkAgent):
    def __init__(self, 
                 name: str = "research_agent",
                 port: int = 50051,
                 topics: list = None):
        if topics is None:
            topics = [
                "personal-discovery",
                "task-delegation",
                "research.requests",
                "research.results"
            ]
        
        super().__init__(
            name=name,
            topics=topics,
            host=f"127.0.0.1:{port}"  # Change to IPv4 address
        )
        self.research_state = {}
        self.peer_knowledge = {}
        self.connected_peers = set()

    async def handle_event(self, event: ai_service_pb2.AiEvent):
        """Handle network events and coordinate AI logic"""
        try:
            print(f"Research agent received event: {event.event_type}")
            
            if event.event_type == "peer_update":
                await self._handle_peer_update(event)
            elif event.event_type == "research_request":
                await self._handle_research_request(event)
            elif event.event_type == "knowledge_share":
                await self._handle_knowledge_share(event)
                
        except Exception as e:
            print(f"Error handling event: {e}")

    async def establish_initial_connections(self):
        """Establish initial connections to the network"""
        try:
            # Send initial discovery request
            discovery_request = ai_service_pb2.AiRequest(
                request_id=str(uuid.uuid4()),
                prompt="discover_peers",
                agent_type=self.name,
                parameters={
                    "action": "discover",
                    "topics": self.topics
                }
            )
            
            await self.stub.ProcessMessage(discovery_request)
            await asyncio.sleep(2)  # Wait for discovery response
            
            # Check connection status
            status = await self.check_connection()
            print(f"Initial connection status: {status}")
            
        except Exception as e:
            print(f"Error establishing initial connections: {e}")

    async def _handle_peer_update(self, event):
        """Process peer discovery and connection events"""
        try:
            peers = event.payload.split("\n")
            new_peers = []
            
            for peer in peers:
                if peer.startswith("12D3KooW"):  # Valid peer ID
                    self.connected_peers.add(peer)
                    if peer not in self.peer_knowledge:
                        self.peer_knowledge[peer] = {
                            "last_seen": asyncio.get_event_loop().time(),
                            "capabilities": [],
                            "shared_knowledge": {},
                            "status": "connected"
                        }
                        new_peers.append(peer)
            
            print(f"Connected peers count: {len(self.connected_peers)}")
            
            if new_peers:
                print(f"New peers connected: {new_peers}")
                # Subscribe to topics for new peers
                for peer in new_peers:
                    await self._subscribe_to_peer_topics(peer)
                    await self._announce_capabilities(peer)
                    
        except Exception as e:
            print(f"Error handling peer update: {e}")

    async def _subscribe_to_peer_topics(self, peer_id: str):
        """Subscribe to topics for a specific peer"""
        try:
            subscription_request = ai_service_pb2.AiRequest(
                request_id=str(uuid.uuid4()),
                prompt="subscribe",
                agent_type=self.name,
                parameters={
                    "action": "subscribe",
                    "topics": self.topics,
                    "peer_id": peer_id
                }
            )
            await self.stub.ProcessMessage(subscription_request)
        except Exception as e:
            print(f"Error subscribing to peer topics: {e}")

    async def publish_message(self, topic: str, content: str, metadata: Dict[str, str] = None):
        """Override publish_message to check for sufficient peers"""
        if len(self.connected_peers) == 0:
            print("No peers connected, attempting to establish connection...")
            await self.establish_initial_connections()
            await asyncio.sleep(1)  # Wait for connections
            
        if len(self.connected_peers) > 0:
            return await super().publish_message(topic, content, metadata)
        else:
            raise Exception("InsufficientPeers: No peers available for publishing")

    async def _handle_research_request(self, event):
        """Process research requests from other agents"""
        try:
            request_data = event.payload
            # Add AI logic for processing research requests
            response = await self._process_research(request_data)
            
            # Share results with the network
            await self.publish_message(
                Topics.RESEARCH_RESULTS,
                response,
                {"originator": event.metadata.get("sender")}
            )
        except Exception as e:
            print(f"Error processing research request: {e}")

    async def _handle_knowledge_share(self, event):
        """Process knowledge shared by other agents"""
        try:
            knowledge_data = event.payload
            peer_id = event.metadata.get("sender")
            
            if peer_id in self.peer_knowledge:
                self.peer_knowledge[peer_id]["shared_knowledge"].update(
                    knowledge_data
                )
                # Trigger knowledge integration
                await self._integrate_knowledge(peer_id, knowledge_data)
        except Exception as e:
            print(f"Error processing shared knowledge: {e}")

    async def _announce_capabilities(self, peer_id: str):
        """Announce agent capabilities to peers"""
        capabilities = {
            "agent_type": "research",
            "supported_topics": self.topics,
            "ai_models": ["mixtral-8x7b-32768"]
        }
        await self.publish_message(
            Topics.AGENT_DISCOVERY,
            capabilities,
            {"target_peer": peer_id}
        )

    async def _process_research(self, request_data: str) -> Dict[str, Any]:
        """AI logic for processing research requests"""
        # Add your AI processing logic here
        # This is where you'd integrate with your AI models
        return {
            "status": "processed",
            "results": "Research results here",
            "confidence": 0.95
        }

    async def _integrate_knowledge(self, peer_id: str, knowledge_data: Dict):
        """Integrate knowledge shared by peers into local knowledge base"""
        # Add knowledge integration logic here
        pass
