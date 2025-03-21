use std::error::Error;
use std::collections::HashMap;
use std::sync::Arc;
use std::pin::Pin;

use libp2p::{
    core::{transport::Transport, upgrade},
    gossipsub::{self, MessageAuthenticity, ValidationMode, Sha256Topic},
    identity, noise, tcp, mdns,
    swarm::{SwarmEvent, Config as SwarmConfig, ConnectionError},
    PeerId, Swarm,
    futures::StreamExt,
};
use tokio::io::AsyncBufReadExt;

// Import types from our library
use decentralized_ai_agents::{
    AgentType,
    AgentMessage,
    Behaviour,
    BehaviourEvent,
};

use decentralized_ai_agents::rpc::ai_service::{
    ai_service_server::{AiService, AiServiceServer},
    AiRequest, AiResponse, AiEvent, StreamRequest,
};
use tonic::{transport::Server, Request, Response, Status};
use futures_util::Stream;

use tracing::{info, Level};
use tracing_subscriber::{FmtSubscriber, EnvFilter};
use tracing_appender::rolling::{RollingFileAppender, Rotation};

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Initialize file appender with correct parameters
    let file_appender = RollingFileAppender::new(
        Rotation::NEVER,
        "logs",  // directory
        "ai-agents",  // filename prefix
    );

    // Create a non-blocking writer
    let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);

    // Initialize the subscriber with both console and file output
    let subscriber = FmtSubscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .with_writer(non_blocking)
        .with_ansi(false)
        .with_thread_ids(true)
        .with_file(true)
        .with_line_number(true)
        .with_level(true)
        .pretty()
        .try_init()
        .expect("Failed to set tracing subscriber");

    info!("Starting AI agent server...");
    
    // Create a new identity
    let id = identity::Keypair::generate_ed25519();
    let peer_id = PeerId::from(id.public());

    // Create transport
    let transport = tcp::tokio::Transport::new(tcp::Config::default())
        .upgrade(upgrade::Version::V1)
        .authenticate(noise::Config::new(&id)?)
        .multiplex(libp2p::yamux::Config::default())
        .boxed();

    // Create a gossipsub network behaviour with modified keep-alive settings
    let gossipsub_config = gossipsub::ConfigBuilder::default()
        .heartbeat_interval(std::time::Duration::from_secs(10))
        .validation_mode(ValidationMode::Strict)
        // Remove keep_alive as it's not available
        .build()
        .expect("Valid config");
            
    let gossipsub = gossipsub::Behaviour::new(
        MessageAuthenticity::Signed(id.clone()),
        gossipsub_config,
    ).expect("Valid gossipsub behavior");

    // Create an mdns network behaviour
    let mdns = mdns::tokio::Behaviour::new(mdns::Config::default(), peer_id)?;

    // Create a swarm
    let mut swarm = Swarm::new(
        transport,
        Behaviour {
            gossipsub,
            mdns,
        },
        peer_id,
        SwarmConfig::with_tokio_executor(), // Changed from default()
    );

    // Subscribe to topics (assuming Personal agent type for this example)
    let agent_type = AgentType::Personal;
    let topics = match agent_type {
        AgentType::Personal => vec!["personal-discovery", "task-delegation"],
        AgentType::RoleBased => vec!["role-discovery", "specific-role-tasks"],
        AgentType::TaskBased => vec!["task-discovery", "task-execution"],
        AgentType::Business => vec!["business-discovery", "business-queries"],
    };

    for topic_name in topics {
        let topic = Sha256Topic::new(topic_name);
        swarm.behaviour_mut().gossipsub.subscribe(&topic.into())?;
    }

    // Listen on all interfaces
    swarm.listen_on("/ip4/0.0.0.0/tcp/0".parse()?)?;

    // In the main function, before creating the RPC service
    let swarm = Arc::new(tokio::sync::Mutex::new(swarm));
    let rpc_service = AiRpcService::new(swarm.clone());

    // Create RPC service and start server
    let rpc_addr = "[::1]:50051".parse().unwrap();

    println!("Starting RPC server on {}", rpc_addr);

    let rpc_server = Server::builder()
        .add_service(AiServiceServer::new(rpc_service))
        .serve(rpc_addr);

    tokio::spawn(async move {
        if let Err(e) = rpc_server.await {
            eprintln!("RPC server error: {}", e);
        }
    });

    // Event loop with stdin handling
    let mut stdin = tokio::io::BufReader::new(tokio::io::stdin()).lines();

    loop {
        tokio::select! {
            line = stdin.next_line() => {
                if let Ok(Some(line)) = line {
                    let mut swarm_lock = swarm.lock().await;
                    handle_command(&mut swarm_lock, &line).await?;
                }
            }
            event = Box::pin(async {
                let mut lock = swarm.lock().await;
                lock.select_next_some().await
            }) => {
                match event {
                    SwarmEvent::Behaviour(BehaviourEvent::Gossipsub(gossipsub::Event::Message { 
                        propagation_source: _,
                        message_id: _,
                        message,
                    })) => {
                        if let Ok(msg) = serde_json::from_slice::<AgentMessage>(&message.data) {
                            handle_message(msg).await?;
                        }
                    }
                    SwarmEvent::NewListenAddr { address, .. } => {
                        println!("Listening on {}", address);
                    }
                    SwarmEvent::IncomingConnection { local_addr, send_back_addr, .. } => {
                        println!("Incoming connection from {} to {}", send_back_addr, local_addr);
                    }
                    SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                        println!("Connected to peer: {}", peer_id);
                    }
                    SwarmEvent::ConnectionClosed { peer_id, cause, .. } => {
                        println!("Connection closed with peer {}: {:?}", peer_id, cause);
                        // Fix the ConnectionError matching
                        if let Some(error) = cause {
                            if matches!(error, ConnectionError::KeepAliveTimeout) {
                                println!("Attempting to reconnect to peer: {}", peer_id);
                                if let Err(e) = swarm.lock().await.dial(peer_id) {
                                    println!("Failed to reconnect: {}", e);
                                }
                            }
                        }
                    }
                    event => {
                        println!("Other event: {:?}", event);
                    }
                }
            }
        }
    }
} // End of main()

