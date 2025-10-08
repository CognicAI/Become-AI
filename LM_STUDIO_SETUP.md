# LM Studio GPU Setup Guide for RAG System

This guide shows you how to set up LM Studio with GPU acceleration for optimal performance.

## 🚀 Quick Setup Steps

### 1. Download & Install LM Studio
- Get it from: https://lmstudio.ai/
- Install and launch LM Studio
- Default port: `localhost:1234` ✅

### 2. Load Required Models

#### Chat Model (for responses):
- **Phi-3 Mini 128K Instruct** (3.8GB) - Recommended
- **Llama 3.1 8B Instruct** (4.6GB)
- **Mistral 7B Instruct** (4.1GB)

#### Embedding Model (for search):
- **BAAI/bge-base-en-v1.5** (438MB) - Recommended
- **sentence-transformers/all-MiniLM-L6-v2** (80MB)

### 3. Enable GPU Acceleration

In LM Studio Settings:
```
Hardware → GPU Acceleration:
• NVIDIA: Select CUDA
• AMD: Select ROCm
• Apple: Select Metal

GPU Layers: 32 (or maximum available)
Context Length: 4096-8192
```

### 4. Start the Server

1. Go to **Local Server** tab in LM Studio
2. Select your chat model (e.g., Phi-3 Mini)
3. Click **Start Server**
4. Verify at: http://localhost:1234

### 5. Test Connection

```powershell
# Test if LM Studio is responding
Invoke-WebRequest -Uri http://localhost:1234/v1/models -UseBasicParsing
```

### 6. Update Your .env File

```env
LMSTUDIO_URL=http://localhost:1234
LM_MODEL_NAME=phi-3-mini-128k-instruct
EMBEDDING_MODEL=bge-base-en-v1.5
EMBEDDING_DIMENSION=768
```

## 🎯 Hardware Recommendations

| GPU VRAM | Chat Model | Embedding Model | GPU Layers |
|-----------|------------|-----------------|------------|
| 4GB | Phi-3 Mini | bge-base-en-v1.5 | 20-25 |
| 8GB | Llama 3.1 8B | bge-base-en-v1.5 | 30-35 |
| 12GB+ | Llama 3.1 8B | bge-large-en-v1.5 | All |

## ⚡ Performance Tips

1. **Close other GPU apps** (games, video editing)
2. **Use SSD storage** for models
3. **16GB+ RAM** recommended
4. **Monitor GPU usage** in Task Manager

## 🔧 Troubleshooting

**"LM Studio not accessible"**
- ✅ Check LM Studio is running
- ✅ Server started in LM Studio interface
- ✅ No firewall blocking port 1234

**"No embedding models detected"**
- ✅ Load embedding model in LM Studio
- ✅ Model name matches .env file
- ✅ Try different embedding model

**"GPU out of memory"**
- ➡️ Reduce GPU layers
- ➡️ Use smaller model
- ➡️ Reduce context length

## ✅ Verify Setup

After setup, restart your RAG system:

```powershell
# Stop current server (Ctrl+C)
# Then restart
python start.py
```

Look for these success messages:
```
✅ LM Studio connection successful
✅ Embedding models found: ['bge-base-en-v1.5']
⚡ Using GPU acceleration
```

Now your RAG system will use GPU acceleration for both chat and embeddings! 🎉