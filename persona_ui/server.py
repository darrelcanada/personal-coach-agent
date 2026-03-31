import os
import json
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

current_dir = Path(__file__).parent
config_path = current_dir.parent / "config.json"

DISCORD_BOT_URL = "http://localhost:8000"

app = FastAPI()

app.mount("/static", StaticFiles(directory=current_dir), name="static")

STATIC_DIR = current_dir


@app.get("/api/config")
async def get_config():
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "config.json not found"}, 404
    except json.JSONDecodeError:
        return {"error": "config.json is not valid JSON"}, 500


@app.post("/api/config/reload")
async def reload_bot_schedules():
    try:
        response = requests.post(f"{DISCORD_BOT_URL}/api/schedules/reload", timeout=5)
        if response.ok:
            return {"status": "reloaded", "message": "Bot schedules reloaded"}
        return {
            "status": "error",
            "message": f"Bot returned: {response.status_code}",
        }, 500
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Cannot connect to bot. Is it running?",
        }, 503
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


@app.put("/api/config/persona/{channel_id}")
async def update_persona(channel_id: str, persona_data: dict):
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        return {"error": "config.json not found"}, 404
    except json.JSONDecodeError:
        return {"error": "config.json is not valid JSON"}, 500

    if channel_id not in config.get("personas", {}):
        return {"error": f"Persona '{channel_id}' not found"}, 404

    config["personas"][channel_id].update(persona_data)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return {"status": "updated", "persona": config["personas"][channel_id]}


@app.post("/api/config/persona")
async def create_persona(persona_data: dict):
    channel_id = persona_data.get("channel_id")
    if not channel_id:
        return {"error": "channel_id is required"}, 400

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        return {"error": "config.json not found"}, 404
    except json.JSONDecodeError:
        return {"error": "config.json is not valid JSON"}, 500

    if channel_id in config.get("personas", {}):
        return {"error": f"Persona '{channel_id}' already exists"}, 409

    config.setdefault("personas", {})[channel_id] = persona_data

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return {"status": "created", "persona": config["personas"][channel_id]}


@app.delete("/api/config/persona/{channel_id}")
async def delete_persona(channel_id: str):
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        return {"error": "config.json not found"}, 404
    except json.JSONDecodeError:
        return {"error": "config.json is not valid JSON"}, 500

    if channel_id not in config.get("personas", {}):
        return {"error": f"Persona '{channel_id}' not found"}, 404

    if channel_id == "default":
        return {"error": "Cannot delete the default persona"}, 400

    del config["personas"][channel_id]

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return {"status": "deleted"}


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8002)


if __name__ == "__main__":
    run_server()
