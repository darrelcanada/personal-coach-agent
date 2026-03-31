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
| **Proactive Reminders** | Day-based workout reminders at scheduled times |
| **User Profiles** | Store age, height, goals for personalized coaching |
| **Conversation Memory** | SQLite-backed chat history per channel |

## Quick Start

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: LangChain Agent
cd langchain_agent && source venv/bin/activate && python agent.py

# Terminal 3: Discord Bot
cd discord_bot && source venv/bin/activate && python bot.py

# Optional: Persona UI
cd persona_ui && source venv/bin/activate && python server.py
```

See `discord_bot/README.md` for Discord bot setup instructions.

## Workout Tracking

The project includes a structured walking routine with two workout types:

### Workout Schedule

| Day | Type | Description |
|-----|------|-------------|
| Monday | Jump Rope | 4km walk + 25 sets of 35 skips (30s on/10s rest) |
| Tuesday | Body Weight | 4km walk + bodyweight exercises |
| Wednesday | Jump Rope | 4km walk + 25 sets of 35 skips |
| Thursday | Body Weight | 4km walk + bodyweight exercises |
| Friday | Jump Rope | 4km walk + 25 sets of 35 skips |
| Saturday | Body Weight | 4km walk + bodyweight exercises |
| Sunday | Rest | No workout |

### Default Body Weight Exercises

- Push-ups: 4 sets of 10
- Planks: 3 sets of 30 seconds
- Squats: 3 sets of 15
- Lunges, Mountain Climbers, Burpees, etc.

### Logging Workouts

**Jump Rope Days:**
```
Log workout: Jump rope night
Log workout: Jump rope day, 4km walk, 25 sets of 35 skips
```

**Body Weight Days:**
```
Log workout: Body weight day, push-ups 4x10, planks 3x30sec, squats 3x15
Log workout: Body weight, lunges 3x12, mountain climbers 3x20
```

**Partial Completion:**
```
Log workout: Jump rope night, only did 20 sets
Log workout: Body weight, push-ups 4x10 (only 3 sets)
```

### Querying Workout History

```
How many workouts did I do this week?
How many jump rope workouts this month?
How many body weight exercises last week?
Show my workout history
```

### Workout Reminders

Ask the bot:
```
What's tonight's workout?
What type of workout is today?
```

Proactive reminders are sent at scheduled times (configured per persona in `config.json`).

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
      "proactive_scheduling": {
        "enabled": true,
        "interval_seconds": 7200,
        "time_window": { "start_hour": 18, "end_hour": 19 },
        "message_content": "WORKOUT_REMINDER"
      }
    }
  }
}
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