async fn handle_message(msg: AgentMessage) -> Result<(), Box<dyn Error>> {
    match msg {
        AgentMessage::Discovery { agent_type, capabilities } => {
            println!("Discovered agent: {:?} with capabilities: {:?}", agent_type, capabilities);
        }
        AgentMessage::TaskRequest { task_id, description, parameters: _ } => {
            println!("Received task request: {} - {}", task_id, description);
        }
        AgentMessage::TaskResponse { task_id, result: _, status } => {
            println!("Received task response: {} - {:?}", task_id, status);
        }
        AgentMessage::BusinessSearch { query, filters } => {
            println!("Business search query: {} with filters: {:?}", query, filters);
        }
        AgentMessage::BusinessSearchResult { results } => {
            println!("Received {} business results", results.len());
        }
    }
    Ok(())
}

async fn handle_command(swarm: &mut Swarm<Behaviour>, line: &str) -> Result<(), Box<dyn Error>> {
    match line {
        s if s.starts_with("/search ") => {
            let query = s.strip_prefix("/search ").unwrap_or("").to_string();
            let msg = AgentMessage::BusinessSearch {
                query,
                filters: HashMap::new(),
            };
            let topic = Sha256Topic::new("business-queries");
            match swarm.behaviour_mut().gossipsub.publish(topic, serde_json::to_vec(&msg)?) {
                Ok(_) => println!("Published search query"),
                Err(e) => println!("Failed to publish: {}", e),
            }
        }
        s if s.starts_with("/connect ") => {
            if let Ok(peer_id_str) = s.strip_prefix("/connect ").unwrap_or("").parse::<PeerId>() {
                println!("Attempting to connect to peer: {}", peer_id_str);
                swarm.dial(peer_id_str)?;
            } else {
                println!("Invalid peer ID format");
            }
        }
        "/peers" => {
            let peers: Vec<_> = swarm.behaviour().mdns.discovered_nodes().collect();
            if peers.is_empty() {
                println!("No peers connected. Waiting for peer discovery...");
            } else {
                println!("Connected peers:");
                for peer in peers {
                    println!("  {}", peer);
                }
            }
        }
        "/topics" => {
            println!("Subscribed topics:");
            let topic_names = vec![
                "personal-discovery",
                "task-delegation",
                "role-discovery",
                "specific-role-tasks",
                "task-discovery",
                "task-execution",
                "business-discovery",
                "business-queries",
            ];
            for topic_name in topic_names {
                let topic = Sha256Topic::new(topic_name);
                let topic_hash = topic.hash();
                if swarm.behaviour().gossipsub.topics().any(|t| t == &topic_hash) {
                    println!("  {} ({})", topic_name, topic_hash);
                }
            }
        }
        "/help" => {
            println!("Available commands:");
            println!("  /search <query>   - Search for businesses");
            println!("  /connect <peerid> - Connect to a specific peer");
            println!("  /peers           - List connected peers");
            println!("  /topics          - List subscribed topics");
            println!("  /help            - Show this help message");
        }
        _ => println!("Unknown command. Type /help for available commands"),
    }
    Ok(())
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_message_serialization() {
        let msg = AgentMessage::Discovery {
            agent_type: AgentType::Personal,
            capabilities: vec!["ai".to_string(), "chat".to_string()],
        };
        let serialized = serde_json::to_string(&msg).expect("Failed to serialize");
        let deserialized: AgentMessage = serde_json::from_str(&serialized).expect("Failed to deserialize");
        
        match deserialized {
            AgentMessage::Discovery { agent_type, capabilities } => {
                assert!(matches!(agent_type, AgentType::Personal));
                assert_eq!(capabilities, vec!["ai".to_string(), "chat".to_string()]);
            }
            _ => panic!("Wrong message type after deserialization"),
        }
    }

    #[test]
    fn test_business_info_serialization() {
        let mut metadata = HashMap::new();
        metadata.insert("location".to_string(), "San Francisco".to_string());
        
        let business = BusinessInfo {
            name: "Test Business".to_string(),
            description: "A test business".to_string(),
            metadata,
        };
        
        let serialized = serde_json::to_string(&business).expect("Failed to serialize");
        let deserialized: BusinessInfo = serde_json::from_str(&serialized).expect("Failed to deserialize");
        
        assert_eq!(business.name, deserialized.name);
        assert_eq!(business.description, deserialized.description);
        assert_eq!(business.metadata.get("location"), deserialized.metadata.get("location"));
    }

    #[test]
    fn test_behaviour_event_conversion() {
        let gossipsub_event = gossipsub::Event::Subscribed {
            peer_id: PeerId::random(),
            topic: Sha256Topic::new("test-topic").into(),  // Add .into() here
        };
        
        let behaviour_event = BehaviourEvent::from(gossipsub_event);
        assert!(matches!(behaviour_event, BehaviourEvent::Gossipsub(_)));
        
        let mdns_event = mdns::Event::Discovered(vec![]);
        let behaviour_event = BehaviourEvent::from(mdns_event);
        assert!(matches!(behaviour_event, BehaviourEvent::Mdns(())));
    }
}


