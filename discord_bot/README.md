# Discord Cron and API Bot

This project is a Python-based Discord bot designed to facilitate communication between Discord and an external LangChain agent. It features message monitoring, a built-in scheduler for proactive messages, and a FastAPI-powered API for external services to interact with Discord.

## Features

*   **Discord Message Monitoring:** The bot listens to messages in all channels it has access to. User messages (excluding its own and `!hello` commands) are forwarded to the configured LangChain agent for processing.
*   **`!hello` Command:** A simple command. If you type `!hello`, the bot will respond with `Hello <your_username>!`.
*   **API for External Agents:** A FastAPI server runs alongside the bot, exposing endpoints for sending immediate messages and scheduling recurring messages.
*   **Asynchronous Operations:** Leverages `asyncio` for efficient handling of Discord events and `APScheduler` for concurrent task scheduling.

## Project Structure

```
discord_bot/
├── venv/                 # Python virtual environment
├── bot.py                # Main application file containing bot logic, scheduler, and FastAPI server
├── requirements.txt      # Project dependencies
└── .env                  # Environment variables (for bot token only)

../config.json            # Shared configuration (personas, scheduling, URLs)
```

## Setup and Installation

### Prerequisites

*   Python 3.10+
*   A Discord account and a created Discord Bot application in the [Discord Developer Portal](https://discord.com/developers/applications).
*   The `langchain_agent` running (typically on `http://localhost:8001`).

### 1. Clone the Repository

(Assuming you have this project in a git repository)
```bash
git clone <your-repo-url>
cd discord_bot
```

### 2. Set Up Virtual Environment and Install Dependencies

Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```
Install the required packages:
```bash
pip install -r requirements.txt
```

### 3. Get Your Discord Bot Token and Configure Intents

1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Create a **New Application**.
3.  Navigate to the **Bot** tab and click **Add Bot**.
4.  Under the bot's username, click **Reset Token** (or **Copy Token** if you have one already) and copy the token.
5.  In the **Bot** tab, enable the **Message Content Intent** under "Privileged Gateway Intents". This is crucial for the bot to read message content.

### 4. Configure Environment Variables

1.  Create a file named `.env` in the `discord_bot` directory.
2.  Add your bot token to this file:
    ```
    DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
    ```
    *   Replace `YOUR_DISCORD_BOT_TOKEN` with the token you copied.
    *   The LangChain agent URLs are configured in `config.json` (in the project root), not in `.env`.

### 5. Invite the Bot to Your Server

1.  In the Discord Developer Portal, go to **OAuth2 > URL Generator**.
2.  Select the `bot` scope.
3.  Under **Bot Permissions**, grant the bot `Read Message History`, `Send Messages`, and `View Channels`. Make sure these permissions are enabled.
4.  Copy the generated URL, paste it into your browser, and select your server to invite the bot.

## Running the Bot

To start the bot, run the following command from within the `discord_bot` directory:

```bash
venv/bin/python bot.py
```

You should see output in your terminal indicating that the bot has connected successfully and that the scheduler has started. The bot's internal FastAPI server will run on `http://0.0.0.0:8000` in a separate thread, ensuring non-blocking operation for Discord events.

## Proactive Scheduling

Proactive messages are configured per-persona in `config.json`. Each persona can have its own schedule:

```json
"personas": {
  "CHANNEL_ID": {
    "name": "Trainer",
    "prompt": "You are a professional trainer...",
    "proactive_scheduling": {
      "enabled": true,
      "interval_seconds": 300,
      "time_window": {
        "start_hour": 19,
        "end_hour": 22
      },
      "message_content": null
    }
  }
}
```

### Settings

*   **enabled**: Set to `true` to enable check-ins
*   **interval_seconds**: How often to check (not frequency of messages)
*   **time_window.start_hour/end_hour**: Restrict messages to specific hours (24-hour format)
*   **message_content**: Custom prompt or `null` for default check-in

**Important:** Ensure your `langchain_agent` is running for these proactive messages to be generated and sent successfully.

## API Endpoints

The FastAPI server embedded within the Discord bot runs on `http://0.0.0.0:8000`. It allows external services (like the LangChain agent) to interact with Discord.

### 1. `/send_discord_message/`

*   **Method**: `POST`
*   **Description**: Sends a message immediately to a specified Discord channel. This endpoint is primarily used by the `langchain_agent` to send its responses.
*   **Parameters**:
    *   `channel_id` (integer): The ID of the channel to send the message to.
    *   `message_content` (string): The content of the message.
*   **Implementation Detail:** This endpoint uses `asyncio.run_coroutine_threadsafe` to safely execute Discord API calls on the bot's main event loop from the FastAPI thread.
*   **Example using `curl`**:
    ```bash
    curl -X POST "http://localhost:8000/send_discord_message/?channel_id=YOUR_CHANNEL_ID&message_content=Hello from the API!"
    ```

### 2. `/schedule_discord_message/`

*   **Method**: `POST`
*   **Description**: Schedules a recurring static message to be sent to a Discord channel at a regular interval.
*   **Parameters**:
    *   `channel_id` (integer): The ID of the channel to send the message to.
    *   `message_content` (string): The static content of the message to be scheduled.
    *   `trigger_seconds` (integer): The interval in seconds to send the message.
*   **Example using `curl`**:
    ```bash
    curl -X POST "http://localhost:8000/schedule_discord_message/?channel_id=YOUR_CHANNEL_ID&message_content=This is a scheduled message!&trigger_seconds=60"
    ```
    This will send the message to the specified channel every 60 seconds.