import grpc
import asyncio
import sys
import ai_service_pb2
import ai_service_pb2_grpc

class P2PCliTool:
    def __init__(self, loop):
        self.loop = loop
        self.channel = grpc.aio.insecure_channel('localhost:50051')
        self.stub = ai_service_pb2_grpc.AiServiceStub(self.channel)
        # Print available methods
        print("Available methods:", dir(self.stub))

    async def list_peers(self):
        try:
            # Create request with required fields from proto definition
            request = ai_service_pb2.AiRequest(
                request_id="1",
                prompt="peers",
                agent_type="cli",
                parameters={}
            )
            response = await self.stub.ProcessMessage(request)
            print("\n/peers")
            print("Connected peers:")
            if response.response:
                for peer in response.response.split('\n'):
                    if peer.strip():
                        print(f"  {peer.strip()}")
        except grpc.RpcError as e:
            print(f"Error listing peers: {e}")
        except Exception as e:
            print(f"Error: {e}")

    async def list_topics(self):
        try:
            request = ai_service_pb2.AiRequest(
                request_id="2",
                prompt="topics",
                agent_type="cli",
                parameters={}
            )
            response = await self.stub.ProcessMessage(request)
            print("\n/topics")
            print("Subscribed topics:")
            if response.response:
                topics = response.response.split('\n')
                if not topics or (len(topics) == 1 and not topics[0].strip()):
                    print("  No topics subscribed")
                else:
                    for topic in topics:
                        if topic.strip():
                            print(f"  {topic.strip()}")
        except grpc.RpcError as e:
            print(f"Error listing topics: {e}")
        except Exception as e:
            print(f"Error: {e}")

    async def connect_topic(self, topic_name):
        try:
            request = ai_service_pb2.AiRequest(
                request_id="3",
                prompt=f"connect {topic_name}",
                agent_type="cli",
                parameters={"topic": topic_name}
            )
            response = await self.stub.ProcessMessage(request)
            print(f"Connected to topic: {topic_name}")
        except grpc.RpcError as e:
            print(f"Error connecting to topic: {e}")

    async def monitor_events(self):
        try:
            request = ai_service_pb2.StreamRequest(
                agent_type="cli",
                topics=[]
            )
            async for event in self.stub.StreamEvents(request):
                if "mdns" in event.event_type.lower():
                    print("Other event: Behaviour(Mdns(()))")
                elif event.event_type == "peers":
                    print(event.payload)
        except grpc.RpcError as e:
            print(f"Error monitoring events: {e}")

    async def handle_command(self, command):
        if command == "peers":
            await self.list_peers()
        elif command == "topics":
            await self.list_topics()
        elif command.startswith("connect "):
            topic = command.split(" ", 1)[1]
            await self.connect_topic(topic)
        else:
            print(f"Unknown command: {command}")

    async def run(self):
        if len(sys.argv) > 1:
            await self.handle_command(" ".join(sys.argv[1:]))
        else:
            print("P2P CLI Tool")
            print("Available commands: peers, topics, connect <topic>")
            while True:
                try:
                    command = input("> ").strip()
                    if command == "exit":
                        break
                    await self.handle_command(command)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {e}")

async def main():
    loop = asyncio.get_event_loop()
    cli = P2PCliTool(loop)
    await cli.run()

if __name__ == "__main__":
    asyncio.run(main())