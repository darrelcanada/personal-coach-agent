from fastapi import FastAPI, Request, Body
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

PERSONAS = {
    "default": "You are a helpful general-purpose AI assistant. Please respond concisely.",
    "1478120173071499264": "You are a cheerful and encouraging personal trainer AI named 'Coach'. Your goal is to help users achieve their fitness goals with positive reinforcement."
}

# --- LangChain Setup ---

# Instantiate the local LLM
llm = Ollama(model="llama3:8b")

# --- Helper Function to Process Messages and Respond ---
async def _process_message_and_respond(channel_id: str, input_content: str, is_proactive_message: bool = False):
    """
    Processes a message through the LangChain agent and sends a response to Discord.
    
    Args:
        channel_id (str): The Discord channel ID.
        input_content (str): The content to be processed by the LLM.
        is_proactive_message (bool): True if this is a proactive message initiated by the system,
                                     False if it's a user-initiated message.
    """
    
    # Select the appropriate system prompt for the channel
    selected_system_prompt = PERSONAS.get(channel_id, PERSONAS.get("default"))

    # Create the prompt template dynamically for this request
    prompt = ChatPromptTemplate.from_messages([
        ("system", selected_system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    # Create the LangChain chain dynamically for this request
    chain = prompt | llm | StrOutputParser()

    # Get conversation history from the database
    history = SQLChatMessageHistory(
        session_id=channel_id,
        connection_string=DB_CONNECTION_STRING
    )
    
    # Limit the history to avoid overflowing the context window
    limited_history = history.messages[-CONVERSATION_HISTORY_LIMIT:]

    # Invoke the chain to get the agent's response
    print(f"Invoking LangChain agent for channel {channel_id} (proactive={is_proactive_message}) with persona: {selected_system_prompt[:50]}...")
    ai_response = chain.invoke({
        "input": input_content,
        "chat_history": limited_history,
    })
    print(f"Agent response: {ai_response}")

    # Save the new messages to the database
    if not is_proactive_message:
        history.add_user_message(input_content) # Only save user input if not proactive
    history.add_ai_message(ai_response)

    # Send the response back to Discord
    try:
        requests.post(
            f"{DISCORD_BOT_URL}/send_discord_message/",
            params={"channel_id": channel_id, "message_content": ai_response}
        )
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord bot: {e}")
    
    return {"status": "message processed"}


# --- FastAPI Server ---

app = FastAPI()

@app.post("/message")
async def receive_message(request: Request):
    data = await request.json()
    channel_id = str(data.get("channel_id"))
    author = data.get("author")
    content = data.get("content")

    if author == "agent": # Prevent infinite loops if agent replies to its own messages
        return {"status": "message from agent ignored"}

    print(f"Received user-initiated message from {author} in channel {channel_id}: {content}")
    return await _process_message_and_respond(channel_id, content, is_proactive_message=False)


@app.post("/proactive_message")
async def proactive_message_endpoint(channel_id: str = Body(..., embed=True), message_content: str = None):
    """
    Endpoint for external systems to request a proactive message from the agent.
    """
    print(f"Received request for proactive message in channel {channel_id}")

    proactive_llm_input = message_content if message_content else "Generate a short, natural, and supportive check-in message for your client. Ask how they are feeling physically, check on their training progress, or suggest rest/recovery. Avoid being spammy or asking for a detailed log. Just an open-ended, encouraging check-in."
    
    return await _process_message_and_respond(channel_id, proactive_llm_input, is_proactive_message=True)


def run_agent_server():
    print("Starting LangChain agent server with SQLite persistence and proactive support...")
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    run_agent_server()
