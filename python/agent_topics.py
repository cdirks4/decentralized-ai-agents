from enum import Enum

class Topics:
    # Core topics (matching Rust server)
    PERSONAL_DISCOVERY = "personal-discovery"
    TASK_DELEGATION = "task-delegation"
    
    # Agent-specific subtopics
    RESEARCH = {
        "requests": f"{TASK_DELEGATION}/research-requests",
        "analysis": f"{TASK_DELEGATION}/data-analysis",
        "results": f"{TASK_DELEGATION}/research-results"
    }
    
    COORDINATION = {
        "requests": f"{TASK_DELEGATION}/task-requests",
        "assignments": f"{TASK_DELEGATION}/task-assignments",
        "results": f"{TASK_DELEGATION}/task-results"
    }
    
    COMMUNICATION = {
        "external": f"{PERSONAL_DISCOVERY}/external-requests",
        "internal": f"{PERSONAL_DISCOVERY}/internal-communications",
        "responses": f"{PERSONAL_DISCOVERY}/external-responses"
    }
    
    # Research related topics
    RESEARCH = {
        "requests": "research.requests",
        "results": "research.results",
        "updates": "research.updates"
    }
    
    # Task delegation topics
    TASK_DELEGATION = "tasks.delegation"
    
    # Agent discovery and coordination
    AGENT_DISCOVERY = "agent.discovery"
    RESEARCH_RESULTS = "research.results"
    RESEARCH_REQUESTS = "research.requests"  # Add this line
    
    # Knowledge sharing topics
    KNOWLEDGE_SHARE = "knowledge.share"