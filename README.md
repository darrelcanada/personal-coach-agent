# Personal Coach AI Agent

This project is a multi-persona AI coaching agent that interacts with users via Discord. It is powered by a local Large Language Model (LLM) through Ollama and uses the LangChain framework for its core logic, memory, and dynamic persona management.

## Features

- **Multi-Persona Support**: The agent can adopt different personalities and roles (e.g., "Personal Trainer," "Math Tutor") in different Discord channels, configured via a simple JSON file.
- **Persistent Memory**: Conversation history is stored permanently in a SQLite database, allowing the agent to remember context across restarts. Each channel's conversation is stored independently.
- **Local LLM Integration**: Natively uses a locally-hosted LLM via Ollama (`llama3:8b` by default).
- **Git Version Control**: The project is structured for version control using a `main`/`develop` branch strategy.

---

## Architecture Overview

The system is composed of two primary services that run independently and communicate via an HTTP API. This decoupled design makes the system modular and easier to maintain.

```
+---------------------------------------------+      +------------------------------------------------+
|          User on Discord Client             |      |                                                |
+---------------------------------------------+      |                                                |
                   ^    |                            |                                                |
                   |    v                            |                                                |
+------------------+----|--------------------------+ |                                                |
|   Discord Server (Channels, e.g., #trainer)      | |                                                |
+--------------------------------------------------+ |                                                |
                   ^    |                            |                                                |
                   |    v                            |                                                |
+------------------+----|--------------------------+<----+            +--------------------------------+
|       1. Discord Bot (`discord_bot`)             |     |            |       2. LangChain Agent       |
|--------------------------------------------------|     | POST       |      (`langchain_agent`)         |
| - Listens for user messages in all channels.     |--+  | Response   |--------------------------------|
| - Forwards new messages via HTTP POST to the     |  +->|            | - Listens for messages from bot. |
|   LangChain Agent.                             |     |            | - Loads persona from personas.json.|
| - Exposes an API to receive and post the         |     |            | - Retrieves history from memory.db.|
|   agent's final response back to Discord.        |     |            | - Invokes LLM to get a response. |
+--------------------------------------------------+     |            | - Saves new turn to memory.db.   |
                                                         |            +--------------------------------+
```

---

## Systematic Overview (For LLM/Developer Review)

### Key Components

1.  **`discord_bot/`**
    *   **Purpose**: A stateless bridge between the Discord API and the LangChain agent.
    *   **Technology**: Python, `discord.py`, `fastapi`.
    *   **`bot.py`**: The main script. It runs the Discord client and a FastAPI server that exposes `/send_discord_message/` for the agent to send replies. On receiving a user message, it makes a POST request to the agent's `/message` endpoint.

2.  **`langchain_agent/`**
    *   **Purpose**: The "brain" of the system. It handles all state, memory, and intelligent response generation.
    *   **Technology**: Python, `langchain`, `fastapi`, `SQLAlchemy`, `ollama`.
    *   **`agent.py`**: The main application. Runs a FastAPI server listening on the `/message` endpoint.
    *   **`personas.json`**: A key-value store mapping a Discord `channel_id` (string) to a `system_prompt` (string). This allows for different agent personas in different channels. Includes a `"default"` persona as a fallback.
    *   **`memory.db`**: A SQLite database file that serves as the persistent memory store. LangChain's `SQLChatMessageHistory` uses this file to automatically save and retrieve conversation history, keyed by a `session_id` (which we set as the `channel_id`).

---

## Setup and Installation

### Prerequisites

*   Python 3.10+
*   Git
*   [Ollama](https://ollama.com/) running with a model pulled (e.g., `ollama pull llama3:8b`).
*   A Discord Bot Token.

### Configuration

1.  **Discord Bot**:
    *   In `discord_bot/.env`, set your `DISCORD_TOKEN`.
    *   The `AGENT_WEBHOOK_URL` should point to your LangChain agent's server (default is `http://localhost:8001/message`).
2.  **LangChain Agent**:
    *   In `langchain_agent/personas.json`, map your desired Discord channel IDs to system prompts to define your agent's personas.

### Launch Procedure

You must run both the bot and the agent simultaneously in two separate terminals.

**Terminal 1: Start the Discord Bot**

```bash
# Navigate to the discord_bot directory
cd /path/to/your/project/personal-coach-agent/discord_bot

# Create and activate the virtual environment (only needed once)
python3 -m venv venv
source venv/bin/activate

# Install dependencies (only needed once)
pip install -r requirements.txt

# Run the bot
python bot.py
```

**Terminal 2: Start the LangChain Agent**

```bash
# Navigate to the langchain_agent directory
cd /path/to/your/project/personal-coach-agent/langchain_agent

# Create and activate the virtual environment (only needed once)
python3 -m venv venv
source venv/bin/activate

# Install dependencies (only needed once)
pip install -r requirements.txt

# Run the agent
python agent.py
```

Once both services are running, the agent is live and will respond in your Discord server according to your `personas.json` configuration.
