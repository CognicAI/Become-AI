"""Test LM Studio connection and setup."""
import requests
import json

def test_lm_studio():
    """Test if LM Studio is running and configured properly."""
    print("🧪 Testing LM Studio Setup")
    print("=" * 40)
    
    lm_studio_url = "http://localhost:1234"
    chat_models = []
    embed_models = []
    
    # Test 1: Check if LM Studio is running
    print("\n1. Testing LM Studio connection...")
    try:
        response = requests.get(f"{lm_studio_url}/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print("✅ LM Studio is running and accessible")
            
            if models.get("data"):
                print("📋 Available models:")
                for model in models["data"]:
                    model_id = model.get("id", "Unknown")
                    print(f"   • {model_id}")
                
                # Check for chat models
                chat_models = [m for m in models["data"] 
                             if any(keyword in m.get("id", "").lower() 
                                   for keyword in ["instruct", "chat", "phi", "llama", "mistral"])]
                
                # Check for embedding models  
                embed_models = [m for m in models["data"]
                              if any(keyword in m.get("id", "").lower()
                                    for keyword in ["embed", "bge", "minilm", "gte"])]
                
                if chat_models:
                    print(f"✅ Chat models found: {len(chat_models)}")
                    for model in chat_models[:3]:  # Show first 3
                        print(f"   • {model['id']}")
                else:
                    print("⚠️  No chat models found")
                    print("💡 Load a chat model (e.g., Phi-3 Mini) in LM Studio")
                
                if embed_models:
                    print(f"✅ Embedding models found: {len(embed_models)}")
                    for model in embed_models[:3]:  # Show first 3
                        print(f"   • {model['id']}")
                else:
                    print("⚠️  No embedding models found")
                    print("💡 Load an embedding model (e.g., bge-base-en-v1.5) in LM Studio")
                    
            else:
                print("⚠️  No models loaded in LM Studio")
                print("💡 Load at least one chat model and one embedding model")
                
        else:
            print(f"❌ LM Studio responded with status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ LM Studio is not running on localhost:1234")
        print("💡 Start LM Studio and ensure the server is running")
        return False
    except Exception as e:
        print(f"❌ Error connecting to LM Studio: {e}")
        return False
    
    # Test 2: Test chat completion
    print("\n2. Testing chat completion...")
    try:
        chat_payload = {
            "model": "phi-3-mini-128k-instruct",  # Try common model name
            "messages": [
                {"role": "user", "content": "Hello! Can you respond with just 'Working' if you receive this?"}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{lm_studio_url}/v1/chat/completions",
            json=chat_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0]["message"]["content"]
                print(f"✅ Chat completion working")
                print(f"   Response: {message}")
            else:
                print("⚠️  Chat completion returned empty response")
        else:
            print(f"⚠️  Chat completion failed: {response.status_code}")
            print("💡 Make sure a chat model is loaded and server is started in LM Studio")
            
    except Exception as e:
        print(f"⚠️  Chat completion test error: {e}")
    
    # Test 3: Test embeddings
    print("\n3. Testing embeddings...")
    try:
        embed_payload = {
            "model": "bge-base-en-v1.5",  # Try common embedding model
            "input": "This is a test sentence for embedding generation."
        }
        
        response = requests.post(
            f"{lm_studio_url}/v1/embeddings",
            json=embed_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "data" in result and len(result["data"]) > 0:
                embedding = result["data"][0]["embedding"]
                print(f"✅ Embeddings working")
                print(f"   Dimension: {len(embedding)}")
                print(f"   Sample values: {embedding[:5]}...")
            else:
                print("⚠️  Embedding returned empty response")
        else:
            print(f"⚠️  Embedding failed: {response.status_code}")
            print("💡 Make sure an embedding model is loaded in LM Studio")
            
    except Exception as e:
        print(f"⚠️  Embedding test error: {e}")
    
    print("\n" + "=" * 40)
    print("🎯 Setup Summary:")
    print("✅ LM Studio is accessible" if response.status_code == 200 else "❌ LM Studio connection failed")
    
    if response.status_code == 200 and models.get("data"):
        if chat_models and embed_models:
            print("✅ Both chat and embedding models are loaded")
            print("🚀 Your setup is ready for the RAG system!")
        elif chat_models:
            print("⚠️  Chat models loaded, but missing embedding models")
            print("💡 Load an embedding model for full functionality")
        elif embed_models:
            print("⚠️  Embedding models loaded, but missing chat models")
            print("💡 Load a chat model for full functionality")
        else:
            print("❌ No suitable models found")
            print("💡 Load both chat and embedding models in LM Studio")
    else:
        print("❌ LM Studio setup incomplete")
        print("💡 Follow the LM_STUDIO_SETUP.md guide")
    
    return True

if __name__ == "__main__":
    test_lm_studio()