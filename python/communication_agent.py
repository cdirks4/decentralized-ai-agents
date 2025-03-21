from base_agent import BaseNetworkAgent
from agent_topics import Topics
import json
from datetime import datetime

class CommunicationAgent(BaseNetworkAgent):
    def __init__(self, name: str = "communication_agent"):
        super().__init__(
            name=name,
            topics=[
                Topics.PERSONAL_DISCOVERY,
                Topics.COMMUNICATION["external"],
                Topics.COMMUNICATION["internal"],
                Topics.COMMUNICATION["responses"]
            ]
        )

    async def handle_event(self, event):
        if event.event_type == Topics.COMMUNICATION["external"]:
            # Process external requests and route internally
            processed_request = await self.process_external_request(event.payload)
            await self.publish_message(
                Topics.COMMUNICATION["internal"],
                json.dumps(processed_request)
            )
        elif event.event_type == Topics.COMMUNICATION["internal"]:
            # Format and send external responses
            await self.send_external_response(json.loads(event.payload))

    async def process_external_request(self, request):
        # Format external requests for internal processing
        return {
            "type": "external_request",
            "content": request,
            "timestamp": str(datetime.now())
        }