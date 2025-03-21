import asyncio
from research_agent import ResearchAgent
from agent_topics import Topics
import json
import grpc
import ai_service_pb2_grpc
import ai_service_pb2

class LibP2pAiServiceImpl(ai_service_pb2_grpc.AiServiceServicer):
    def __init__(self):
        self.connected_peers = set()
        self.peer_addresses = {}
        self.mdns_discovered_peers = set()

    async def ProcessMessage(self, request, context):
        print(f"Processing libp2p message from {request.agent_type}")
        if request.prompt == "discover_peers":
            # Add the requesting peer to our known peers
            peer_addr = context.peer()
            peer_id = request.agent_type
            self.peer_addresses[peer_id] = peer_addr
            self.connected_peers.add(peer_id)
            
            return ai_service_pb2.AiResponse(
                response_id=request.request_id,
                content="\n".join(self.connected_peers),
                status="success"
            )
        return ai_service_pb2.AiResponse(
            response_id=request.request_id,
            content="Processed",
            status="success"
        )
    
    async def StreamEvents(self, request, context):
        try:
            peer_id = request.agent_type
            self.connected_peers.add(peer_id)
            
            # Send initial peer list
            yield ai_service_pb2.AiEvent(
                event_type="peer_update",
                payload="\n".join(self.connected_peers),
                metadata={
                    "status": "active",
                    "discovery_type": "mdns"
                }
            )
            
            while True:
                # Simulate MDNS discovery of new peers
                if len(self.connected_peers) > 0:
                    yield ai_service_pb2.AiEvent(
                        event_type="peer_update",
                        payload="\n".join(self.connected_peers),
                        metadata={
                            "status": "active",
                            "discovery_type": "mdns"
                        }
                    )
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"Stream error: {e}")
            self.connected_peers.discard(peer_id)

async def start_grpc_server(port: int):
    server = grpc.aio.server()
    service = LibP2pAiServiceImpl()
    ai_service_pb2_grpc.add_AiServiceServicer_to_server(service, server)
    server.add_insecure_port(f'127.0.0.1:{port}')
    await server.start()
    return server, service

async def run_discovery_test():
    # Start gRPC servers with shared state
    server1, service1 = await start_grpc_server(50051)
    server2, service2 = await start_grpc_server(50052)
    
    # Create agents after servers are running
    agent1 = ResearchAgent(
        name="mdns_agent_1",
        port=50051,
        topics=[
            "personal-discovery",
            "task-delegation",
            "research.requests",
            "research.results"
        ]
    )
    
    agent2 = ResearchAgent(
        name="mdns_agent_2",
        port=50052,
        topics=[
            "personal-discovery",
            "task-delegation",
            "research.requests",
            "research.results"
        ]
    )
    
    try:
        await asyncio.gather(
            agent1.run(),
            agent2.run()
        )
    except Exception as e:
        print(f"Error in discovery test: {e}")
    finally:
        await server1.stop(grace=None)
        await server2.stop(grace=None)

if __name__ == "__main__":
    try:
        asyncio.run(run_discovery_test())
    except KeyboardInterrupt:
        print("\nStopping discovery test...")