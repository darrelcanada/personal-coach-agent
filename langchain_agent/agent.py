import re
import json
import os
import sqlite3
from datetime import date, timedelta, datetime

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
import uvicorn

from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "..", "config.json")

try:
    with open(config_path, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: config.json not found.")
    exit(1)
except json.JSONDecodeError:
    print("Error: config.json is not valid JSON.")
    exit(1)

DISCORD_BOT_URL = config.get("_discord", {}).get("bot_url", "http://localhost:8000")
DB_CONNECTION_STRING = config.get("_database", {}).get(
    "db_connection_string", "sqlite:///memory.db"
)
CONVERSATION_HISTORY_LIMIT = config.get("_database", {}).get(
    "conversation_history_limit", 20
)
PERSONAS = config.get("personas", {})

DEFAULT_EXERCISES = [
    "push-ups",
    "pushups",
    "push ups",
    "planks",
    "plank",
    "squats",
    "squat",
    "lunges",
    "lunge",
    "mountain climbers",
    "burpees",
    "jumping jacks",
    "high knees",
    "calf raises",
    "leg raises",
    "crunches",
    "glute bridges",
]

JUMP_ROPE_DAYS = [0, 2, 4]
BODY_WEIGHT_DAYS = [1, 3, 5]
REST_DAY = 6


def _get_persona_prompt(channel_id: str) -> str:
    persona = PERSONAS.get(channel_id) or PERSONAS.get("default")
    if isinstance(persona, dict):
        return persona.get("prompt", "You are a helpful assistant.")
    return persona


def initialize_database():
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                user_id TEXT PRIMARY KEY,
                age INTEGER,
                sex TEXT,
                height_cm REAL,
                baseline_weight_kg REAL,
                goal_weight_kg REAL,
                activity_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                workout_date DATE NOT NULL,
                workout_type TEXT NOT NULL,
                distance_km REAL DEFAULT 4.0,
                completed INTEGER DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jump_rope_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                total_sets INTEGER DEFAULT 25,
                skips_per_set INTEGER DEFAULT 35,
                set_duration_sec INTEGER DEFAULT 30,
                rest_duration_sec INTEGER DEFAULT 10,
                sets_completed INTEGER,
                FOREIGN KEY (workout_id) REFERENCES workout_log(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bodyweight_exercise (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                exercise_name TEXT NOT NULL,
                sets INTEGER,
                reps INTEGER,
                duration_sec INTEGER,
                FOREIGN KEY (workout_id) REFERENCES workout_log(id)
            )
        """)
        conn.commit()
        print(f"Database initialized at {db_path}")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()


def log_health_data(user_id: str, message_content: str) -> str:
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        weight = None
        walking_steps = None
        walking_distance = None
        sleep_duration_hours = None
        daily_goals_steps = None
        daily_goals_workout = None

        weight_match = re.search(
            r"weight:?\s*(\d+\.?\d*)\s*(kg|lbs)", message_content, re.IGNORECASE
        )
        if weight_match:
            weight = float(weight_match.group(1))

        steps_match = re.search(r"(\d+)\s*steps", message_content, re.IGNORECASE)
        if steps_match:
            walking_steps = int(steps_match.group(1))

        distance_match = re.search(
            r"(\d+\.?\d*)\s*(km|mi)\s*walk", message_content, re.IGNORECASE
        )
        if distance_match:
            walking_distance = float(distance_match.group(1))

        sleep_match = re.search(
            r"slept:?\s*(\d+\.?\d*)\s*hours", message_content, re.IGNORECASE
        )
        if sleep_match:
            sleep_duration_hours = float(sleep_match.group(1))

        goals_match = re.search(r"goals:?\s*(.+)", message_content, re.IGNORECASE)
        if goals_match:
            goals_text = goals_match.group(1)
            steps_goal_match = re.search(r"(\d+)\s*steps", goals_text, re.IGNORECASE)
            if steps_goal_match:
                daily_goals_steps = int(steps_goal_match.group(1))
            workout_match = re.search(
                r"(\d+min\s*run|\d+min\s*workout)", goals_text, re.IGNORECASE
            )
            if workout_match:
                daily_goals_workout = workout_match.group(1).strip()

        if any(
            [
                weight,
                walking_steps,
                walking_distance,
                sleep_duration_hours,
                daily_goals_steps,
                daily_goals_workout,
            ]
        ):
            cursor.execute(
                """
                INSERT INTO health_log (user_id, log_date, weight, walking_steps, walking_distance, sleep_duration_hours, daily_goals_steps, daily_goals_workout)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    date.today().isoformat(),
                    weight,
                    walking_steps,
                    walking_distance,
                    sleep_duration_hours,
                    daily_goals_steps,
                    daily_goals_workout,
                ),
            )
            conn.commit()
            return "Health data logged successfully!"
        return "Could not parse health data. Try formats like 'Weight: 75.5kg', 'Walked 10000 steps', 'Slept 7.5 hours'."

    except sqlite3.Error as e:
        print(f"Error logging health data: {e}")
        return "An error occurred while logging your health data."
    finally:
        if conn:
            conn.close()


