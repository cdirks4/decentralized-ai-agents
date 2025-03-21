use std::pin::Pin;
use std::sync::Arc;
use std::collections::HashMap;  // Add this import
use tokio::sync::Mutex;
use tonic::{Request, Response, Status};
use libp2p::Swarm;
use tokio_stream::Stream;
use futures_util::StreamExt;

use crate::Behaviour;

pub mod ai_service {
    tonic::include_proto!("ai_service");
}

use ai_service::{
    ai_service_server::AiService,
    AiRequest, AiResponse, StreamRequest, AiEvent,
};

pub struct AiRpcService {
    swarm: Arc<Mutex<Swarm<Behaviour>>>,
}

impl AiRpcService {
    pub fn new(swarm: Arc<Mutex<Swarm<Behaviour>>>) -> Self {
        Self { swarm }
    }
}

#[tonic::async_trait]
impl AiService for AiRpcService {
    type StreamEventsStream = Pin<Box<dyn Stream<Item = Result<AiEvent, Status>> + Send + 'static>>;

    async fn process_message(
        &self,
        request: Request<AiRequest>,
    ) -> Result<Response<AiResponse>, Status> {
        let swarm = self.swarm.lock().await;
        
        match request.into_inner().prompt.as_str() {
            "peers" => {
                // Immediate response with connected peers
                let peers: Vec<String> = swarm
                    .connected_peers()
                    .map(|p| p.to_string())
                    .collect();
                
                Ok(Response::new(AiResponse {
                    request_id: "1".to_string(),
                    response: peers.join("\n"),
                    metadata: HashMap::new(),
                    status: "success".to_string(),
                }))
            },
            "topics" => {
                // Immediate response with subscribed topics
                let topics: Vec<String> = swarm
                    .behaviour()
                    .gossipsub
                    .topics()
                    .map(|t| t.to_string())
                    .collect();
                
                Ok(Response::new(AiResponse {
                    request_id: "2".to_string(),
                    response: topics.join("\n"),
                    metadata: HashMap::new(),
                    status: "success".to_string(),
                }))
            },
            _ => Ok(Response::new(AiResponse {
                request_id: "0".to_string(),
                response: "Unknown command".to_string(),
                metadata: HashMap::new(),
                status: "error".to_string(),
            }))
        }
    }

    async fn stream_events(
        &self,
        _request: Request<StreamRequest>,
    ) -> Result<Response<Self::StreamEventsStream>, Status> {
        let stream = tokio_stream::wrappers::IntervalStream::new(
            tokio::time::interval(std::time::Duration::from_secs(1))
        )
        .map(move |_| {
            Ok(AiEvent {
                payload: "heartbeat".to_string(),
                metadata: Default::default(),
                event_type: "heartbeat".to_string(),  // Add the required event_type field
            })
        });

        Ok(Response::new(Box::pin(stream)))
    }
}