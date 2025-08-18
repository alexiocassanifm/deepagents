#!/usr/bin/env python3
"""
Test script per validare l'integrazione LLM compression in CompactIntegration.

Questo script testa:
1. Caricamento della configurazione LLM compression
2. Inizializzazione del CompactIntegration con LLM
3. Analisi di una conversazione di esempio su software design
4. Confronto tra pattern-matching e LLM analysis
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_llm_compression_integration():
    """Test dell'integrazione LLM compression."""
    print("🧪 Testing LLM Compression Integration")
    print("=" * 50)
    
    try:
        # Import components
        from src.context.context_manager import ContextManager
        from src.context.compact_integration import CompactIntegration
        
        print("✅ Imports successful")
        
        # Test messages simulating software design conversation
        test_messages = [
            {
                "role": "user",
                "content": "I need to design a secure e-commerce platform with user authentication, payment processing, and real-time inventory management. The system should be scalable and handle high traffic during peak times."
            },
            {
                "role": "assistant", 
                "content": "I'll help you design a scalable e-commerce platform. Let me break this down into key components:\n\n1. **Authentication System**: We'll implement JWT-based authentication with refresh tokens\n2. **Payment Processing**: Integration with Stripe/PayPal with PCI compliance\n3. **Inventory Management**: Real-time stock updates with Redis caching\n4. **Scalability**: Microservices architecture with load balancing\n\nShall we start with the authentication microservice design?"
            },
            {
                "role": "user",
                "content": "Yes, let's focus on authentication first. I want it to be very secure with multi-factor authentication support. Also, the user data needs to comply with GDPR."
            },
            {
                "role": "assistant",
                "content": "Perfect! For a secure authentication system with GDPR compliance, here's the design:\n\n**Architecture:**\n- Microservice: `auth-service`\n- Database: PostgreSQL with encrypted fields\n- Cache: Redis for session management\n- Files: `src/auth/auth_controller.py`, `src/auth/models/user.py`\n\n**Security Features:**\n1. Password hashing with bcrypt (salt rounds: 12)\n2. MFA via TOTP (Google Authenticator compatible)\n3. Rate limiting: 5 login attempts per 15 minutes\n4. JWT tokens: 15min access, 7day refresh\n\n**GDPR Compliance:**\n- Data minimization in user profiles\n- Encryption at rest for PII\n- Right to deletion implementation\n- Audit logging for data access\n\nTODO: Implement password strength validation\nTODO: Add email verification flow\nTODO: Create admin panel for user management"
            }
        ]
        
        # Initialize ContextManager
        context_manager = ContextManager()
        print("✅ ContextManager initialized")
        
        # Initialize CompactIntegration
        compact_integration = CompactIntegration(
            context_manager=context_manager,
            model_name="claude-3-haiku-20240307"
        )
        print("✅ CompactIntegration initialized")
        
        # Check if LLM compression is available
        if compact_integration.use_llm_compression:
            print("🤖 LLM compression is ENABLED")
            print(f"   Model: {compact_integration.llm_config.get('model_name', 'Unknown')}")
            print(f"   Strategy: {compact_integration.llm_config.get('strategy', 'Unknown')}")
        else:
            print("⚠️  LLM compression is DISABLED (will use pattern-matching)")
        
        print("\n🔍 Testing Analysis Methods")
        print("-" * 30)
        
        # Test pattern-based analysis
        print("📊 Pattern-based analysis:")
        pattern_analysis = compact_integration._analyze_with_patterns(test_messages)
        print(f"   - Primary requests: {len(pattern_analysis['primary_request'])}")
        print(f"   - Technical concepts: {len(pattern_analysis['technical_concepts'])}")
        print(f"   - Files mentioned: {len(pattern_analysis['files_and_code'])}")
        print(f"   - Tasks found: {len(pattern_analysis['pending_tasks'])}")
        
        # Test LLM analysis if available
        if compact_integration.use_llm_compression:
            print("\n🤖 LLM-based analysis:")
            try:
                llm_analysis = compact_integration._analyze_with_llm(test_messages)
                print(f"   - Primary requests: {len(llm_analysis['primary_request'])}")
                print(f"   - Technical concepts: {len(llm_analysis['technical_concepts'])}")
                print(f"   - Files mentioned: {len(llm_analysis['files_and_code'])}")
                print(f"   - Tasks found: {len(llm_analysis['pending_tasks'])}")
                
                # Show some examples of extracted content
                if llm_analysis['technical_concepts']:
                    print(f"   - Example concepts: {llm_analysis['technical_concepts'][:3]}")
                if llm_analysis['primary_request']:
                    print(f"   - Example request: {llm_analysis['primary_request'][0][:100]}...")
                    
            except Exception as e:
                print(f"   ❌ LLM analysis failed: {e}")
        
        # Test full compression workflow
        print("\n📦 Testing Full Compression Workflow")
        print("-" * 40)
        
        try:
            compacted_messages, summary = compact_integration.perform_automatic_compaction(
                test_messages, 
                context={"test": True}
            )
            
            if summary.summary_content != "No compaction needed":
                print("✅ Compression completed successfully")
                print(f"   - Reduction: {summary.total_reduction_percentage:.1f}%")
                print(f"   - Trigger: {summary.trigger_type}")
                print(f"   - Preserved elements: {len(summary.preserved_elements)}")
                print(f"   - Summary length: {len(summary.summary_content)} chars")
            else:
                print("ℹ️  No compression needed (context below threshold)")
                
        except Exception as e:
            print(f"❌ Compression workflow failed: {e}")
        
        print("\n🎉 Integration test completed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed:")
        print("   pip install langchain-anthropic")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_configuration_status():
    """Mostra lo stato della configurazione."""
    print("\n🔧 Configuration Status")
    print("=" * 30)
    
    # Check environment variables
    compression_key = os.getenv('COMPRESSION_MODEL_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    model_name = os.getenv('COMPRESSION_MODEL_NAME')
    
    print(f"COMPRESSION_MODEL_API_KEY: {'✅ Set' if compression_key else '❌ Not set'}")
    print(f"ANTHROPIC_API_KEY: {'✅ Set' if anthropic_key else '❌ Not set'}")
    print(f"COMPRESSION_MODEL_NAME: {model_name or 'Not set (will use default)'}")
    
    # Check config file
    config_file = Path(__file__).parent / "config" / "context_config.yaml"
    print(f"Config file: {'✅ Found' if config_file.exists() else '❌ Missing'}")
    
    if not (compression_key or anthropic_key):
        print("\n💡 Setup Instructions:")
        print("1. Copy .env.example to .env")
        print("2. Add your Anthropic API key")
        print("3. Set COMPRESSION_MODEL_API_KEY=your-api-key")

if __name__ == "__main__":
    print("🚀 LLM Compression Integration Test")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    show_configuration_status()
    
    success = test_llm_compression_integration()
    
    if success:
        print("\n✅ All tests passed! LLM compression integration is working.")
    else:
        print("\n❌ Tests failed. Check the errors above.")
        sys.exit(1)