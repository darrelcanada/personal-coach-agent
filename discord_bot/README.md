# Discord Cron and API Bot

This project is a Python-based Discord bot designed to facilitate communication between Discord and an external LangChain agent. It features message monitoring, a built-in scheduler for proactive messages, and a FastAPI-powered API for external services to interact with Discord.

## Features

- **Discord Message Monitoring:** The bot listens to messages in all channels it has access to. User messages (excluding its own and `!hello` commands) are forwarded to the configured LangChain agent for processing.
- **`!hello` Command:** A simple command. If you type `!hello`, the bot will respond with `Hello <your_username>!`.
- **API for External Agents:** A FastAPI server runs alongside the bot, exposing endpoints for sending immediate messages and scheduling recurring messages.
- **Asynchronous Operations:** Leverages `asyncio` for efficient handling of Discord events and `APScheduler` for concurrent task scheduling.
- **Proactive Check-ins:** Scheduled messages with minute-precision time windows
- **Pause/Resume:** Instant toggle of schedules via API, with config.json persistence

## Project Structure

```
discord_bot/
├── venv/                 # Python virtual environment
├── bot.py                # Main application file containing bot logic, scheduler, and FastAPI server
├── requirements.txt      # Project dependencies
├── .env                  # Environment variables (for bot token only)
└── bot.log               # Server log output

../config.json            # Shared configuration (personas, scheduling, URLs)
```

## Setup and Installation

### Prerequisites

- Python 3.10+
- A Discord account and a created Discord Bot application in the [Discord Developer Portal](https://discord.com/developers/applications).
- The `langchain_agent` running (typically on `http://localhost:8001`).

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd discord_bot
```

### 2. Set Up Virtual Environment and Install Dependencies

Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Get Your Discord Bot Token and Configure Intents

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a **New Application**.
3. Navigate to the **Bot** tab and click **Add Bot**.
4. Under the bot's username, click **Reset Token** (or **Copy Token** if you have one already) and copy the token.
5. In the **Bot** tab, enable the **Message Content Intent** under "Privileged Gateway Intents". This is crucial for the bot to read message content.

### 4. Configure Environment Variables

1. Create a file named `.env` in the `discord_bot` directory.
2. Add your bot token to this file:
   ```
   DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
   ```
   - Replace `YOUR_DISCORD_BOT_TOKEN` with the token you copied.
   - The LangChain agent URLs are configured in `config.json` (in the project root), not in `.env`.

### 5. Invite the Bot to Your Server

1. In the Discord Developer Portal, go to **OAuth2 > URL Generator**.
2. Select the `bot` scope.
3. Under **Bot Permissions**, grant the bot `Read Message History`, `Send Messages`, and `View Channels`. Make sure these permissions are enabled.
4. Copy the generated URL, paste it into your browser, and select your server to invite the bot.

## Running the Bot

```bash
source venv/bin/activate
python bot.py
```

The bot connects to Discord and the FastAPI server runs on `http://0.0.0.0:8000`.

## Startup Log

When the bot starts, you'll see logs like:
```
[Trainer] Scheduled 'Workout Reminder' every 2h (18:00-19:00)
[Trainer] Scheduled 'Daily Thought' every 5m (8:55-20:00)
[Icelandic Teacher] Scheduled 'Practice Reminder' every 12m (12:00-17:00)
Scheduler started.
```

## Proactive Scheduling

Proactive messages are configured per-persona in `config.json`. Each persona can have multiple schedules:

```json
"personas": {
  "CHANNEL_ID": {
    "name": "Trainer",
    "prompt": "You are a professional trainer...",
    "proactive_scheduling": [
      {
        "id": "workout_reminder",
        "name": "Workout Reminder",
        "enabled": true,
        "interval_seconds": 7200,
        "time_window": {
          "start_hour": 18,
          "start_minute": 0,
          "end_hour": 19,
          "end_minute": 0
        },
        "message_content": "WORKOUT_REMINDER"
      }
    ]
  }
}
```

### Settings

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `name` | Display name |
| `enabled` | Initial state (true/false) |
| `interval_seconds` | How often to check (not frequency of messages) |
| `time_window.start_hour` | Start hour (0-23) |
| `time_window.start_minute` | Start minute (0-59) |
| `time_window.end_hour` | End hour (0-23) |
| `time_window.end_minute` | End minute (0-59) |
| `message_content` | Custom message or `WORKOUT_REMINDER` |

## API Endpoints

The FastAPI server runs on `http://0.0.0.0:8000`.

### Schedule Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/schedules` | GET | Get all active schedules |
| `/api/schedules/{job_id}/pause` | POST | Pause a schedule |
| `/api/schedules/{job_id}/resume` | POST | Resume a schedule |
| `/api/schedules/{job_id}/remove` | POST | Remove a schedule |
| `/api/schedules/reload` | POST | Reload schedules from config |

### Messaging

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/send_discord_message/` | POST | Send immediate message to channel |
| `/schedule_discord_message/` | POST | Schedule recurring message |

### Examples

```bash
# Pause a schedule
curl -X POST http://localhost:8000/api/schedules/proactive_workout_reminder/pause

# Resume a schedule
curl -X POST http://localhost:8000/api/schedules/proactive_workout_reminder/resume

# Get all schedules
curl http://localhost:8000/api/schedules

# Send a message
curl -X POST "http://localhost:8000/send_discord_message/?channel_id=123&message_content=Hello!"
```

**Important:** Ensure your `langchain_agent` is running for proactive messages to be generated.
