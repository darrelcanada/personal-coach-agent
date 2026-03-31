import os
import discord
import json
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
import uvicorn
import threading
import asyncio

import requests

load_dotenv()  # Load .env from the project root by default

# --- Configuration Loading ---
CONFIG_FILE = (
    "../config.json"  # Assumes config.json is in the parent directory (project root)
)
try:
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print(
        f"Error: {CONFIG_FILE} not found. Please create it with the necessary configurations."
    )
    config = {
        "discord_bot_url": "http://localhost:8000",
        "db_connection_string": "sqlite:///memory.db",
        "conversation_history_limit": 20,
        "personas": {
            "default": "You are a helpful general-purpose AI assistant. Please respond concisely."
        },
        "discord_bot": {
            "agent_webhook_url": "http://localhost:8001/message",
            "langchain_agent_url": "http://localhost:8001",
        },
        "proactive_scheduling": {},
    }
except json.JSONDecodeError:
    print(
        f"Error: {CONFIG_FILE} is not a valid JSON file. Using default configurations."
    )
    config = {
        "discord_bot_url": "http://localhost:8000",
        "db_connection_string": "sqlite:///memory.db",
        "conversation_history_limit": 20,
        "personas": {
            "default": "You are a helpful general-purpose AI assistant. Please respond concisely."
        },
        "discord_bot": {
            "agent_webhook_url": "http://localhost:8001/message",
            "langchain_agent_url": "http://localhost:8001",
        },
        "proactive_scheduling": {},
    }

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AGENT_WEBHOOK_URL = config["discord_bot"].get("agent_webhook_url")
LANGCHAIN_AGENT_URL = config["discord_bot"].get("langchain_agent_url")

# Initialize Discord Bot
intents = discord.Intents.default()
intents.message_content = True  # Required for accessing message.content
bot = discord.Client(intents=intents)

# Initialize Scheduler
scheduler = AsyncIOScheduler()

# Store proactive schedule configs for time window checking
schedule_configs = {}

# Initialize FastAPI app
app = FastAPI()


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    scheduler.start()
    print("Scheduler started.")

    # Schedule proactive messages from config
    proactive_schedules = config.get("proactive_scheduling", {})
    for job_name, job_details in proactive_schedules.items():
        channel_id = job_details.get("channel_id")
        interval_seconds = job_details.get("interval_seconds")
        message_content = job_details.get("message_content")
        start_hour = job_details.get("start_hour")
        end_hour = job_details.get("end_hour")

        if channel_id and interval_seconds:
            schedule_configs[job_name] = {
                "channel_id": channel_id,
                "message_content": message_content,
                "start_hour": start_hour,
                "end_hour": end_hour,
            }
            scheduler.add_job(
                _send_proactive_message_to_agent,
                "interval",
                seconds=interval_seconds,
                args=[job_name],
                id=job_name,
            )
            time_window = (
                f" ({start_hour}:00-{end_hour}:00)"
                if start_hour is not None and end_hour is not None
                else ""
            )
            print(
                f"Scheduled proactive message '{job_name}' for channel {channel_id} every {interval_seconds} seconds{time_window}."
            )
        else:
            print(
                f"Warning: Proactive schedule '{job_name}' is missing channel_id or interval_seconds."
            )


def _is_within_time_window(start_hour: int | None, end_hour: int | None) -> bool:
    """Check if current hour is within the allowed time window."""
    if start_hour is None or end_hour is None:
        return True
    current_hour = datetime.now().hour
    if start_hour <= end_hour:
        return start_hour <= current_hour < end_hour
    else:
        return current_hour >= start_hour or current_hour < end_hour


async def _send_proactive_message_to_agent(job_name: str):
    """Sends a proactive message to the LangChain agent if within the allowed time window."""
    schedule = schedule_configs.get(job_name)
    if not schedule:
        print(f"No schedule config found for job '{job_name}'")
        return

    channel_id = schedule["channel_id"]
    message_content = schedule["message_content"]
    start_hour = schedule.get("start_hour")
    end_hour = schedule.get("end_hour")

    if not _is_within_time_window(start_hour, end_hour):
        current_hour = datetime.now().hour
        print(
            f"Skipping proactive message '{job_name}' - current hour ({current_hour}) is outside window ({start_hour}:00-{end_hour}:00)"
        )
        return

    if LANGCHAIN_AGENT_URL:
        try:
            requests.post(
                f"{LANGCHAIN_AGENT_URL}/proactive_message",
                json={
                    "channel_id": str(channel_id),
                    "message_content": message_content,
                },
            )
            print(f"Sent proactive message request to agent for channel {channel_id}.")
        except requests.exceptions.RequestException as e:
            print(f"Error sending proactive message to agent: {e}")
    else:
        print("LANGCHAIN_AGENT_URL not set. Proactive message not sent.")


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Handle the hello command directly
    if message.content.startswith("!hello"):
        await message.channel.send(f"Hello {message.author.display_name}!")
        return

    # Forward other messages to the agent
    if AGENT_WEBHOOK_URL:
        try:
            payload = {
                "channel_id": message.channel.id,
                "author": message.author.display_name,
                "user_id": str(message.author.id),  # Added user_id
                "content": message.content,
            }
            requests.post(AGENT_WEBHOOK_URL, json=payload)
            print(f"Forwarded message from {message.author.display_name} to agent.")
        except requests.exceptions.RequestException as e:
            print(f"Error forwarding message to agent: {e}")
    else:
        print("AGENT_WEBHOOK_URL not set. Message not forwarded.")


# Function to send a scheduled message
async def send_scheduled_message(channel_id: int, message_content: str):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(message_content)
        print(f"Sent scheduled message to channel {channel_id}: {message_content}")
    else:
        print(f"Error: Channel with ID {channel_id} not found.")


# FastAPI endpoint to send a message
@app.post("/send_discord_message/")
async def send_discord_message_endpoint(channel_id: int, message_content: str):
    # Schedule the coroutine on the bot's event loop and wait for the result.
    # This is thread-safe and prevents the "attached to a different loop" error.
    future = asyncio.run_coroutine_threadsafe(
        send_scheduled_message(channel_id, message_content), bot.loop
    )
    try:
        # Wait for the result for a reasonable time
        future.result(timeout=10)
        return {"message": "Message sent successfully."}
    except Exception as e:
        print(f"Error sending message from API endpoint: {e}")
        return {"message": "Failed to send message."}


# FastAPI endpoint to schedule a message
@app.post("/schedule_discord_message/")
async def schedule_discord_message_endpoint(
    channel_id: int, message_content: str, trigger_seconds: int
):
    scheduler.add_job(
        send_scheduled_message,
        "interval",
        seconds=trigger_seconds,
        args=[channel_id, message_content],
    )
    return {"message": f"Message scheduled to be sent every {trigger_seconds} seconds."}


# Function to run the FastAPI app in a separate thread
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    # Start FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()

    # Run the Discord bot
    bot.run(DISCORD_TOKEN)