def process_health_query(user_id: str, message_content: str) -> str:
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    conn = None
    response = "I couldn't find any data matching your query."
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        message_lower = message_content.lower()

        metric = None
        if "walk" in message_lower or "distance" in message_lower:
            metric = "walking_distance"
        elif "steps" in message_lower:
            metric = "walking_steps"
        elif "weight" in message_lower:
            metric = "weight"
        elif "sleep" in message_lower:
            metric = "sleep_duration_hours"

        if not metric:
            return response

        end_date = date.today()
        start_date = None

        if "today" in message_lower:
            start_date = end_date
        elif "this week" in message_lower or "past week" in message_lower:
            start_date = end_date - timedelta(days=6)
        elif "this month" in message_lower or "past month" in message_lower:
            start_date = end_date.replace(day=1)
        elif "last month" in message_lower:
            first_day_this_month = end_date.replace(day=1)
            start_date = (first_day_this_month - timedelta(days=1)).replace(day=1)
            end_date = first_day_this_month - timedelta(days=1)

        if not start_date:
            return response

        cursor.execute(
            f"SELECT {metric} FROM health_log WHERE user_id = ? AND log_date BETWEEN ? AND ?",
            (user_id, start_date.isoformat(), end_date.isoformat()),
        )
        results = [r[0] for r in cursor.fetchall() if r[0] is not None]

        if results:
            if metric == "weight":
                return f"Your latest weight is: {results[-1]:.1f}"
            return f"Your total {metric.replace('_', ' ')} for the period is: {sum(results):.1f}"
        return f"No {metric.replace('_', ' ')} data found for the specified period."

    except sqlite3.Error as e:
        print(f"Error querying health data: {e}")
        return "An error occurred while retrieving your health data."
    finally:
        if conn:
            conn.close()


