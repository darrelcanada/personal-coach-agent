# Personal Coach Agent Project

A Discord bot with AI-powered personal coaching via LangChain. Multiple personas handle fitness tracking, workout logging, health data, and general assistance.

## Project Structure

```
.
├── .gitignore
├── README.md               # This file
├── AGENTS.md               # Agent/coding guidelines
├── config.json             # Centralized configuration
├── discord_bot/           # Discord bot + FastAPI (port 8000)
├── langchain_agent/       # LangChain agent + FastAPI (port 8001)
└── persona_ui/            # Persona config web UI (port 8002)
```

## Features

| Feature | Description |
|---------|-------------|
| **Dynamic Personas** | AI personas per Discord channel (Trainer, Math Tutor, etc.) |
| **Workout Tracking** | Structured walking routine with jump rope and bodyweight exercises |
| **Health Logging** | Log weight, steps, sleep via Discord |
| **Proactive Reminders** | Scheduled check-in messages with time windows |
| **User Profiles** | Store age, height, goals for personalized coaching |
| **Conversation Memory** | SQLite-backed chat history per channel |
| **Web UI** | Visual interface for managing personas and schedules |

## Quick Start

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: LangChain Agent
cd langchain_agent && source venv/bin/activate && python agent.py

# Terminal 3: Discord Bot
cd discord_bot && source venv/bin/activate && python bot.py

# Terminal 4: Persona UI (optional)
cd persona_ui && source venv/bin/activate && python server.py
```

Then open http://localhost:8002 in your browser.

## Web UI (Persona Management)

The Persona UI runs on port 8002 and provides:
- View all personas
- Edit persona details (name, description, prompt)
- Add/edit/delete proactive check-in schedules
- Pause/resume schedules instantly
- Reload bot to apply changes

### Check-in Schedule Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier for the schedule |
| `name` | Display name (e.g., "Workout Reminder") |
| `enabled` | Whether the schedule is active in config (true/false) |
| `interval_seconds` | How often to send messages (e.g., 7200 = 2 hours) |
| `time_window` | Hour range when messages can be sent |
| `message_content` | The message to send |

### Pause/Resume Behavior

- **Pause**: Instantly stops the scheduler from sending messages. State is maintained in memory until the next reload.
- **Resume**: Instantly resumes the scheduler.
- **Reload**: Re-reads config.json and recreates all scheduled jobs. If `enabled: false` in config, the job starts paused.

## Configuration

All settings in `config.json`:

```json
{
  "_database": { "db_connection_string": "sqlite:///memory.db" },
  "_discord": { "bot_url": "http://localhost:8000" },
  "personas": {
    "CHANNEL_ID": {
      "name": "Persona Name",
      "prompt": "System prompt...",
      "proactive_scheduling": [
        {
          "id": "workout_reminder",
          "name": "Workout Reminder",
          "enabled": true,
          "interval_seconds": 7200,
          "time_window": { "start_hour": 18, "end_hour": 19 },
          "message_content": "WORKOUT_REMINDER"
        }
      ]
    }
  }
}
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET | Get full config |
| `/api/config` | PUT | Update persona |
| `/api/config/reload` | POST | Reload bot schedules |
| `/api/schedules` | GET | Get all active schedules |
| `/api/schedules/{job_id}/pause` | POST | Pause a schedule |
| `/api/schedules/{job_id}/resume` | POST | Resume a schedule |
| `/api/schedules/{job_id}/remove` | POST | Remove a schedule |

## Health Data Logging

```
Log health: Weight: 75.5kg
Log health: Walked 10000 steps
Log health: Slept 7.5 hours
```

**Querying:**
```
How much did I walk this week?
What is my weight today?
```

## User Profile

```
Set profile: Age: 30, Sex: Male, Height: 175cm, Goal weight: 70kg, Activity: moderate
Update profile: Age: 31, Activity: active
```

## Database

SQLite database at `langchain_agent/memory.db`:

```bash
sqlite3 langchain_agent/memory.db "SELECT * FROM workout_log;"
sqlite3 langchain_agent/memory.db "SELECT * FROM jump_rope_session;"
sqlite3 langchain_agent/memory.db "SELECT * FROM bodyweight_exercise;"
sqlite3 langchain_agent/memory.db "SELECT * FROM health_log;"
sqlite3 langchain_agent/memory.db "SELECT * FROM user_profile;"
```
