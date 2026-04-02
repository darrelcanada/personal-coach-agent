# Future Features

This document outlines planned features for future development.

---

## Conversation History Management

### Problem Statement

During development and testing, the LLM may generate "toxic" or low-quality responses that get stored in the conversation history database. These problematic messages (refusal responses, error messages, test "Message Received" replies, emotionally unstable AI responses) pollute the chat history and degrade future interactions.

**Example problematic responses stored in history:**
- "I cannot provide a workout routine that may cause injury or exacerbate existing medical conditions..."
- "I cannot continue a conversation that is overly emotional or repetitive."
- "Message Received" (test responses)
- "*AI Trainer's eyes well up with tears*" (inappropriate emotional responses)

When these messages are included in the chat history context, the LLM uses them as conversation baseline, causing subsequent responses to be similarly degraded.

### Current Mitigation

Manual SQLite deletion of specific message IDs after identifying problematic entries via:
```bash
sqlite3 langchain_agent/memory.db "SELECT id, json_extract(message, '$.type') as type, ... FROM message_store WHERE session_id='CHANNEL_ID' ORDER BY id DESC LIMIT 40;"
```

### Proposed Solutions

#### Option 1: Response Quality Filter (Recommended)
**Implementation:** Add a filter in `langchain_agent/agent.py` that evaluates each AI response before adding to history.

**Logic:**
```python
# Pseudocode
def should_store_response(response):
    # Skip storing if response contains refusal patterns
    refusal_patterns = [
        "cannot provide",
        "consult a healthcare professional",
        "cannot continue a conversation",
        "overly emotional"
    ]
    
    # Skip test responses
    if response == "Message Received":
        return False
    
    # Skip responses with excessive emotional markers
    emotional_markers = ["*gets a bit emotional*", "*well up with tears*"]
    
    return True
```

**Pros:** Automatic, transparent to users
**Cons:** Requires code change

---

#### Option 2: Conversation Editing via Discord Command
**Implementation:** Add bot commands to manage history:
- `!history` - Show last N messages
- `!history delete <id>` - Delete specific message
- `!history clear` - Clear all history (with confirmation)
- `!history export` - Export to JSON

**Pros:** User-controlled, intuitive
**Cons:** More complex code, Discord-specific

---

#### Option 3: Semantic Memory Layer
**Implementation:** Store key learned facts separately from raw chat:
- **Factual memory:** User profile, preferences, goals (structured table)
- **Context memory:** Recent relevant conversation (limited)
- **Episodic memory:** Full history (archived, not used for context)

**Pros:** More targeted context, better personalization
**Cons:** Significant architecture change

---

#### Option 4: Frozen Baseline
**Implementation:** Mark specific messages as "pinned" or "baseline" - these always stay in context, while newer messages can be pruned.

**Pros:** Stable foundation, user control
**Cons:** Requires UI or command to pin messages

---

## Related Files

- `langchain_agent/agent.py` - Main agent logic, handles message processing
- `langchain_agent/memory.db` - SQLite database with message_store table
- `config.json` - Persona configurations

---

## Priority Recommendation

1. **Immediate:** Continue manual pruning for existing bad entries
2. **Short-term:** Implement Option 1 (Response Quality Filter) - low effort, high impact
3. **Medium-term:** Implement Option 2 (Conversation Editing) - adds user control
4. **Long-term:** Consider Option 3 (Semantic Memory) for deeper personalization
