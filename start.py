"""Simple startup script for the Become AI RAG System."""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main function to start the RAG system."""
    print("🚀 Starting Become AI RAG System...")
    
    # Check if we're in the right directory
    if not Path("app/main.py").exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Check if virtual environment is activated
    if sys.platform == "win32":
        venv_python = Path(".venv/Scripts/python.exe")
    else:
        venv_python = Path(".venv/bin/python")

    if not venv_python.exists():
        print("❌ Error: Virtual environment not found. Please create it first:")
        print("   python3 -m venv .venv")
        if sys.platform == "win32":
            print("   .venv\\Scripts\\activate")
        else:
            print("   source .venv/bin/activate")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠️  Warning: .env file not found. Creating from template...")
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file from template")
        else:
            print("❌ Error: .env.example not found")
            sys.exit(1)
    
    print("✅ Environment checks passed")
    print("📊 Configuration loaded:")
    
    # Test configuration
    try:
        # Import here to avoid import errors during environment checks
        from app.utils.config import settings
        
        print(f"   • Database URL: {settings.database_url}")
        print(f"   • LM Studio URL: {settings.lmstudio_url}")
        print(f"   • Embedding Model: {settings.embedding_model}")
        print(f"   • API Host: {settings.api_host}:{settings.api_port}")
        print(f"   • Debug Mode: {settings.debug_mode}")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    print("\n🎯 Starting FastAPI server...")
    print("📖 API Documentation will be available at:")
    print(f"   • Swagger UI: http://{settings.api_host}:{settings.api_port}/docs")
    print(f"   • ReDoc: http://{settings.api_host}:{settings.api_port}/redoc")
    print(f"   • Health Check: http://{settings.api_host}:{settings.api_port}/health")
    
    print("\n💡 Quick Start:")
    print("   1. Ensure PostgreSQL with pgvector is running")
    print("   2. Start LM Studio with Phi-3 Mini model")
    print("   3. Use the API endpoints to scrape and query websites")
    
    print("\n⚡ Press Ctrl+C to stop the server")
    print("-" * 60)
    
    # Start the server
    try:
        cmd = [
            str(venv_python),
            "-m", "uvicorn",
            "app.main:app",
            "--host", settings.api_host,
            "--port", str(settings.api_port)
        ]
        
        # Add reload option only if debug mode is enabled
        if settings.debug_mode:
            cmd.append("--reload")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n👋 RAG System stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()