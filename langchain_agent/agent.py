from fastapi import FastAPI, Request, Body
import uvicorn
import requests
import os
import json
from dotenv import load_dotenv # Added load_dotenv
import re # Added for regex parsing
from datetime import date, timedelta # Added for log_date and timedelta



load_dotenv() # Load .env from the project root by default

from langchain_community.llms import Ollama
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

# --- Configuration ---
load_dotenv()

# Load configurations from config.json
try:
    # Construct the absolute path to config.json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "..", "config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: config.json not found. Please create it in the root directory.")
    exit(1)
except json.JSONDecodeError:
    print("Error: config.json is not a valid JSON file.")
    exit(1)

DISCORD_BOT_URL = os.getenv("DISCORD_BOT_URL", config.get("discord_bot_url", "http://localhost:8000"))
DB_CONNECTION_STRING = config.get("db_connection_string", "sqlite:///memory.db") # Now from config.json or default
CONVERSATION_HISTORY_LIMIT = config.get("conversation_history_limit", 20) # Now from config.json or default
PERSONAS = config.get("personas", {"default": "You are a helpful general-purpose AI assistant. Please respond concisely."})



import sqlite3 # Added for database interaction

# ... (rest of the imports and configuration loading)

# --- Database Initialization for Health Data ---
def initialize_health_database():
    """Initializes the SQLite database and creates the health_log table if it doesn't exist."""
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                log_date DATE NOT NULL,
                weight REAL,
                walking_steps INTEGER,
                walking_distance REAL,
                sleep_duration_hours REAL,
                daily_goals_steps INTEGER,
                daily_goals_workout TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print(f"Health log database initialized at {db_path}")
    except sqlite3.Error as e:
        print(f"Error initializing health log database: {e}")
    finally:
        if conn:
            conn.close()