def process_user_profile(user_id: str, message_content: str) -> str:
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    conn = None
    response = "I couldn't understand your profile. Try 'Set profile: Age: 30, Sex: Male, Height: 175cm'."
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        message_lower = message_content.lower()

        age = None
        sex = None
        height_cm = None
        baseline_weight_kg = None
        goal_weight_kg = None
        activity_level = None

        age_match = re.search(r"age:?\s*(\d+)", message_lower)
        if age_match:
            age = int(age_match.group(1))

        sex_match = re.search(r"sex:?\s*(male|female|non-binary)", message_lower)
        if sex_match:
            sex = sex_match.group(1).capitalize()

        height_match = re.search(r"height:?\s*(\d+\.?\d*)\s*(cm|m)", message_lower)
        if height_match:
            height_val = float(height_match.group(1))
            height_cm = height_val * 100 if height_match.group(2) == "m" else height_val

        baseline_weight_match = re.search(
            r"(current|baseline)\s*weight:?\s*(\d+\.?\d*)\s*(kg|lbs)", message_lower
        )
        if baseline_weight_match:
            weight_val = float(baseline_weight_match.group(2))
            baseline_weight_kg = (
                weight_val * 0.453592
                if baseline_weight_match.group(3) == "lbs"
                else weight_val
            )

        goal_weight_match = re.search(
            r"goal\s*weight:?\s*(\d+\.?\d*)\s*(kg|lbs)", message_lower
        )
        if goal_weight_match:
            weight_val = float(goal_weight_match.group(1))
            goal_weight_kg = (
                weight_val * 0.453592
                if goal_weight_match.group(2) == "lbs"
                else weight_val
            )

        activity_match = re.search(
            r"activity:?\s*(sedentary|moderate|active)", message_lower
        )
        if activity_match:
            activity_level = activity_match.group(1)

        if not any(
            [age, sex, height_cm, baseline_weight_kg, goal_weight_kg, activity_level]
        ):
            return response

        cursor.execute("SELECT user_id FROM user_profile WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()

        if exists:
            update_fields = []
            update_values = []
            if age is not None:
                update_fields.append("age = ?")
                update_values.append(age)
            if sex is not None:
                update_fields.append("sex = ?")
                update_values.append(sex)
            if height_cm is not None:
                update_fields.append("height_cm = ?")
                update_values.append(height_cm)
            if baseline_weight_kg is not None:
                update_fields.append("baseline_weight_kg = ?")
                update_values.append(baseline_weight_kg)
            if goal_weight_kg is not None:
                update_fields.append("goal_weight_kg = ?")
                update_values.append(goal_weight_kg)
            if activity_level is not None:
                update_fields.append("activity_level = ?")
                update_values.append(activity_level)

            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                update_values.append(user_id)
                cursor.execute(
                    f"UPDATE user_profile SET {', '.join(update_fields)} WHERE user_id = ?",
                    tuple(update_values),
                )
                conn.commit()
            return "Profile updated successfully!"
        else:
            cursor.execute(
                """
                INSERT INTO user_profile (user_id, age, sex, height_cm, baseline_weight_kg, goal_weight_kg, activity_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    age,
                    sex,
                    height_cm,
                    baseline_weight_kg,
                    goal_weight_kg,
                    activity_level,
                ),
            )
            conn.commit()
            return "Profile created successfully!"

    except sqlite3.Error as e:
        print(f"Error managing user profile: {e}")
        return "An error occurred while managing your profile."
    finally:
        if conn:
            conn.close()


def _normalize_exercise_name(name: str) -> str:
    name = name.lower().strip()
    replacements = {
        "pushups": "push-ups",
        "push ups": "push-ups",
        "squat": "squats",
        "lunge": "lunges",
    }
    return replacements.get(name, name)


def _parse_workout_log(user_id: str, message_content: str) -> dict:
    parsed = {
        "workout_type": None,
        "distance_km": 4.0,
        "completed": 1,
        "notes": None,
        "jump_rope": None,
        "exercises": [],
    }

    content_lower = message_content.lower()

    if "jump rope" in content_lower or "jumping rope" in content_lower:
        parsed["workout_type"] = "jump_rope"
        parsed["jump_rope"] = {
            "total_sets": 25,
            "skips_per_set": 35,
            "set_duration_sec": 30,
            "rest_duration_sec": 10,
            "sets_completed": 25,
        }
        if "only" in content_lower or "only did" in content_lower:
            sets_match = re.search(r"only\s+(\d+)\s+sets?", content_lower)
            if sets_match:
                parsed["jump_rope"]["sets_completed"] = int(sets_match.group(1))
                parsed["completed"] = 0

    elif (
        "body weight" in content_lower
        or "bodyweight" in content_lower
        or "walk" in content_lower
    ):
        parsed["workout_type"] = "body_weight"

        exercise_pattern = r"(\w+[-\s]?\w*)\s+(\d+)[xX](\d+)(?:sec)?"
        for match in re.finditer(exercise_pattern, message_content):
            exercise_name = _normalize_exercise_name(match.group(1))
            sets = int(match.group(2))
            reps_or_duration = int(match.group(3))
            is_time = (
                "sec" in match.group(0).lower()
                or "seconds" in content_lower[match.start() : match.end() + 20]
            )

            parsed["exercises"].append(
                {
                    "name": exercise_name,
                    "sets": sets,
                    "reps": reps_or_duration if not is_time else None,
                    "duration_sec": reps_or_duration if is_time else None,
                }
            )

        if "only" in content_lower:
            parsed["completed"] = 0

    return parsed


def log_workout(user_id: str, message_content: str) -> str:
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    conn = None
    try:
        parsed = _parse_workout_log(user_id, message_content)

        if not parsed["workout_type"]:
            return (
                "I couldn't understand the workout type. Try:\n"
                "- 'Log workout: Jump rope day, 4km walk, 25 sets of 35 skips'\n"
                "- 'Log workout: Body weight day, push-ups 4x10, planks 3x30sec'"
            )

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO workout_log (user_id, workout_date, workout_type, distance_km, completed)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                user_id,
                date.today().isoformat(),
                parsed["workout_type"],
                parsed["distance_km"],
                parsed["completed"],
            ),
        )
        workout_id = cursor.lastrowid

        if parsed["workout_type"] == "jump_rope" and parsed["jump_rope"]:
            jr = parsed["jump_rope"]
            cursor.execute(
                """
                INSERT INTO jump_rope_session (workout_id, total_sets, skips_per_set, set_duration_sec, rest_duration_sec, sets_completed)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    workout_id,
                    jr["total_sets"],
                    jr["skips_per_set"],
                    jr["set_duration_sec"],
                    jr["rest_duration_sec"],
                    jr["sets_completed"],
                ),
            )

        elif parsed["workout_type"] == "body_weight":
            for ex in parsed["exercises"]:
                cursor.execute(
                    """
                    INSERT INTO bodyweight_exercise (workout_id, exercise_name, sets, reps, duration_sec)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        workout_id,
                        ex["name"],
                        ex["sets"],
                        ex.get("reps"),
                        ex.get("duration_sec"),
                    ),
                )

        conn.commit()

        if parsed["workout_type"] == "jump_rope":
            return f"Jump rope workout logged! {parsed['jump_rope']['sets_completed']} sets of {parsed['jump_rope']['skips_per_set']} skips completed."
        else:
            exercises_str = ", ".join(
                [f"{e['sets']}x{e['name']}" for e in parsed["exercises"]]
            )
            return f"Body weight workout logged! {len(parsed['exercises'])} exercises completed: {exercises_str}"

    except sqlite3.Error as e:
        print(f"Error logging workout: {e}")
        return "An error occurred while logging your workout."
    finally:
        if conn:
            conn.close()


def query_workout_history(user_id: str, message_content: str) -> str:
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    conn = None
    response = "I couldn't find workout data matching your query."
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        message_lower = message_content.lower()

        today = date.today()
        period_days = None
        workout_type = None

        if "today" in message_lower:
            period_days = 0
        elif "this week" in message_lower or "past week" in message_lower:
            period_days = 6
        elif "this month" in message_lower or "past month" in message_lower:
            period_days = 29
        elif "last week" in message_lower:
            period_days = 13
        elif "last month" in message_lower:
            period_days = 59

        if "jump rope" in message_lower:
            workout_type = "jump_rope"
        elif "body weight" in message_lower or "bodyweight" in message_lower:
            workout_type = "body_weight"

        start_date = today - timedelta(days=period_days) if period_days else None

        if period_days is None:
            cursor.execute(
                """
                SELECT COUNT(*) FROM workout_log 
                WHERE user_id = ? AND completed = 1
            """,
                (user_id,),
            )
        elif workout_type:
            cursor.execute(
                """
                SELECT COUNT(*) FROM workout_log 
                WHERE user_id = ? AND workout_date >= ? AND workout_type = ? AND completed = 1
            """,
                (user_id, start_date.isoformat(), workout_type),
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(*) FROM workout_log 
                WHERE user_id = ? AND workout_date >= ? AND completed = 1
            """,
                (user_id, start_date.isoformat()),
            )

        count = cursor.fetchone()[0]

        if count == 0:
            period_str = (
                "this period"
                if period_days is None
                else f"the last {period_days + 1} days"
            )
            type_str = f" {workout_type.replace('_', ' ')}" if workout_type else ""
            return f"You haven't logged any{type_str} workouts {period_str}."

        period_str = (
            "in total" if period_days is None else f"in the last {period_days + 1} days"
        )
        type_str = f" {workout_type.replace('_', ' ')}" if workout_type else ""
        response = f"You've completed {count} {type_str} workout{'' if count == 1 else 's'} {period_str}."

        if workout_type == "jump_rope" and period_days is not None:
            cursor.execute(
                """
                SELECT SUM(sets_completed) FROM workout_log w
                JOIN jump_rope_session j ON w.id = j.workout_id
                WHERE w.user_id = ? AND w.workout_date >= ?
            """,
                (user_id, start_date.isoformat()),
            )
            total_sets = cursor.fetchone()[0] or 0
            total_skips = total_sets * 35
            response += f" That's {total_sets} total sets and approximately {total_skips:,} skips!"

        return response

    except sqlite3.Error as e:
        print(f"Error querying workout history: {e}")
        return "An error occurred while retrieving your workout history."
    finally:
        if conn:
            conn.close()


