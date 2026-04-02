# Unique System Prompts for Proactive vs Reactive Responses

## Problem Statement

Currently, both proactive (scheduled check-ins) and reactive (user messages) responses use the same system prompt from `config.json`. This means the persona behaves identically regardless of whether it's initiating a conversation or responding to one.

## Current Behavior

```
config.json:  "prompt": "You are a professional trainer..."
                                    ↓
        Both PROACTIVE & REACTIVE use same prompt
```

## Proposed Solution

Allow separate system prompts in `config.json`:

```json
"personas": {
  "CHANNEL_ID": {
    "name": "Trainer",
    "description": "...",
    "prompt_reactive": "You are a professional trainer. Respond to user questions...",
    "prompt_proactive": "You are a proactive wellness coach. Send encouraging check-ins...",
    "proactive_scheduling": [...]
  }
}
```

### Use Cases

1. **Tone Differences**
   - Reactive: Detailed, instructional, educational
   - Proactive: Brief, encouraging, motivational

2. **Context Differences**
   - Reactive: Has full conversation history available
   - Proactive: Should be standalone, no context required

3. **Length Differences**
   - Reactive: Can be lengthy explanations
   - Proactive: Should be short and scannable

4. **Behavioral Differences**
   - Reactive: Answers questions, provides guidance
   - Proactive: Sends reminders, checks in, motivates

## Implementation Options

### Option 1: Separate Fields (Recommended)
Add `prompt_reactive` and `prompt_proactive` fields to config.

```python
# In agent.py
if is_proactive:
    persona_prompt = _get_persona_prompt(channel_id, mode="proactive")
else:
    persona_prompt = _get_persona_prompt(channel_id, mode="reactive")
```

### Option 2: Prompt Templates
Keep single prompt with placeholders:

```json
"prompt": "You are a {mode} trainer. For reactive: be detailed. For proactive: be brief."
```

### Option 3: Fallback Pattern
If only `prompt` exists, use for both. If separate fields exist, use those.

## Priority

Medium - Useful for personas that need significantly different behaviors for check-ins vs. Q&A

## Related Files

- `langchain_agent/agent.py` - `_get_persona_prompt()` function
- `config.json` - Persona configuration
- `persona_ui/app.js` - UI form for editing prompts
