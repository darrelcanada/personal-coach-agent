# LangChain Personal Coach Agent

This directory contains the LangChain agent that acts as a personal coach. It runs a FastAPI server, providing AI-driven responses, persona management, and proactive messaging capabilities. It communicates with the Discord bot to send and receive messages.

## Features

*   **Dynamic Personas:** The agent can adopt different personas based on the Discord channel ID. These personas are configured directly within `agent.py` in the `PERSONAS` dictionary, allowing for specialized interactions (e.g., a "Trainer" persona for fitness-related channels). A `default` persona is used if no specific channel ID matches.
*   **Conversation History / Memory:** The agent maintains conversation history using `SQLChatMessageHistory` with an SQLite database (`memory.db`). This ensures that context is preserved across interactions within each Discord channel, up to a configurable limit (`CONVERSATION_HISTORY_LIMIT`). The database file `memory.db` is created automatically upon the first interaction.
*   **LLM Integration:** Utilizes Ollama with the `llama3:8b` model for generating responses.
*   **FastAPI Endpoints:** Exposes endpoints for handling incoming messages from the Discord bot and for triggering proactive messages.
*   **Proactive Messaging Capabilities:** Can generate and send proactive messages when triggered by an external system (like the Discord bot's internal scheduler).

## Setup

1.  **Create a virtual environment and install dependencies:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configure Environment Variables:**
    Create a file named `.env` in this `langchain_agent` directory if you need to override the default `DISCORD_BOT_URL`.
    ```
    # Example .env for langchain_agent
    # DISCORD_BOT_URL="http://localhost:8000" # URL of the Discord bot's FastAPI server (default is http://localhost:8000)
    ```
    `DISCORD_BOT_URL` is crucial for the agent to send responses back to the Discord bot. Other configurations like `DB_CONNECTION_STRING` and `CONVERSATION_HISTORY_LIMIT` are set directly in `agent.py`.

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

Personas are defined in the `PERSONAS` dictionary within `langchain_agent/agent.py`. Each key is a Discord `channel_id` (as a string), and its value is the system prompt for that channel. The `"default"` key provides a fallback persona.

Example:
```python
PERSONAS = {
    "default": "You are a helpful general-purpose AI assistant. Please respond concisely.",
    "1478120173071499264": "You are a cheerful and encouraging personal trainer AI named 'Coach'. Your goal is to help users achieve their fitness goals with positive reinforcement."
}
```
To customize or add new personas, modify this dictionary.

### Conversation History Limit

The `CONVERSATION_HISTORY_LIMIT` constant in `langchain_agent/agent.py` defines the number of past messages to include in the LLM's context for each conversation. Adjust this value to control the agent's memory length.