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

load_dotenv()

CONFIG_FILE = "../config.json"

try:
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"Error: {CONFIG_FILE} not found.")
    exit(1)
except json.JSONDecodeError:
    print(f"Error: {CONFIG_FILE} is not valid JSON.")
    exit(1)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AGENT_WEBHOOK_URL = config.get("_discord", {}).get(
    "agent_webhook_url", "http://localhost:8001/message"
)
LANGCHAIN_AGENT_URL = config.get("_discord", {}).get(
    "langchain_agent_url", "http://localhost:8001"
)

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

scheduler = AsyncIOScheduler()
schedule_configs = {}
app = FastAPI()


def _is_within_time_window(start_hour: int | None, end_hour: int | None) -> bool:
    """Check if current hour is within the allowed time window."""
    if start_hour is None or end_hour is None:
        return True
    current_hour = datetime.now().hour
    if start_hour <= end_hour:
        return start_hour <= current_hour < end_hour
    else:
        return current_hour >= start_hour or current_hour < end_hour


def _load_schedule_configs():
    """Load proactive schedule configs from personas in config.json."""
    personas = config.get("personas", {})
    for channel_id, persona_config in personas.items():
        proactive = persona_config.get("proactive_scheduling")
        if not proactive or not proactive.get("enabled"):
            continue

        interval_seconds = proactive.get("interval_seconds", 300)
        time_window = proactive.get("time_window", {})
        start_hour = time_window.get("start_hour")
        end_hour = time_window.get("end_hour")

        schedule_configs[channel_id] = {
            "channel_id": int(channel_id),
            "message_content": proactive.get("message_content"),
            "start_hour": start_hour,
            "end_hour": end_hour,
        }

        scheduler.add_job(
            _send_proactive_message_to_agent,
            "interval",
            seconds=interval_seconds,
            args=[channel_id],
            id=f"proactive_{channel_id}",
        )

        window_str = (
            f" ({start_hour}:00-{end_hour}:00)" if start_hour and end_hour else ""
        )
        print(
            f"Scheduled '{persona_config.get('name', 'Unnamed')}' check-in for channel {channel_id} every {interval_seconds}s{window_str}."
        )


async def _send_proactive_message_to_agent(channel_id: str):
    """Sends a proactive message to the LangChain agent if within the allowed time window."""
    schedule = schedule_configs.get(channel_id)
    if not schedule:
        return

    persona = config.get("personas", {}).get(channel_id, {})
    persona_name = persona.get("name", "Unknown")

    start_hour = schedule.get("start_hour")
    end_hour = schedule.get("end_hour")

    if not _is_within_time_window(start_hour, end_hour):
        current_hour = datetime.now().hour
        print(
            f"[{persona_name}] Skipped - outside time window ({current_hour}:00 not in {start_hour}-{end_hour})"
        )
        return

    try:
        requests.post(
            f"{LANGCHAIN_AGENT_URL}/proactive_message",
            json={
                "channel_id": str(schedule["channel_id"]),
                "message_content": schedule["message_content"],
            },
        )
        print(
            f"[{persona_name}] Sent proactive message to channel {schedule['channel_id']}."
        )
    except requests.exceptions.RequestException as e:
        print(f"[{persona_name}] Error: {e}")


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    _load_schedule_configs()
    scheduler.start()
    print("Scheduler started.")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith("!hello"):
        await message.channel.send(f"Hello {message.author.display_name}!")
        return

    if AGENT_WEBHOOK_URL:
        try:
            requests.post(
                AGENT_WEBHOOK_URL,
                json={
                    "channel_id": message.channel.id,
                    "author": message.author.display_name,
                    "user_id": str(message.author.id),
                    "content": message.content,
                },
            )
        except requests.exceptions.RequestException as e:
            print(f"Error forwarding message: {e}")


async def send_scheduled_message(channel_id: int, message_content: str):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(message_content)


@app.post("/send_discord_message/")
async def send_discord_message_endpoint(channel_id: int, message_content: str):
    future = asyncio.run_coroutine_threadsafe(
        send_scheduled_message(channel_id, message_content), bot.loop
    )
    try:
        future.result(timeout=10)
        return {"message": "Message sent successfully."}
    except Exception as e:
        print(f"Error: {e}")
        return {"message": "Failed to send message."}


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
    return {"message": f"Message scheduled every {trigger_seconds} seconds."}


def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()
    bot.run(DISCORD_TOKEN)