# --- Health Data Logging ---
def log_health_data(user_id: str, message_content: str) -> str:
    """
    Parses health data from the message content and logs it to the database.
    Returns a confirmation message.
    """
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Initialize data points
        weight = None
        walking_steps = None
        walking_distance = None
        sleep_duration_hours = None
        daily_goals_steps = None
        daily_goals_workout = None

        # Regex patterns for extraction
        # Weight log: "Weight: 75.5kg" or "75.5kg weight"
        weight_match = re.search(r"weight:?\s*(\d+\.?\d*)\s*(kg|lbs)", message_content, re.IGNORECASE)
        if weight_match:
            weight = float(weight_match.group(1))

        # Walking: "Walked 10000 steps" or "5km walk"
        steps_match = re.search(r"(\d+)\s*steps", message_content, re.IGNORECASE)
        if steps_match:
            walking_steps = int(steps_match.group(1))

        distance_match = re.search(r"(\d+\.?\d*)\s*(km|mi)\s*walk", message_content, re.IGNORECASE)
        if distance_match:
            walking_distance = float(distance_match.group(1))

        # Sleep duration: "Slept 7.5 hours"
        sleep_match = re.search(r"slept:?\s*(\d+\.?\d*)\s*hours", message_content, re.IGNORECASE)
        if sleep_match:
            sleep_duration_hours = float(sleep_match.group(1))

        # Daily goals: "Goals: 12000 steps, 30min run"
        goals_match = re.search(r"goals:?\s*(.+)", message_content, re.IGNORECASE)
        if goals_match:
            goals_text = goals_match.group(1)
            steps_goal_match = re.search(r"(\d+)\s*steps", goals_text, re.IGNORECASE)
            if steps_goal_match:
                daily_goals_steps = int(steps_goal_match.group(1))
            workout_goal_match = re.search(r"(\d+min\s*run|\d+min\s*workout)", goals_text, re.IGNORECASE) # Example, can be expanded
            if workout_goal_match:
                daily_goals_workout = workout_goal_match.group(1).strip()


        if any([weight, walking_steps, walking_distance, sleep_duration_hours, daily_goals_steps, daily_goals_workout]):
            cursor.execute(
                """
                INSERT INTO health_log (user_id, log_date, weight, walking_steps, walking_distance, sleep_duration_hours, daily_goals_steps, daily_goals_workout)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    date.today().isoformat(), # Log as YYYY-MM-DD
                    weight,
                    walking_steps,
                    walking_distance,
                    sleep_duration_hours,
                    daily_goals_steps,
                    daily_goals_workout
                )
            )
            conn.commit()
            return "Health data logged successfully! Thanks for keeping track."
        else:
            return "Could not parse health data from your message. Please use formats like 'Weight: 75.5kg', 'Walked 10000 steps', 'Slept 7.5 hours', 'Goals: 12000 steps, 30min run'."

    except sqlite3.Error as e:
        print(f"Error logging health data: {e}")
        return "An error occurred while trying to log your health data."
    finally:
        if conn:
            conn.close()

# --- Health Data Querying ---
def process_health_query(user_id: str, message_content: str) -> str:
    """
    Processes a health data query from the message content and retrieves data from the database.
    Returns a formatted response.
    """
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    conn = None
    response_message = "I couldn't find any data matching your query."
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # --- Parameter Extraction (simple keyword-based for now) ---
        metric = None
        time_period = None
        
        message_lower = message_content.lower()

        # Extract Metric
        if "walk" in message_lower or "distance" in message_lower:
            metric = "walking_distance"
        elif "steps" in message_lower:
            metric = "walking_steps"
        elif "weight" in message_lower:
            metric = "weight"
        elif "sleep" in message_lower or "duration" in message_lower:
            metric = "sleep_duration_hours"
        # Add more metrics as needed

        # Extract Time Period
        from datetime import datetime, timedelta
        end_date = date.today()
        start_date = None

        if "today" in message_lower:
            start_date = end_date
        elif "this week" in message_lower or "past week" in message_lower:
            start_date = end_date - timedelta(days=6) # Last 7 days including today
        elif "this month" in message_lower or "past month" in message_lower:
            # Simple approximation for "this month"
            start_date = end_date.replace(day=1)
        elif "last month" in message_lower:
            first_day_this_month = end_date.replace(day=1)
            start_date = (first_day_this_month - timedelta(days=1)).replace(day=1)
            end_date = first_day_this_month - timedelta(days=1)
        # Add more time periods as needed

        if metric and start_date:
            query = f"SELECT {metric} FROM health_log WHERE user_id = ? AND log_date BETWEEN ? AND ?"
            cursor.execute(query, (user_id, start_date.isoformat(), end_date.isoformat()))
            results = cursor.fetchall()

            if results:
                values = [r[0] for r in results if r[0] is not None] # Filter out None values
                if values:
                    # Basic aggregation
                    if metric in ["walking_distance", "walking_steps", "sleep_duration_hours"]:
                        total = sum(values)
                        response_message = f"Your total {metric.replace('_', ' ')} for the period is: {total:.1f}"
                    elif metric == "weight":
                        latest_weight = values[-1] # Get the most recent weight
                        response_message = f"Your latest recorded weight is: {latest_weight:.1f}"
                    # Add more sophisticated aggregation/reporting as needed
                else:
                    response_message = f"No {metric.replace('_', ' ')} data found for the specified period."
            else:
                response_message = f"No {metric.replace('_', ' ')} data found for the specified period."
        else:
            response_message = "I couldn't understand your health data query. Please specify a metric (e.g., 'walk', 'weight', 'sleep') and a time period (e.g., 'today', 'this week', 'this month')."

    except sqlite3.Error as e:
        print(f"Error querying health data: {e}")
        response_message = "An error occurred while trying to retrieve your health data."
    except Exception as e:
        print(f"Error in process_health_query: {e}")
        response_message = "An unexpected error occurred while processing your query."
    finally:
        if conn:
            conn.close()
    return response_message

# --- LangChain Setup ---


# Instantiate the local LLM
llm = Ollama(model="llama3:8b")

# --- Helper Function to Process Messages and Respond ---
async def _process_message_and_respond(channel_id: str, input_content: str, is_proactive_message: bool = False, user_id: str = None):
    """
    Processes a message through the LangChain agent and sends a response to Discord.
    
    Args:
        channel_id (str): The Discord channel ID.
        input_content (str): The content to be processed by the LLM.
        is_proactive_message (bool): True if this is a proactive message initiated by the system,
                                     False if it's a user-initiated message.
        user_id (str): The ID of the user sending the message, for health logging.
    """
    # Check for health data logging intent
    if input_content.lower().startswith("log health:") and user_id:
        response_message = log_health_data(user_id, input_content)
        # Send the response back to Discord
        try:
            requests.post(
                f"{DISCORD_BOT_URL}/send_discord_message/",
                params={"channel_id": channel_id, "message_content": response_message}
            )
        except requests.exceptions.RequestException as e:
            print(f"Error sending message to Discord bot: {e}")
        return {"status": "health data processed"}
    # Check for health data query intent
    elif any(input_content.lower().startswith(p) for p in ["how much", "how many", "how far", "what is my", "report my", "my "]) and user_id:
        response_message = process_health_query(user_id, input_content)
        # Send the response back to Discord
        try:
            requests.post(
                f"{DISCORD_BOT_URL}/send_discord_message/",
                params={"channel_id": channel_id, "message_content": response_message}
            )
        except requests.exceptions.RequestException as e:
            print(f"Error sending message to Discord bot: {e}")
        return {"status": "health query processed"}
    
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
    user_id = data.get("user_id") # Get user_id from the incoming data

    if author == "agent": # Prevent infinite loops if agent replies to its own messages
        return {"status": "message from agent ignored"}

    print(f"Received user-initiated message from {author} in channel {channel_id}: {content}")
    return await _process_message_and_respond(channel_id, content, is_proactive_message=False, user_id=user_id)


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
    initialize_health_database() # Initialize health database
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    run_agent_server()
