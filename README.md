# Personal Coach Agent Project

This project implements a Discord bot that acts as a personal coach, leveraging a LangChain agent with dynamic persona capabilities and proactive messaging. The project is composed of two main components: a `discord_bot` for handling Discord interactions and a `langchain_agent` for AI-driven responses and persona management.

## Project Structure

```
.
├── .gitignore
├── README.md               # This file
├── AGENTS.md               # Agent/coding guidelines
├── config.json             # Shared configuration (personas, scheduling, URLs)
├── discord_bot/            # Discord bot application
│   ├── bot.py              # Main bot + FastAPI server
│   ├── requirements.txt    # Python dependencies
│   └── .env                # Environment variables (bot token only)
└── langchain_agent/       # LangChain agent application
    ├── agent.py            # Main agent + FastAPI server
    ├── memory.db           # SQLite database (gitignored)
    └── requirements.txt    # Python dependencies
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

## Configuration

All configuration is centralized in `config.json` in the project root:

```json
{
  "discord_bot_url": "http://localhost:8000",
  "db_connection_string": "sqlite:///memory.db",
  "conversation_history_limit": 20,
  "personas": {
    "default": "You are a helpful general-purpose AI assistant.",
    "CHANNEL_ID": "Your persona prompt here..."
  },
  "discord_bot": {
    "agent_webhook_url": "http://localhost:8001/message",
    "langchain_agent_url": "http://localhost:8001"
  },
  "proactive_scheduling": {
    "trainer_checkin": {
      "channel_id": 1478120173071499264,
      "interval_seconds": 300,
      "start_hour": 19,
      "end_hour": 22,
      "message_content": null
    }
  }
}
```

### Proactive Scheduling

Each schedule in `proactive_scheduling` supports:
- **channel_id**: Discord channel to send messages to
- **interval_seconds**: How often to check (not how often to send)
- **start_hour/end_hour**: Optional time window (24-hour format)
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
