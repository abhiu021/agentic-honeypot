# End-to-End Readiness – Agentic Honeypot

**Status: READY** – Full pipeline, API, session, and tests are in place.

---

## What’s in place

| Layer | Component | Status |
|-------|-----------|--------|
| **API** | FastAPI app, `/health`, `/api/honeypot`, CORS, request logging | ✅ |
| **Auth** | `x-api-key` header (see `.env` / `config.settings.API_KEY`) | ✅ |
| **Orchestration** | `process_message()`: Detection → Kill chain → Strategy → Engagement → Ethics → Extraction → session update | ✅ |
| **Agents** | Detection, Strategic, Engagement, Extraction, Ethics | ✅ |
| **Kill chains** | UPI_FRAUD, ACCOUNT_TAKEOVER, FAKE_CUSTOMER_SUPPORT, PHISHING, INVESTMENT_SCAM, FAKE_OFFER | ✅ |
| **Session** | In-memory (Redis optional via `REDIS_URL`) | ✅ |
| **Intelligence** | Merge across turns (`IntelligenceAccumulator`), stored in session | ✅ |
| **Ethics gate** | Every response validated; violations → safe fallback | ✅ |
| **Termination** | Message count ≥20, kill chain completion ≥95%, “are you a bot”, stage ≥6 | ✅ |
| **Tests** | Orchestrator (12), Ethics (19), Engagement (19), Extraction (15), Kill chains (7) | ✅ 72+ passing |

---

## How to run

### 1. Install and env

```bash
pip install -r requirements.txt
# Copy .env.example to .env and set API_KEY, optional GEMINI_API_KEY or GROQ_API_KEY
```

### 2. Start API

```bash
python main.py
# or: uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Call the honeypot

```bash
# Health (no auth)
curl http://localhost:8000/health

# Honeypot (requires x-api-key; default in .env: sk_test_honeypot_2026)
curl -X POST http://localhost:8000/api/honeypot \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk_test_honeypot_2026" \
  -d '{
    "sessionId": "my-session-001",
    "message": {"sender": "scammer", "text": "Your UPI is blocked. Share test@paytm for verification."},
    "conversationHistory": []
  }'
```

Response includes: `scamDetected`, `scamConfidenceScore`, `engagementMetrics`, `killChainAnalysis`, `extractedIntelligence`, `agentResponse` (message to send back), `agentNotes`.

### 4. Run tests

```bash
# Core pipeline + agents
pytest tests/test_orchestrator.py tests/test_ethics_agent.py tests/test_engagement_agent.py tests/test_extraction_agent.py tests/test_kill_chains.py -v

# All tests (excluding Redis if not running)
pytest tests/ -v --ignore=tests/test_redis_session_manager.py
```

---

## Optional / not required for E2E

- **LLM** – Engagement and (optionally) kill chain work without it; fallbacks and rule-based path used.
- **Redis** – Sessions work in-memory; set `REDIS_URL` for persistence.
- **GUVI callback** – Termination logic exists; actual HTTP callback to GUVI is not implemented (stub or add when URL/contract is fixed).

---

## Request/response (GUVI-style)

- **Request:** `sessionId`, `message` (sender, text), `conversationHistory` (list of Message), optional `metadata` (channel, etc.).
- **Response:** `status`, `scamDetected`, `scamConfidenceScore`, `engagementMetrics`, `killChainAnalysis`, `extractedIntelligence`, `agentResponse` (message, responseGeneratedBy, personaUsed, intentionBehindResponse), `agentNotes`.

The service is ready for end-to-end use: run the API, send scammer messages to `/api/honeypot`, and use the returned `agentResponse.message` as the honeypot reply.
