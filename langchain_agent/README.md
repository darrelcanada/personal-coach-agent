# LangChain Personal Coach Agent

This directory contains the LangChain agent that acts as a personal coach. It runs a FastAPI server, providing AI-driven responses, persona management, and proactive messaging capabilities. It communicates with the Discord bot to send and receive messages.

## Features

*   **Dynamic Personas:** The agent can adopt different personas based on the Discord channel ID. These personas are configured in the `config.json` file in the project's root directory, allowing for specialized interactions (e.g., a "Trainer" persona for fitness-related channels). A `default` persona is used if no specific channel ID matches.
*   **Conversation History / Memory:** The agent maintains conversation history using `SQLChatMessageHistory` with an SQLite database (`memory.db`). This ensures that context is preserved across interactions within each Discord channel, up to a configurable limit (`CONVERSATION_HISTORY_LIMIT`). The database file `memory.db` is created automatically upon the first interaction.
*   **LLM Integration:** Utilizes Ollama with the `llama3:8b` model for generating responses.
*   **FastAPI Endpoints:** Exposes endpoints for handling incoming messages from the Discord bot and for triggering proactive messages.
*   **Proactive Messaging Capabilities:** Can generate and send proactive messages when triggered by an external system (like the Discord bot's internal scheduler).

## Data Storage

*   **Conversation History / Memory:** The agent maintains conversation history using `SQLChatMessageHistory` with an SQLite database (`memory.db`). This ensures that context is preserved across interactions within each Discord channel, up to a configurable limit (`CONVERSATION_HISTORY_LIMIT`). The database file `memory.db` is created automatically upon the first interaction.

*   **Health Data Logging:** The agent now supports logging health data directly from Discord messages. This data is stored in a separate `health_log` table within the same `memory.db` SQLite database.

    The `health_log` table schema:
    ```
    CREATE TABLE IF NOT EXISTS health_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        log_date DATE NOT NULL,
        weight REAL,
        walking_steps INTEGER,
        walking_distance REAL,
        sleep_duration_hours REAL,
        daily_goals_steps INTEGER,
        daily_goals_workout TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ```
    Users can log data by starting their message with "Log health:". The agent uses regex parsing to extract metrics like weight, walking distance/steps, sleep duration, and daily goals. If successful, it confirms the log to the user.

*   **Health Data Querying:** The agent can also process queries about logged health data. Users can ask questions like "How much did I walk this week?" or "What is my weight today?". The agent will attempt to parse the metric and time period from the query, retrieve relevant data from the `health_log` table, and provide a summary.

To view your health-related data directly in the database, you can use the `sqlite3` CLI tool from the project root:
```bash
# View all entries in the health_log table
sqlite3 langchain_agent/memory.db "SELECT * FROM health_log;"

# View all entries in the user_profile table
sqlite3 langchain_agent/memory.db "SELECT * FROM user_profile;"
```

## Architectural Flow

The `langchain_agent` operates as a FastAPI application that integrates with a Discord bot.
1.  **Incoming Messages:** The Discord bot forwards user messages to the agent's `/message` endpoint.
2.  **Persona Selection:** Based on the `channel_id` from the incoming message, the agent selects an appropriate persona from its `PERSONAS` dictionary.
3.  **Conversation Context:** The agent retrieves the conversation history for that channel from its SQLite memory.
4.  **LLM Invocation:** The selected persona's system prompt, the conversation history, and the new user input are fed to the Ollama `llama3:8b` model to generate a response.
5.  **Response to Discord:** The agent sends its generated response back to the Discord bot's `/send_discord_message/` endpoint.
6.  **Proactive Messages:** External systems (such as the Discord bot's internal scheduler) can trigger proactive messages by calling the agent's `/proactive_message` endpoint. The agent then follows steps 2-5 to generate and send a proactive message.

## Running the Agent

To start the agent's server, run:
```bash
venv/bin/python agent.py
```
The agent will be running on `http://0.0.0.0:8001`. Ensure these URLs are correctly configured in `config.json` under `discord_bot`:
```json
"discord_bot": {
  "agent_webhook_url": "http://localhost:8001/message",
  "langchain_agent_url": "http://localhost:8001"
}
```

## Endpoints

### 1. `/message`

*   **Method**: `POST`
*   **Description**: Receives user-initiated messages from the Discord bot, processes them using LangChain, and sends a response back to the Discord bot.
*   **Payload**:
    ```json
    {
        "channel_id": "string",
        "author": "string",
        "user_id": "string",
        "content": "string"
    }
    ```
    *   `user_id` is required for health data logging and user profile management.

### 2. `/proactive_message`

*   **Method**: `POST`
*   **Description**: Receives requests from external systems (e.g., Discord bot scheduler) to generate and send a proactive message to a specified Discord channel.
*   **Payload**:
    ```json
    {
        "channel_id": "string",
        "message_content": "string | null" // Optional: custom content for the proactive message
    }
    ```
    If `message_content` is not provided, a default proactive prompt is used.

## Configuration

All configuration is in `config.json` (project root). The config is organized by persona, with each persona having its own settings including proactive scheduling.

### Config Structure

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
      "prompt": "You are a helpful assistant."
    },
    "CHANNEL_ID": {
      "name": "Persona Name",
      "description": "What this persona does.",
      "prompt": "Your persona prompt here...",
      "proactive_scheduling": {
        "enabled": true,
        "interval_seconds": 300,
        "time_window": { "start_hour": 19, "end_hour": 22 },
        "message_content": "Custom prompt or null for default."
      }
    }
  }
}
```

### Key Settings

- **prompt**: The system prompt for the persona
- **proactive_scheduling.enabled**: Set to `true` to enable automatic check-ins
- **proactive_scheduling.interval_seconds**: How often to check (not frequency of messages)
- **proactive_scheduling.time_window**: Restrict messages to specific hours
- **proactive_scheduling.message_content**: Custom prompt or `null` for default check-in