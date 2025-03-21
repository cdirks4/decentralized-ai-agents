import asyncio
import grpc
import ai_service_pb2
import ai_service_pb2_grpc
import uuid

async def test_grpc_connection():
    print("Testing gRPC connection...")
    
    # Try both ports
    ports = ["50051", "50052"]
    
    for port in ports:
        try:
            channel = grpc.aio.insecure_channel(f"[::1]:{port}")
            stub = ai_service_pb2_grpc.AiServiceStub(channel)
            
            # Test request
            request = ai_service_pb2.AiRequest(
                request_id=str(uuid.uuid4()),
                prompt="connection_test",
                agent_type="test_agent",
                parameters={"test": "true"}
            )
            
            print(f"\nTesting port {port}...")
            response = await stub.ProcessMessage(request)
            print(f"Response from {port}: {response}")
            
            # Test stream
            stream_request = ai_service_pb2.StreamRequest(
                agent_type="test_agent",
                topics=["test-topic"]
            )
            
            print(f"Testing stream on port {port}...")
            async for event in stub.StreamEvents(stream_request):
                print(f"Stream event from {port}: {event}")
                break  # Just test first event
                
            print(f"\nPort {port} is responding correctly")
            
        except Exception as e:
            print(f"Error testing port {port}: {e}")
            
        finally:
            if 'channel' in locals():
                await channel.close()

if __name__ == "__main__":
    asyncio.run(test_grpc_connection())