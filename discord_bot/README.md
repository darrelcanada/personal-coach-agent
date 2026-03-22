# Discord Cron and API Bot

This project is a Python-based Discord bot that can send and monitor messages in a Discord channel. It also features a built-in scheduler for sending messages at timed intervals (like a cron job) and a FastAPI-powered API to allow external services, such as LLM agents, to interact with it.

## Features

- **Discord Message Monitoring**: The bot listens to messages in all channels it has access to and prints them to the console.
- **`!hello` Command**: A simple command to check if the bot is responsive. If you type `!hello`, the bot will reply with `Hello <your_username>!`.
- **API for External Agents**: A FastAPI server runs alongside the bot to expose endpoints for sending and scheduling messages.
  - **Send Immediate Message**: An endpoint to send a message to a channel instantly.
  - **Schedule Recurring Message**: An endpoint to schedule a message to be sent to a channel at a regular interval.

## Project Structure

```
discord_bot/
├── venv/                 # Python virtual environment
├── bot.py                # Main application file
├── requirements.txt      # Project dependencies
└── .env                  # Environment variables (for bot token)
```

## Setup and Installation

### Prerequisites

- Python 3.10+
- A Discord account

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

### 3. Get Your Discord Bot Token

You'll need a Discord Bot Token to run the bot.

1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Create a **New Application**.
3.  Navigate to the **Bot** tab and click **Add Bot**.
4.  Under the bot's username, click **Reset Token** (or **Copy Token** if you have one already) and copy the token.

### 4. Configure Environment Variables

1.  Create a file named `.env` in the `discord_bot` directory.
2.  Add your bot token to this file:
    ```
    DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
    ```
    Replace `YOUR_DISCORD_BOT_TOKEN` with the token you copied.

### 5. Invite the Bot to Your Server

1.  In the Discord Developer Portal, go to **OAuth2 > URL Generator**.
2.  Select the `bot` scope.
3.  Under **Bot Permissions**, grant the bot `Read Message History`, `Send Messages`, and `View Channels`.
4.  Copy the generated URL, paste it into your browser, and select your server to invite the bot.

## Running the Bot

To start the bot, run the following command from within the `discord_bot` directory:

```bash
venv/bin/python bot.py
```

You should see output in your terminal indicating that the bot has connected successfully.

## API Endpoints

The FastAPI server will be running on `http://0.0.0.0:8000`.

### Send a Message Immediately

- **Endpoint**: `/send_discord_message/`
- **Method**: `POST`
- **Parameters**:
  - `channel_id` (integer): The ID of the channel to send the message to.
  - `message_content` (string): The content of the message.
- **Example using `curl`**:
  ```bash
  curl -X POST "http://localhost:8000/send_discord_message/?channel_id=YOUR_CHANNEL_ID&message_content=Hello from the API!"
  ```

### Schedule a Recurring Message

- **Endpoint**: `/schedule_discord_message/`
- **Method**: `POST`
- **Parameters**:
  - `channel_id` (integer): The ID of the channel to send the message to.
  - `message_content` (string): The content of the message.
  - `trigger_seconds` (integer): The interval in seconds to send the message.
- **Example using `curl`**:
  ```bash
  curl -X POST "http://localhost:8000/schedule_discord_message/?channel_id=YOUR_CHANNEL_ID&message_content=This is a scheduled message!&trigger_seconds=60"
  ```
  This will send the message to the specified channel every 60 seconds.