// Modify the service to wrap Swarm in Arc<tokio::sync::Mutex<>>
pub struct AiRpcService {
    swarm: Arc<tokio::sync::Mutex<Swarm<Behaviour>>>,  // Use tokio's Mutex instead of parking_lot
}

impl AiRpcService {
    pub fn new(swarm: Arc<tokio::sync::Mutex<Swarm<Behaviour>>>) -> Self {
        Self { swarm }
    }
}

// Update the trait implementation with correct lifetimes
#[tonic::async_trait]
impl AiService for AiRpcService {
    type StreamEventsStream = Pin<Box<dyn Stream<Item = Result<AiEvent, Status>> + Send + 'static>>;

    async fn process_message(
        &self,
        request: Request<AiRequest>,
    ) -> Result<Response<AiResponse>, Status> {
        // Use the swarm to get peer count
        let swarm = self.swarm.lock().await;
        let peer_count = swarm.connected_peers().count();
        
        let request_data = request.into_inner();
        let response = AiResponse {
            request_id: request_data.request_id,
            response: format!("Processed message with {} connected peers", peer_count),
            metadata: HashMap::new(),
            status: "success".to_string(),
        };
        
        Ok(Response::new(response))
    }
    
    async fn stream_events(
        &self,
        _request: Request<StreamRequest>,
    ) -> Result<Response<Self::StreamEventsStream>, Status> {
        let swarm = self.swarm.clone();
        let stream = tokio_stream::wrappers::IntervalStream::new(
            tokio::time::interval(std::time::Duration::from_secs(1))
        )
        .map(move |_| {
            let peer_count = swarm.try_lock()
                .map(|s| s.connected_peers().count())
                .unwrap_or(0);
            
            Ok(AiEvent {
                payload: format!("Connected peers: {}", peer_count),
                metadata: HashMap::new(),
                event_type: "peer_update".to_string(),  // Added missing field
            })
        });

        Ok(Response::new(Box::pin(stream)))
    }
}

// Remove everything after the tests module (lines 306-326)
