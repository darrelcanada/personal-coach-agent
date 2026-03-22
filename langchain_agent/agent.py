from fastapi import FastAPI, Request
import uvicorn
import requests
import os
import json
from dotenv import load_dotenv

from langchain_community.llms import Ollama
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

# --- Configuration ---
load_dotenv()
DISCORD_BOT_URL = os.getenv("DISCORD_BOT_URL", "http://localhost:8000")
DB_CONNECTION_STRING = "sqlite:///memory.db"
CONVERSATION_HISTORY_LIMIT = 20 # Number of past messages to include in the context
PERSONAS_FILE = "personas.json" # File containing persona definitions

# Load personas from JSON file
try:
    with open(PERSONAS_FILE, 'r') as f:
        PERSONAS = json.load(f)
except FileNotFoundError:
    print(f"Error: {PERSONAS_FILE} not found. Please create it.")
    PERSONAS = {"default": "You are a helpful assistant."} # Fallback
except json.JSONDecodeError:
    print(f"Error: {PERSONAS_FILE} is not a valid JSON file.")
    PERSONAS = {"default": "You are a helpful assistant."} # Fallback


# --- LangChain Setup (LLM is still global, chain will be dynamic) ---

# Instantiate the local LLM (this can remain global as it's not persona-specific)
llm = Ollama(model="llama3:8b")

# --- FastAPI Server ---

app = FastAPI()

@app.post("/message")
async def receive_message(request: Request):
    data = await request.json()
    channel_id = str(data.get("channel_id")) # Session ID must be a string
    author = data.get("author")
    content = data.get("content")

    if author == "agent":
        return {"status": "message from agent ignored"}

    print(f"Received message from {author} in channel {channel_id}: {content}")

    # 1. Select the appropriate system prompt for the channel
    # Use .get() with a default to handle cases where a channel_id isn't explicitly in PERSONAS
    selected_system_prompt = PERSONAS.get(channel_id, PERSONAS.get("default"))

    # 2. Create the prompt template and chain dynamically for this request
    prompt = ChatPromptTemplate.from_messages([
        ("system", selected_system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    current_chain = prompt | llm | StrOutputParser()


    # 3. Get conversation history from the database
    history = SQLChatMessageHistory(
        session_id=channel_id,
        connection_string=DB_CONNECTION_STRING
    )
    
    # 4. Limit the history to avoid overflowing the context window
    limited_history = history.messages[-CONVERSATION_HISTORY_LIMIT:]

    # 5. Invoke the chain to get the agent's response
    print(f"Invoking LangChain agent for channel {channel_id} with persona: {selected_system_prompt[:50]}...")
    ai_response = current_chain.invoke({
        "input": content,
        "chat_history": limited_history,
    })
    print(f"Agent response: {ai_response}")

    # 6. Save the new messages to the database
    history.add_user_message(content)
    history.add_ai_message(ai_response)

    # 7. Send the response back to Discord
    try:
        requests.post(
            f"{DISCORD_BOT_URL}/send_discord_message/",
            params={"channel_id": channel_id, "message_content": ai_response}
        )
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord bot: {e}")

    return {"status": "message processed"}

def run_agent_server():
    print("Starting LangChain agent server with SQLite persistence and multi-persona support...")
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    run_agent_server()
