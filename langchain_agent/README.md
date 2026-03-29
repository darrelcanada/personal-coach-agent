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
The agent will be running on `http://0.0.0.0:8001`. Ensure this URL is correctly configured as `AGENT_WEBHOOK_URL` and `LANGCHAIN_AGENT_URL` in your `discord_bot/.env` file.

## Endpoints

### 1. `/message`

*   **Method**: `POST`
*   **Description**: Receives user-initiated messages from the Discord bot, processes them using LangChain, and sends a response back to the Discord bot.
*   **Payload**:
    ```json
    {
        "channel_id": "string",
        "author": "string",
        "content": "string"
    }
    ```

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

### Personas

Personas are now configured via the `config.json` file located in the project's root directory. This external JSON file holds a dictionary under the "personas" key, where each key is a Discord `channel_id` (as a string), and its value is the system prompt for that channel. The `"default"` key provides a fallback persona if a specific channel ID is not found.

Example `config.json` structure (relevant section):
```json
{
  "personas": {
    "default": "You are a helpful general-purpose AI assistant. Please respond concisely.",
    "1478120173071499264": "You are a cheerful and encouraging personal trainer AI named 'Coach'. Your goal is to help users achieve their fitness goals with positive reinforcement."
  }
}
```
If `config.json` or its "personas" section is not found or is invalid, the agent will gracefully fall back to a hardcoded default persona to ensure continuous operation. To customize or add new personas, modify this `config.json` file.

### Conversation History Limit

The `CONVERSATION_HISTORY_LIMIT` is now configured in `config.json` in the project root. This value defines the number of past messages to include in the LLM's context for each conversation. Adjust this value to control the agent's memory length.

### Database Connection String

The `DB_CONNECTION_STRING` for the SQLite database is also configured in `config.json`. By default, it uses `sqlite:///memory.db`.