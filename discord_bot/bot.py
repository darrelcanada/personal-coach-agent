import os
import discord
import json
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
schedule_registry = {}
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _is_within_time_window(
    start_hour: int | None,
    start_minute: int | None,
    end_hour: int | None,
    end_minute: int | None,
) -> bool:
    if start_hour is None or end_hour is None:
        return True
    now = datetime.now()
    current_time = now.hour * 60 + now.minute
    start_time = start_hour * 60 + (start_minute or 0)
    end_time = end_hour * 60 + (end_minute or 0)
    if start_time <= end_time:
        return start_time <= current_time < end_time
    else:
        return current_time >= start_time or current_time < end_time


def _load_schedules():
    schedule_registry.clear()
    personas = config.get("personas", {})

    for channel_id, persona in personas.items():
        schedules = persona.get("proactive_scheduling", []) or []
        if not isinstance(schedules, list):
            schedules = [schedules] if schedules else []

        for schedule in schedules:
            if not schedule:  # Skip empty schedule entries
                continue

            schedule_id = schedule.get("id") or f"{channel_id}_{len(schedule_registry)}"
            job_id = f"proactive_{schedule_id}"
            interval = schedule.get("interval_seconds", 300)
            time_window = schedule.get("time_window", {})
            start_hour = time_window.get("start_hour")
            start_minute = time_window.get("start_minute", 0)
            end_hour = time_window.get("end_hour")
            end_minute = time_window.get("end_minute", 0)
            is_enabled_in_config = schedule.get(
                "enabled", True
            )  # Get initial enabled state from config

            schedule_registry[job_id] = {
                "channel_id": int(channel_id),
                "persona_name": persona.get("name", "Unknown"),
                "schedule_name": schedule.get("name", "Unnamed"),
                "message_content": schedule.get("message_content"),
                "start_hour": start_hour,
                "start_minute": start_minute,
                "end_hour": end_hour,
                "end_minute": end_minute,
                "enabled_in_config": is_enabled_in_config,  # Store original enabled state from config
            }

            job = scheduler.add_job(
                _send_proactive_message,
                "interval",
                seconds=interval,
                args=[job_id],
                id=job_id,
                replace_existing=True,
            )

            if not is_enabled_in_config:
                scheduler.pause_job(job_id)

            window_str = (
                f" ({start_hour}:{start_minute:02d}-{end_hour}:{end_minute:02d})"
                if start_hour is not None and end_hour is not None
                else ""
            )

            interval_minutes = interval // 60
            interval_str = (
                f" every {interval_minutes}m"
                if interval < 3600
                else f" every {interval_minutes // 60}h"
            )
            status_str = " (PAUSED by config)" if not is_enabled_in_config else ""

            print(
                f"[{persona.get('name', 'Unknown')}] Scheduled '{schedule.get('name', 'Unnamed')}'{interval_str}{window_str}{status_str}"
            )


async def _send_proactive_message(job_id: str):
    schedule = schedule_registry.get(job_id)
    if not schedule:
        return

    start_hour = schedule.get("start_hour")
    start_minute = schedule.get("start_minute", 0)
    end_hour = schedule.get("end_hour")
    end_minute = schedule.get("end_minute", 0)
    persona_name = schedule.get("persona_name", "Unknown")
    schedule_name = schedule.get("schedule_name", "Unnamed")

    if not _is_within_time_window(start_hour, start_minute, end_hour, end_minute):
        now = datetime.now()
        current_time = f"{now.hour}:{now.minute:02d}"
        window = (
            f"{start_hour}:{start_minute:02d}-{end_hour}:{end_minute:02d}"
            if start_hour and end_hour
            else "any"
        )
        print(
            f"[{persona_name}] Skipped '{schedule_name}' - outside window ({current_time} not in {window})"
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
            f"[{persona_name}] Sent '{schedule_name}' to channel {schedule['channel_id']}"
        )
    except requests.exceptions.RequestException as e:
        print(f"[{persona_name}] Error sending '{schedule_name}': {e}")


@app.get("/api/schedules")
async def get_schedules():
    schedules = []
    for job_id, schedule in schedule_registry.items():
        job = scheduler.get_job(job_id)
        is_active = (
            job is not None and job.next_run_time is not None
        )  # True if scheduled and not paused
        schedules.append(
            {
                "job_id": job_id,
                "channel_id": schedule["channel_id"],
                "persona_name": schedule["persona_name"],
                "schedule_name": schedule["schedule_name"],
                "message_content": schedule["message_content"],
                "start_hour": schedule.get("start_hour"),
                "start_minute": schedule.get("start_minute", 0),
                "end_hour": schedule.get("end_hour"),
                "end_minute": schedule.get("end_minute", 0),
                "enabled_in_config": schedule[
                    "enabled_in_config"
                ],  # Reflect config's initial enabled state
                "is_active": is_active,  # Reflect APScheduler's current runtime state
            }
        )
    return schedules


@app.post("/api/schedules/{job_id}/pause")
async def pause_schedule(job_id: str):
    try:
        scheduler.pause_job(job_id)

        schedule_id = job_id.replace("proactive_", "")
        _update_schedule_enabled(schedule_id, False)

        print(f"DEBUG: After pause, config file check:")
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        for p in config.get("personas", {}).values():
            for s in p.get("proactive_scheduling", []):
                if "workout" in s.get("id", ""):
                    print(f"  workout_reminder enabled = {s.get('enabled')}")

        return {"status": "paused", "job_id": job_id}
    except Exception as e:
        print(f"ERROR in pause_schedule: {e}")
        return {"error": str(e)}, 400


@app.post("/api/schedules/{job_id}/resume")
async def resume_schedule(job_id: str):
    try:
        scheduler.resume_job(job_id)

        schedule_id = job_id.replace("proactive_", "")
        _update_schedule_enabled(schedule_id, True)

        return {"status": "resumed", "job_id": job_id}
    except Exception as e:
        return {"error": str(e)}, 400


def _update_schedule_enabled(schedule_id: str, enabled: bool):
    print(
        f"DEBUG: _update_schedule_enabled called with schedule_id={schedule_id}, enabled={enabled}"
    )
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        updated = False
        for channel_id, persona in config.get("personas", {}).items():
            schedules = persona.get("proactive_scheduling", []) or []
            for schedule in schedules:
                if schedule.get("id") == schedule_id:
                    schedule["enabled"] = enabled
                    updated = True
                    print(f"DEBUG: Updated schedule {schedule_id} to enabled={enabled}")

        if updated:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        else:
            print(f"DEBUG: Schedule {schedule_id} not found in config")
    except Exception as e:
        print(f"Error updating schedule enabled state: {e}")


@app.post("/api/schedules/{job_id}/remove")
async def remove_schedule(job_id: str):
    try:
        scheduler.remove_job(job_id)
        if job_id in schedule_registry:
            del schedule_registry[job_id]
        return {"status": "removed", "job_id": job_id}
    except Exception as e:
        return {"error": str(e)}, 400


@app.post("/api/schedules/reload")
async def reload_schedules():
    _load_schedules()
    return {"status": "reloaded"}


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    _load_schedules()
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
