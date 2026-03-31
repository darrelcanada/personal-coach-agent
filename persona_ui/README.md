# Persona Configuration UI

A web-based interface for managing AI persona configurations.

## Features

- View all personas in a card-based layout
- Add new personas (by Discord channel ID)
- Edit existing personas (name, description, prompt, scheduling)
- Delete personas (except default)
- Toggle proactive scheduling with time window support

## Running

```bash
cd persona_ui
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py
```

Then open `http://localhost:8002` in your browser.

## Requirements

- Python 3.10+
- Access to `config.json` in the project root

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Read full config.json |
| POST | `/api/config/persona` | Create new persona |
| PUT | `/api/config/persona/{channel_id}` | Update persona |
| DELETE | `/api/config/persona/{channel_id}` | Delete persona |

## Notes

- Changes are written directly to `config.json`
- Restart `discord_bot` to apply changes
- The default persona cannot be deleted
