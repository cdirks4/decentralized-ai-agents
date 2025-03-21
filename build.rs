fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create the proto directory if it doesn't exist
    std::fs::create_dir_all("proto")?;
    
    // Use the simplest possible tonic_build configuration
    tonic_build::compile_protos("proto/ai_service.proto")?;
    
    Ok(())
}