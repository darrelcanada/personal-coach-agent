import os
import discord
import json # Added for JSON handling
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
import uvicorn
import threading
import asyncio

import requests

# --- Configuration Loading ---
CONFIG_FILE = "../config.json" # Assumes config.json is in the parent directory (project root)
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"Error: {CONFIG_FILE} not found. Please create it with the necessary configurations.")
    config = {
        "discord_bot_url": "http://localhost:8000",
        "db_connection_string": "sqlite:///memory.db",
        "conversation_history_limit": 20,
        "personas": {
            "default": "You are a helpful general-purpose AI assistant. Please respond concisely."
        },
        "discord_bot": {
            "agent_webhook_url": "http://localhost:8001/message",
            "langchain_agent_url": "http://localhost:8001"
        },
        "proactive_scheduling": {}
    }
except json.JSONDecodeError:
    print(f"Error: {CONFIG_FILE} is not a valid JSON file. Using default configurations.")
    config = {
        "discord_bot": {
            "agent_webhook_url": "http://localhost:8001/message",
            "langchain_agent_url": "http://localhost:8001"
        },
        "personas": {
            "default": {
                "reactive_prompt": "You are a helpful general-purpose AI assistant. Please respond concisely.",
                "proactive_prompt": "You are a helpful general-purpose AI assistant. Please provide a brief, friendly check-in."
            }
        },
        "proactive_scheduling": {}
    }

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AGENT_WEBHOOK_URL = config["discord_bot"].get("agent_webhook_url")
LANGCHAIN_AGENT_URL = config["discord_bot"].get("langchain_agent_url")

# Initialize Discord Bot
intents = discord.Intents.default()
intents.message_content = True # Required for accessing message.content
bot = discord.Client(intents=intents)

# Initialize Scheduler
scheduler = AsyncIOScheduler()

# Initialize FastAPI app
app = FastAPI()

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    scheduler.start()
    print("Scheduler started.")

    # Schedule proactive messages from config
    proactive_schedules = config.get("proactive_scheduling", {})
    for job_name, job_details in proactive_schedules.items():
        channel_id = job_details.get("channel_id")
        interval_seconds = job_details.get("interval_seconds")
        message_content = job_details.get("message_content")

        if channel_id and interval_seconds:
            scheduler.add_job(
                _send_proactive_message_to_agent,
                'interval',
                seconds=interval_seconds,
                args=[channel_id, message_content],
                id=job_name # Assign a unique ID to the job
            )
            print(f"Scheduled proactive message '{job_name}' for channel {channel_id} every {interval_seconds} seconds.")
        else:
            print(f"Warning: Proactive schedule '{job_name}' is missing channel_id or interval_seconds.")

# Helper function to send proactive messages to the agent
async def _send_proactive_message_to_agent(channel_id: int, message_content: str):
    """Sends a proactive message to the LangChain agent to generate a response."""
    if LANGCHAIN_AGENT_URL:
        try:
            requests.post(
                f"{LANGCHAIN_AGENT_URL}/proactive_message",
                json={"channel_id": str(channel_id), "message_content": message_content}
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
    if message.content.startswith('!hello'):
        await message.channel.send(f'Hello {message.author.display_name}!')
        return

    # Forward other messages to the agent
    if AGENT_WEBHOOK_URL:
        try:
            payload = {
                "channel_id": message.channel.id,
                "author": message.author.display_name,
                "content": message.content
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
        send_scheduled_message(channel_id, message_content),
        bot.loop
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
async def schedule_discord_message_endpoint(channel_id: int, message_content: str, trigger_seconds: int):
    scheduler.add_job(send_scheduled_message, 'interval', seconds=trigger_seconds, args=[channel_id, message_content])
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
