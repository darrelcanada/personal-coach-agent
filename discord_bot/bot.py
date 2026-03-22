import os
import discord
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
import uvicorn
import threading
import asyncio

import requests

# Load environment variables from .env file
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AGENT_WEBHOOK_URL = os.getenv("AGENT_WEBHOOK_URL")

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
