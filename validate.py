"""
Quick validation script to check if the AI Auditor setup is working correctly.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_imports():
    """Check if all required imports work."""
    print("🔍 Checking imports...")
    try:
        import fastapi
        import uvicorn
        import loguru
        import prometheus_client
        import psutil
        import langchain
        import sentence_transformers
        import numpy
        import sklearn
        print("✅ Core dependencies OK")
        
        from app.core import config, security, monitoring
        from app.services import vector_store, drift_detector, rag_engine
        from app.api import routes
        print("✅ Application modules OK")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def check_config():
    """Check if configuration loads correctly."""
    print("\n🔍 Checking configuration...")
    try:
        from app.core.config import settings
        print(f"  App Name: {settings.app_name}")
        print(f"  Environment: {settings.environment}")
        print(f"  Port: {settings.port}")
        print(f"  API Key Enabled: {settings.api_key_enabled}")
        print(f"  Use Milvus: {settings.use_milvus}")
        print("✅ Configuration OK")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def check_api_creation():
    """Check if FastAPI app can be created."""
    print("\n🔍 Checking API creation...")
    try:
        from app.api.routes import create_app
        app = create_app()
        print(f"  App Title: {app.title}")
        print(f"  Routes: {len(app.routes)}")
        print("✅ API creation OK")
        return True
    except Exception as e:
        print(f"❌ API creation error: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("AI AUDITOR - VALIDATION SCRIPT")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", check_imports()))
    results.append(("Configuration", check_config()))
    results.append(("API Creation", check_api_creation()))
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:.<40} {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED!")
        print("\n📝 Next steps:")
        print("  1. Copy .env.example to .env and configure")
        print("  2. Run: python -m app.main")
        print("  3. Visit: http://localhost:8000/docs")
        return 0
    else:
        print("⚠️  SOME CHECKS FAILED!")
        print("\nPlease fix the errors above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
