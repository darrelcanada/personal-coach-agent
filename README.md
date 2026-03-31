# Personal Coach Agent Project

This project implements a Discord bot that acts as a personal coach, leveraging a LangChain agent with dynamic persona capabilities and proactive messaging. The project is composed of two main components: a `discord_bot` for handling Discord interactions and a `langchain_agent` for AI-driven responses and persona management.

## Project Structure

```
.
├── .gitignore
├── README.md               # This file
├── AGENTS.md               # Agent/coding guidelines
├── config.json             # Shared configuration (personas, scheduling, URLs)
├── discord_bot/           # Discord bot application
│   ├── bot.py             # Main bot + FastAPI server
│   ├── requirements.txt   # Python dependencies
│   └── .env               # Environment variables (bot token only)
├── langchain_agent/       # LangChain agent application
│   ├── agent.py           # Main agent + FastAPI server
│   ├── memory.db          # SQLite database (gitignored)
│   └── requirements.txt   # Python dependencies
└── persona_ui/            # Persona configuration web interface
    ├── server.py          # Web server
    ├── index.html         # Main page
    ├── styles.css         # Styling
    ├── app.js             # Frontend logic
    └── requirements.txt   # Python dependencies
```

## Features

*   **Dynamic Personas:** The LangChain agent can adopt different personas based on the Discord channel ID. This allows for specialized interactions (e.g., a "Trainer" persona for fitness-related channels, a "Coding Assistant" for tech channels).
*   **Proactive Messaging:** The Discord bot can schedule and send proactive messages from the LangChain agent to specific Discord channels, enabling features like automated check-ins or reminders.
*   **Time Window Scheduling:** Proactive messages can be restricted to specific hours (e.g., 19:00-22:00).
*   **API-driven Communication:** Both components communicate via FastAPI endpoints, providing a flexible and scalable architecture.
*   **Conversation History:** The LangChain agent maintains conversation history using an SQLite database.
*   **Health Data Logging:** Users can log health metrics (weight, steps, sleep) via Discord messages.
*   **User Profile Management:** Users can set profile data (age, height, activity level) for personalized coaching.

## Setup and Installation

### Prerequisites

*   Python 3.10+
*   A Discord account and a created Discord Bot (see `discord_bot/README.md` for details).
*   Ollama running locally with the `llama3:8b` model.

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd personal-coach-agent
```

### 2. Set Up Python Virtual Environments

Each component (`discord_bot` and `langchain_agent`) has its own virtual environment and dependencies.

#### For `discord_bot`:

```bash
cd discord_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### For `langchain_agent`:

```bash
cd langchain_agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the `discord_bot` directory (`discord_bot/.env`):

```
DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
```

Other configurations (agent URLs, personas, scheduling) are managed in `config.json`.

### 4. Invite the Discord Bot to Your Server

Follow the instructions in `discord_bot/README.md` to invite your bot to your Discord server and grant it necessary permissions.

## Running the Project

To run the entire project, you need to start both the `langchain_agent` and the `discord_bot` in separate terminals.

### 1. Start Ollama (required for langchain_agent)

```bash
ollama serve  # In one terminal
```

### 2. Start the `langchain_agent`

```bash
cd langchain_agent
source venv/bin/activate
python agent.py  # Runs on http://0.0.0.0:8001
```

### 3. Start the `discord_bot`

```bash
cd discord_bot
source venv/bin/activate
python bot.py  # Runs on http://0.0.0.0:8000
```

### 4. Start the `persona_ui` (optional)

```bash
cd persona_ui
source venv/bin/activate
pip install -r requirements.txt
python server.py  # Runs on http://0.0.0.0:8002
```

Open `http://localhost:8002` to manage personas via web UI.

## Configuration

All configuration is centralized in `config.json` in the project root. The config is organized by persona, with proactive scheduling per-persona.

```json
{
  "_meta": { "version": "1.0" },
  "_database": {
    "db_connection_string": "sqlite:///memory.db",
    "conversation_history_limit": 20
  },
  "_discord": {
    "bot_url": "http://localhost:8000",
    "agent_webhook_url": "http://localhost:8001/message",
    "langchain_agent_url": "http://localhost:8001"
  },
  "personas": {
    "default": {
      "prompt": "You are a helpful general-purpose AI assistant."
    },
    "CHANNEL_ID": {
      "name": "Persona Name",
      "description": "What this persona does.",
      "prompt": "Your persona prompt here...",
      "proactive_scheduling": {
        "enabled": true,
        "interval_seconds": 300,
        "time_window": { "start_hour": 19, "end_hour": 22 },
        "message_content": null
      }
    }
  }
}
```

### Config Sections

- **_meta**: Version and metadata
- **_database**: Database connection and history limit
- **_discord**: Discord bot and agent URLs
- **personas**: Each persona keyed by Discord channel ID, with:
  - **name**: Display name for logging
  - **description**: Human-readable description
  - **prompt**: System prompt for the LLM
  - **proactive_scheduling**: Optional per-persona scheduling

### Proactive Scheduling (per-persona)

Each persona can have its own proactive schedule:
- **enabled**: Set to `true` to enable
- **interval_seconds**: How often to check (not frequency of messages)
- **time_window**: Optional `{start_hour, end_hour}` to restrict to specific hours
- **message_content**: Custom prompt or `null` for default check-in

## Usage

### Chat with the Bot

Send messages in any Discord channel the bot has access to. The agent responds based on the persona configured for that channel.

### Health Data Logging

Start your message with "Log health:":

```
Log health: Weight: 75.5kg
Log health: Walked 10000 steps
Log health: 5km walk
Log health: Slept 7.5 hours
Log health: Goals: 12000 steps, 30min run
```

### Health Data Querying

```
How much did I walk this week?
What is my weight today?
How many steps did I take yesterday?
```

### User Profile

```
Set profile: Age: 30, Sex: Male, Height: 175cm, Goal weight: 70kg, Activity: moderate
Update profile: Age: 31, Activity: active
```

### Database Queries

To view data directly in the database:

```bash
sqlite3 langchain_agent/memory.db "SELECT * FROM health_log;"
sqlite3 langchain_agent/memory.db "SELECT * FROM user_profile;"
```
