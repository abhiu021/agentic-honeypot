import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory.session_manager import load_session, save_session, get_all_sessions

def test_session_lifecycle():
    """Test session creation, loading, and persistence"""
    print("\n=== Testing Session Management ===\n")
    
    # Test 1: Create new session
    session1 = load_session("test-session-001")
    print(f"[OK] Created session: {session1.sessionId}")
    print(f"  Start time: {session1.sessionStartTime}")
    print(f"  Messages: {session1.totalMessagesExchanged}")
    
    # Test 2: Add conversation data
    session1.scamType = "UPI_FRAUD"
    session1.totalMessagesExchanged = 3
    session1.conversationHistory.append({
        "sender": "scammer",
        "text": "Your account is blocked"
    })
    save_session("test-session-001", session1)
    print(f"\n[OK] Updated session with conversation data")
    
    # Test 3: Load existing session
    session1_loaded = load_session("test-session-001")
    print(f"\n[OK] Loaded existing session")
    print(f"  Scam type: {session1_loaded.scamType}")
    print(f"  Messages: {session1_loaded.totalMessagesExchanged}")
    print(f"  History length: {len(session1_loaded.conversationHistory)}")
    
    # Test 4: Multiple sessions
    session2 = load_session("test-session-002")
    print(f"\n[OK] Created second session: {session2.sessionId}")
    
    all_sessions = get_all_sessions()
    print(f"\n[OK] Total active sessions: {len(all_sessions)}")

if __name__ == "__main__":
    test_session_lifecycle()
    print("\n[OK] All session tests completed!")
