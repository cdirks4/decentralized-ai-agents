// Remove unused import
// use std::error::Error;  

use std::collections::HashMap;
use serde::{Serialize, Deserialize};
use libp2p::{
    gossipsub::{self, IdentityTransform},
    mdns,
    swarm::NetworkBehaviour,
};

#[derive(Debug, Serialize, Deserialize)]
pub enum AgentType {
    Personal,
    RoleBased,
    TaskBased,
    Business,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum TaskStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BusinessInfo {
    pub name: String,
    pub description: String,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum AgentMessage {
    Discovery { agent_type: AgentType, capabilities: Vec<String> },
    TaskRequest { task_id: String, description: String, parameters: HashMap<String, String> },
    TaskResponse { task_id: String, result: String, status: TaskStatus },
    BusinessSearch { query: String, filters: HashMap<String, String> },
    BusinessSearchResult { results: Vec<BusinessInfo> },
}

#[derive(NetworkBehaviour)]
#[behaviour(out_event = "BehaviourEvent")]
pub struct Behaviour {
    pub gossipsub: gossipsub::Behaviour<IdentityTransform>,
    pub mdns: mdns::tokio::Behaviour,
}

#[derive(Debug)]
pub enum BehaviourEvent {
    Gossipsub(gossipsub::Event),
    Mdns(()),
}

impl From<gossipsub::Event> for BehaviourEvent {
    fn from(event: gossipsub::Event) -> Self {
        BehaviourEvent::Gossipsub(event)
    }
}

impl From<mdns::Event> for BehaviourEvent {
    fn from(_event: mdns::Event) -> Self {
        BehaviourEvent::Mdns(())
    }
}


// Add secure key management module
pub mod keys {
    use libp2p::identity::Keypair;
    use std::sync::Arc;
    
    #[allow(dead_code)]
    pub struct SecureKeyStore {
        keypair: Arc<Keypair>,
    }
    
    impl SecureKeyStore {
        pub fn new(keypair: Keypair) -> Self {
            Self {
                keypair: Arc::new(keypair)
            }
        }
        
        // Add secure key operations
    }
}

// Add this line to expose the rpc module
// Remove this line as it's trying to import types that are already defined in this file
// pub use crate::types::{AgentMessage, AgentType, Behaviour};

// Remove these duplicate type exports since they're already defined above
// pub use crate::{
//     AgentMessage,
//     AgentType,
//     Behaviour,
// };

// Keep the rpc module export
pub mod rpc;

// Remove these lines as they're causing the duplicate definitions
// pub use crate::types::{AgentMessage, AgentType, Behaviour};
// pub use crate::{
//     AgentMessage,
//     AgentType,
//     Behaviour,
// };

// The types AgentMessage, AgentType, and Behaviour are already defined 
// in this file, so we don't need to import them

// Add this to src/lib.rs or create a new file src/message.rs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerMessage {
    pub id: String,
    pub sender_id: String,
    pub sender_type: String,
    pub content: String,
    pub timestamp: i64,
}