def get_todays_workout_type() -> str:
    day = datetime.now().weekday()
    if day in JUMP_ROPE_DAYS:
        return "jump_rope"
    elif day in BODY_WEIGHT_DAYS:
        return "body_weight"
    else:
        return "rest"


def get_workout_reminder() -> str:
    workout_type = get_todays_workout_type()

    if workout_type == "jump_rope":
        return (
            "Tonight's your jump rope night! 🪢\n"
            "Remember: 4km walk around the town lap, then 25 sets of 35 skips "
            "(30 sec on, 10 sec rest). You've got this!"
        )
    elif workout_type == "body_weight":
        return (
            "Body weight workout night! 💪\n"
            "4km walk with your exercises:\n"
            "- Push-ups: 4 sets of 10\n"
            "- Planks: 3 sets of 30 seconds\n"
            "- Squats: 3 sets of 15\n"
            "Push through!"
        )
    else:
        return "Rest day today! Recover well for tomorrow."


llm = Ollama(model="llama3:8b")
LLM_MODEL = "llama3:8b"

app = FastAPI()


async def _send_to_discord(channel_id: str, message: str):
    try:
        requests.post(
            f"{DISCORD_BOT_URL}/send_discord_message/",
            params={"channel_id": channel_id, "message_content": message},
        )
    except requests.exceptions.RequestException as e:
        print(f"Error sending to Discord: {e}")


