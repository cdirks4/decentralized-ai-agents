use decentralized_ai_agents::*;
use libp2p::{
    core::{transport::Transport, upgrade},
    gossipsub::{self, MessageAuthenticity, ValidationMode},
    identity, mdns, noise, tcp,
    swarm::{SwarmEvent, Config as SwarmConfig},  // Keep SwarmEvent
    PeerId, Swarm,
    futures::StreamExt,
};
use std::time::Duration;
use tokio::time::sleep;

#[tokio::test]
async fn test_peer_discovery() {
    let mut swarm1 = create_test_swarm().await.expect("Failed to create swarm 1");
    let mut swarm2 = create_test_swarm().await.expect("Failed to create swarm 2");
    
    // Listen on different ports
    swarm1.listen_on("/ip4/127.0.0.1/tcp/0".parse().unwrap()).unwrap();
    swarm2.listen_on("/ip4/127.0.0.1/tcp/0".parse().unwrap()).unwrap();

    // Get the listening addresses
    let mut swarm1_addr = None;
    let mut swarm2_addr = None;

    // Wait for listening addresses to be available
    for _ in 0..10 {
        tokio::select! {
            event = swarm1.select_next_some() => {
                if let SwarmEvent::NewListenAddr { address, .. } = event {
                    swarm1_addr = Some(address);
                }
            }
            event = swarm2.select_next_some() => {
                if let SwarmEvent::NewListenAddr { address, .. } = event {
                    swarm2_addr = Some(address);
                }
            }
            _ = sleep(Duration::from_millis(100)) => {}
        }

        if swarm1_addr.is_some() && swarm2_addr.is_some() {
            break;
        }
    }

    // Dial swarm2 from swarm1
    if let Some(addr) = swarm2_addr {
        swarm1.dial(addr).expect("Swarm 1 failed to dial Swarm 2");
    }

    // Wait for peer discovery
    let mut discovery_timeout = 5;  // 5 seconds timeout
    while discovery_timeout > 0 
        && (swarm1.connected_peers().count() == 0 
            || swarm2.connected_peers().count() == 0) {
        tokio::select! {
            _ = swarm1.select_next_some() => {}
            _ = swarm2.select_next_some() => {}
            _ = sleep(Duration::from_secs(1)) => {
                discovery_timeout -= 1;
            }
        }
    }
    
    // Assert peers have discovered each other
    assert!(swarm1.connected_peers().count() > 0, "Swarm 1 failed to discover any peers");
    assert!(swarm2.connected_peers().count() > 0, "Swarm 2 failed to discover any peers");
}

async fn create_test_swarm() -> Result<Swarm<Behaviour>, Box<dyn std::error::Error>> {
    let id = identity::Keypair::generate_ed25519();
    let peer_id = PeerId::from(id.public());
    
    let transport = tcp::tokio::Transport::new(tcp::Config::default())
        .upgrade(upgrade::Version::V1)
        .authenticate(noise::Config::new(&id)?)
        .multiplex(libp2p::yamux::Config::default())
        .boxed();

    let gossipsub = gossipsub::Behaviour::new(
        MessageAuthenticity::Signed(id.clone()),
        gossipsub::ConfigBuilder::default()
            .heartbeat_interval(Duration::from_secs(1))
            .validation_mode(ValidationMode::Strict)
            .build()
            .expect("Valid config"),
    ).expect("Valid gossipsub behavior");

    let mdns = mdns::tokio::Behaviour::new(mdns::Config::default(), peer_id)?;

    Ok(Swarm::new(
        transport,
        Behaviour { gossipsub, mdns },
        peer_id,
        SwarmConfig::with_tokio_executor(),
    ))
}