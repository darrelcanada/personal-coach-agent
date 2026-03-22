# LangChain Personal Coach Agent

This directory contains the LangChain agent that acts as a personal coach. It runs a FastAPI server to receive messages from the Discord bot and sends responses back.

## Setup

1.  **Create a virtual environment and install dependencies:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configure Environment Variables:**
    The `.env` file contains the URL for the Discord bot's API. The default is `http://localhost:8000`.

## Running the Agent

To start the agent's server, run:
```bash
venv/bin/python agent.py
```
The agent will be running on `http://0.0.0.0:8001`.
