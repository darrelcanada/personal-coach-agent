# AGENTS.md - Personal Coach Agent

## Project Overview

This project is a Discord bot with an integrated LangChain AI agent for personal coaching. It consists of two main components:

- **discord_bot/**: Discord interface with FastAPI endpoints and APScheduler for proactive messaging
- **langchain_agent/**: LangChain agent with FastAPI server for AI responses, persona management, and health data tracking

## Build Commands

### Setup Virtual Environments (required for each component)

```bash
# discord_bot
cd discord_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# langchain_agent
cd langchain_agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the Application

```bash
# Terminal 1: Start the langchain agent
cd langchain_agent
source venv/bin/activate
python agent.py  # Runs on http://0.0.0.0:8001

# Terminal 2: Start the discord bot
cd discord_bot
source venv/bin/activate
python bot.py  # Runs on http://0.0.0.0:8000
```

### Testing

No formal test framework is currently configured. To test functionality:
- Send messages in Discord channels
- Check logs in terminal output
- Query SQLite database directly:
  ```bash
  sqlite3 langchain_agent/memory.db "SELECT * FROM health_log;"
  sqlite3 langchain_agent/memory.db "SELECT * FROM user_profile;"
  ```

### Linting

No linting tools are currently configured. Before committing, manually verify:
- All imports are at the top of files
- No hardcoded credentials (use environment variables)
- Proper exception handling
- Consistent code style matching existing files

## Code Style Guidelines

### General Conventions

- **Python 3.10+** required
- Use `python-dotenv` for environment variable loading via `load_dotenv()`
- Configuration via `config.json` in project root (not hardcoded)
- Two-space indentation (match existing files)
- Max line length: ~120 characters (use judgment)

### Imports

- Standard library imports first
- Third-party imports second (fastapi, uvicorn, discord, langchain, etc.)
- Local imports last
- One import per line
- Group with blank lines between groups

```python
# Correct
import os
import json
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

from langchain_community.llms import Ollama
```

### Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: prefix with `_`
- Descriptive names preferred over abbreviations

```python
# Variables
channel_id = "12345"
db_connection_string = "sqlite:///memory.db"

# Functions
def log_health_data(user_id: str, message_content: str) -> str:
    pass

def _send_proactive_message_to_agent(channel_id: int, message_content: str):
    pass
```

### Type Annotations

Type hints are encouraged for function parameters and return values:

```python
def process_health_query(user_id: str, message_content: str) -> str:
    # Return type is string response message
    pass
```

### Docstrings

Use docstrings for public functions and complex logic:

```python
def log_health_data(user_id: str, message_content: str) -> str:
    """
    Parses health data from the message content and logs it to the database.
    
    Args:
        user_id: The Discord user ID
        message_content: The raw message content to parse
        
    Returns:
        A confirmation message indicating success or failure.
    """
```

### Error Handling

- Use try/except blocks for I/O operations (file, database, network)
- Catch specific exceptions when possible
- Always close resources in `finally` blocks or use context managers
- Return user-friendly error messages, log technical details

```python
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # operations
except sqlite3.Error as e:
    print(f"Error querying health data: {e}")
    response_message = "An error occurred while trying to retrieve your health data."
finally:
    if conn:
        conn.close()
```

### FastAPI Patterns

- Use `@app.post()` and `@app.get()` decorators
- Define request models using Pydantic or `Request`/`Body`
- Use `async def` for endpoint handlers
- Return JSON-serializable responses

```python
@app.post("/message")
async def receive_message(request: Request):
    data = await request.json()
    # process and return
```

### Database Operations

- Use SQLite for local persistence (`sqlite:///memory.db` or file path)
- Create tables with `IF NOT EXISTS`
- Use parameterized queries to prevent SQL injection
- Close connections in `finally` blocks

### Async/Await Patterns

- Use `async def` for Discord event handlers (`@bot.event`)
- Use `asyncio.run_coroutine_threadsafe()` for cross-thread Discord API calls
- APScheduler with `AsyncIOScheduler` for async scheduling

### Configuration Management

- Load environment variables with `load_dotenv()` at module top
- Read config from `config.json` with fallback defaults
- Validate required config and exit with clear error if missing

```python
try:
    config_path = os.path.join(current_dir, "..", "config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: config.json not found. Please create it in the root directory.")
    exit(1)
```

## Environment Variables

Required in `.env` files:

**discord_bot/.env**:
```
DISCORD_TOKEN="your_discord_bot_token"
```

**langchain_agent/.env** (if needed):
```
# Agent configuration
```

## File Structure

```
.
├── config.json              # Shared configuration (personas, scheduling, DB)
├── discord_bot/
│   ├── bot.py              # Main bot + FastAPI server
│   └── requirements.txt
├── langchain_agent/
│   ├── agent.py            # Main agent + FastAPI server
│   ├── memory.db           # SQLite database (gitignored)
│   └── requirements.txt
└── README.md               # User-facing documentation
```

## Key Dependencies

- **discord.py**: Discord API wrapper
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **langchain-ollama**: LLM integration (ollama with llama3:8b)
- **SQLAlchemy**: ORM (langchain dependency)
- **APScheduler**: Task scheduling
- **requests**: HTTP client

## Important Notes

1. **No Tests**: This codebase currently has no automated tests. When adding tests, use `pytest` and place test files in a `tests/` directory.

2. **Database**: `memory.db` is gitignored. Each developer will have their own local database.

3. **Personas**: Configured in `config.json` under `personas` dict, keyed by Discord channel ID.

4. **Proactive Messaging**: Scheduled via `proactive_scheduling` in `config.json`, uses APScheduler.

5. **Health Data**: Parsed from messages starting with "Log health:" using regex patterns. Stored in `health_log` and `user_profile` tables.