async def _process_message(
    channel_id: str, content: str, is_proactive: bool = False, user_id: str = None
):
    content_lower = content.lower()

    if content_lower.startswith("log health:") and user_id:
        return await _send_to_discord(channel_id, log_health_data(user_id, content))

    if content_lower.startswith("log workout:") and user_id:
        return await _send_to_discord(channel_id, log_workout(user_id, content))

    if (
        any(
            content_lower.startswith(p)
            for p in [
                "how much",
                "how many",
                "how far",
                "what is my",
                "report my",
                "my ",
            ]
        )
        and user_id
    ):
        if (
            "workout" in content_lower
            or "exercise" in content_lower
            or "jump rope" in content_lower
        ):
            return await _send_to_discord(
                channel_id, query_workout_history(user_id, content)
            )
        return await _send_to_discord(
            channel_id, process_health_query(user_id, content)
        )

    if (
        any(
            content_lower.startswith(p)
            for p in ["set profile:", "my profile is:", "update profile:"]
        )
        and user_id
    ):
        return await _send_to_discord(
            channel_id, process_user_profile(user_id, content)
        )

    if "tonight" in content_lower and "workout" in content_lower:
        return await _send_to_discord(channel_id, get_workout_reminder())

    if "workout" in content_lower and (
        "today" in content_lower or "type" in content_lower
    ):
        return await _send_to_discord(channel_id, get_workout_reminder())

    persona_prompt = _get_persona_prompt(channel_id)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", persona_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()

    history = SQLChatMessageHistory(
        session_id=channel_id, connection_string=DB_CONNECTION_STRING
    )
    limited_history = history.messages[-CONVERSATION_HISTORY_LIMIT:]

    print(f"""
============================================================
  LLM INVOCATION
============================================================
  Model:       {LLM_MODEL}
  Mode:        {"PROACTIVE" if is_proactive else "REACTIVE"}
  Channel:     {channel_id}
  History:     {len(limited_history)} messages in context
  Prompt:      {persona_prompt[:50].replace(chr(10), " ")}...
  Input:       {content[:50]}...
============================================================""")

    ai_response = chain.invoke({"input": content, "chat_history": limited_history})

    if not is_proactive:
        history.add_user_message(content)
    history.add_ai_message(ai_response)

    await _send_to_discord(channel_id, ai_response)


@app.post("/message")
async def receive_message(request: Request):
    data = await request.json()
    channel_id = str(data.get("channel_id"))
    author = data.get("author")
    content = data.get("content")
    user_id = data.get("user_id")

    if author == "agent":
        return {"status": "ignored"}

    print(f"Message from {author} in {channel_id}: {content}")
    await _process_message(channel_id, content, is_proactive=False, user_id=user_id)
    return {"status": "processed"}


@app.post("/proactive_message")
async def proactive_message_endpoint(request: Request):
    data = await request.json()
    channel_id = data.get("channel_id")
    message_content = data.get("message_content")
    if message_content == "WORKOUT_REMINDER":
        prompt = get_workout_reminder()
    else:
        prompt = message_content or get_workout_reminder()
    await _process_message(channel_id, prompt, is_proactive=True)
    return {"status": "proactive message sent"}


@app.get("/api/workout/today")
async def get_todays_workout():
    return {"workout_type": get_todays_workout_type()}


def run_server():
    print("Starting LangChain agent server...")
    initialize_database()
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    run_server()
