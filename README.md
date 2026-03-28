# Personal Coach Agent Project

This project implements a Discord bot that acts as a personal coach, leveraging a LangChain agent with dynamic persona capabilities and proactive messaging. The project is composed of two main components: a `discord_bot` for handling Discord interactions and a `langchain_agent` for AI-driven responses and persona management.

## Project Structure

```
.
├── .gitignore
├── README.md               # This file
├── discord_bot/            # Discord bot application
│   ├── bot.py              # Main bot logic
│   ├── requirements.txt    # Python dependencies for the bot
│   └── .env                # Environment variables for bot token and agent URL
└── langchain_agent/        # LangChain agent application
    ├── agent.py            # FastAPI server for agent responses and persona management
    ├── requirements.txt    # Python dependencies for the agent
    └── .env                # Environment variables for agent configuration
```

## Features

*   **Dynamic Personas:** The LangChain agent can adopt different personas based on the Discord channel ID. This allows for specialized interactions (e.g., a "Trainer" persona for fitness-related channels, a "Coding Assistant" for tech channels).
*   **Proactive Messaging:** The Discord bot can schedule and send proactive messages from the LangChain agent to specific Discord channels, enabling features like automated check-ins or reminders.
*   **API-driven Communication:** Both components communicate via FastAPI endpoints, providing a flexible and scalable architecture.
*   **Conversation History:** The LangChain agent maintains conversation history using an SQLite database.

## Setup and Installation

### Prerequisites

*   Python 3.10+
*   A Discord account and a created Discord Bot (see `discord_bot/README.md` for details).

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
deactivate
```

#### For `langchain_agent`:

```bash
cd ../langchain_agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd .. # Return to project root
```

### 3. Configure Environment Variables

Create `.env` files in both `discord_bot/` and `langchain_agent/` directories.

#### `discord_bot/.env`

```
DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
AGENT_WEBHOOK_URL="http://localhost:8001/message" # URL for the langchain_agent's message endpoint
LANGCHAIN_AGENT_URL="http://localhost:8001"     # Base URL for the langchain_agent (for proactive messages)
```
Replace `YOUR_DISCORD_BOT_TOKEN` with your actual Discord bot token.

#### `langchain_agent/.env`

```
# No specific environment variables required by the langchain_agent currently,
# but this file is kept for future extensions (e.g., API keys if external LLMs are used).
```

### 4. Invite the Discord Bot to Your Server

Follow the instructions in `discord_bot/README.md` to invite your bot to your Discord server and grant it necessary permissions.

## Running the Project

To run the entire project, you need to start both the `langchain_agent` and the `discord_bot` in separate terminals.

### 1. Start the `langchain_agent`

From the project root:

```bash
cd langchain_agent
source venv/bin/activate
python agent.py
```
The agent's FastAPI server will be running on `http://0.0.0.0:8001`.

### 2. Start the `discord_bot`

From the project root (in a *new* terminal):

```bash
cd discord_bot
source venv/bin/activate
python bot.py
```
The Discord bot will connect to Discord, and its internal FastAPI server will run on `http://0.0.0.0:8000`. It will also start scheduling proactive messages as configured.

## Usage

Once both components are running:

*   **Chat with the Bot:** Send messages in your Discord channel. The bot will forward them to the `langchain_agent`, which will respond based on the persona configured for that channel.
*   **Proactive Messages:** The bot will automatically send proactive messages from the trainer persona to the pre-configured channel (`1478120173071499264`) every 30 seconds.
*   **Persona Configuration:** Modify the `PERSONAS` dictionary in `langchain_agent/agent.py` to customize existing personas or add new ones for different channel IDs. Refer to `langchain_agent/README.md` for more details.
*   **Proactive Scheduling:** Adjust the `send_proactive_trainer_message` job in `discord_bot/bot.py` to change the frequency or content of proactive messages. Refer to `discord_bot/README.md` for more details.
