from fastapi import FastAPI, Request
import uvicorn
import requests
import os
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

# --- LangChain Setup ---

# 1. Define the agent's persona with a system prompt
system_prompt = """
You are a world-class personal trainer and physical therapist AI named 'Coach'. 
Your goal is to help me, the user, achieve my fitness and health goals.
You will start by interviewing me to understand my current fitness level, any injuries or limitations, and my long-term goals.
Based on this, you will develop a personalized weekly exercise routine.
You must be supportive, knowledgeable, and proactive. Check in with me, ask about my progress, and be ready to adjust the plan based on my feedback.
Your tone should be encouraging and professional.
"""

# 2. Set up the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])

# 3. Instantiate the local LLM
llm = Ollama(model="llama3:8b")

# 4. Create the LangChain chain
chain = prompt | llm | StrOutputParser()

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

    # 1. Get conversation history from the database
    history = SQLChatMessageHistory(
        session_id=channel_id,
        connection_string=DB_CONNECTION_STRING
    )
    
    # 2. Limit the history to avoid overflowing the context window
    limited_history = history.messages[-CONVERSATION_HISTORY_LIMIT:]

    # 3. Invoke the chain to get the agent's response
    print("Invoking LangChain agent with history...")
    ai_response = chain.invoke({
        "input": content,
        "chat_history": limited_history,
    })
    print(f"Agent response: {ai_response}")

    # 4. Save the new messages to the database
    history.add_user_message(content)
    history.add_ai_message(ai_response)

    # 5. Send the response back to Discord
    try:
        requests.post(
            f"{DISCORD_BOT_URL}/send_discord_message/",
            params={"channel_id": channel_id, "message_content": ai_response}
        )
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord bot: {e}")

    return {"status": "message processed"}

def run_agent_server():
    print("Starting LangChain agent server with SQLite persistence...")
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    run_agent_server()
