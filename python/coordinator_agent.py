from base_agent import BaseNetworkAgent
from agent_topics import Topics
import json
from datetime import datetime

class CoordinatorAgent(BaseNetworkAgent):
    def __init__(self, name: str = "coordinator_agent"):
        super().__init__(
            name=name,
            topics=[
                Topics.TASK_DELEGATION,
                Topics.COORDINATION["requests"],
                Topics.COORDINATION["assignments"],
                Topics.COORDINATION["results"]
            ]
        )
        self.active_tasks = {}

    async def handle_event(self, event):
        if event.event_type == Topics.COORDINATION["requests"]:
            # Distribute tasks to appropriate agents
            task = json.loads(event.payload)
            assignment = await self.assign_task(task)
            await self.publish_message(
                Topics.COORDINATION["assignments"],
                json.dumps(assignment)
            )
        elif event.event_type == Topics.COORDINATION["results"]:
            # Process and coordinate results
            await self.process_results(json.loads(event.payload))

    async def assign_task(self, task):
        # Logic to determine best agent for task
        task_id = str(uuid.uuid4())
        self.active_tasks[task_id] = {
            "status": "assigned",
            "timestamp": str(datetime.now()),
            "task": task
        }
        return {
            "task_id": task_id,
            "assignment": task
        }