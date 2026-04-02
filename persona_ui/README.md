# Persona Configuration UI

A web-based interface for managing AI persona configurations.

## Features

- View all personas in a card-based layout
- Add new personas (by Discord channel ID)
- Edit existing personas (name, description, prompt, scheduling)
- Delete personas (except default)
- Add/edit/delete check-in schedules with minute-precision time windows
- Pause/resume check-ins instantly
- Reload bot to apply changes

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
- Discord bot running on port 8000

## Check-in Schedule Fields

| Field | Description |
|-------|-------------|
| Name | Display name (e.g., "Workout Reminder") |
| Check Interval | Seconds between checks (e.g., 300 = 5 min, 7200 = 2 hours) |
| Active Between | Start/end hours and minutes (e.g., 8:55 - 20:00) |
| Message Content | Custom message or `WORKOUT_REMINDER` for auto content |
| Enabled | Initial state on bot reload |

## Pause/Resume

- **Pause Button**: Instantly stops the scheduler and saves `enabled: false` to config.json
- **Resume Button**: Instantly resumes and saves `enabled: true` to config.json
- State persists across bot restarts

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Read full config.json |
| GET | `/api/config/reload` | Reload bot schedules |
| POST | `/api/config/persona` | Create new persona |
| PUT | `/api/config/persona/{channel_id}` | Update persona |
| DELETE | `/api/config/persona/{channel_id}` | Delete persona |

## Notes

- Changes are written directly to `config.json`
- Click "Reload Schedules" to apply changes to the running bot
- The default persona cannot be deleted
- Browser cache may need bypass (Ctrl+Shift+R) after code changes
