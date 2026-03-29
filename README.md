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

Create a `.env` file in the project's root directory (`personal-coach-agent/.env`). This file should contain your Discord bot token:

#### `.env` (in project root)

```
DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
```
Replace `YOUR_DISCORD_BOT_TOKEN` with your actual Discord bot token. Other configurations like agent URLs and proactive scheduling are now managed in `config.json`.

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
*   **Proactive Messages:** The Discord bot can schedule and send proactive messages from the LangChain agent to specific Discord channels. These are configured in the `"proactive_scheduling"` section of `config.json`.
*   **Proactive Scheduling:** Adjust the `"proactive_scheduling"` section in `config.json` to define, change the frequency, or content of proactive messages.

*   **Health Data Logging:** You can log your health data by sending messages to the bot starting with "Log health:". The agent will parse the message and store the data in an SQLite database.

    **Examples:**
    *   `Log health: Weight: 75.5kg`
    *   `Log health: Walked 10000 steps`
    *   `Log health: 5km walk`
    *   `Log health: Slept 7.5 hours`
    *   `Log health: Goals: 12000 steps, 30min run`
    *   `Log health: Weight: 75.5kg, Walked 10000 steps, Slept 7.5 hours`

    To view your logged health data, you can use the `sqlite3` CLI tool:
    ```bash
    sqlite3 langchain_agent/memory.db "SELECT * FROM health_log;"
    ```
