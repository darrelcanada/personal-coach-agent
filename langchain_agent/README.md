# LangChain Personal Coach Agent

FastAPI server providing AI-driven responses, persona management, workout tracking, and proactive messaging for the Discord bot.

## Features

- **Dynamic Personas**: Channel-specific AI personas via `config.json`
- **Workout Tracking**: Structured walking routine with jump rope and bodyweight exercises
- **Health Logging**: Weight, steps, sleep tracking
- **User Profiles**: Age, height, goals storage
- **Conversation Memory**: SQLite-backed per-channel history
- **Proactive Reminders**: Day-based workout notifications

## Database Schema

### workout_log
Main workout session record.
```sql
CREATE TABLE workout_log (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    workout_date DATE,
    workout_type TEXT,  -- 'jump_rope' or 'body_weight'
    distance_km REAL DEFAULT 4.0,
    completed INTEGER DEFAULT 1,
    notes TEXT
);
```

### jump_rope_session
Jump rope specific data.
```sql
CREATE TABLE jump_rope_session (
    id INTEGER PRIMARY KEY,
    workout_id INTEGER,
    total_sets INTEGER DEFAULT 25,
    skips_per_set INTEGER DEFAULT 35,
    set_duration_sec INTEGER DEFAULT 30,
    rest_duration_sec INTEGER DEFAULT 10,
    sets_completed INTEGER
);
```

### bodyweight_exercise
Exercises performed during body weight workouts.
```sql
CREATE TABLE bodyweight_exercise (
    id INTEGER PRIMARY KEY,
    workout_id INTEGER,
    exercise_name TEXT,
    sets INTEGER,
    reps INTEGER,
    duration_sec INTEGER
);
```

### health_log
General health metrics.
```sql
CREATE TABLE health_log (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    log_date DATE,
    weight REAL,
    walking_steps INTEGER,
    walking_distance REAL,
    sleep_duration_hours REAL,
    daily_goals_steps INTEGER,
    daily_goals_workout TEXT
);
```

### user_profile
User profile data.
```sql
CREATE TABLE user_profile (
    user_id TEXT PRIMARY KEY,
    age INTEGER,
    sex TEXT,
    height_cm REAL,
    baseline_weight_kg REAL,
    goal_weight_kg REAL,
    activity_level TEXT
);
```

## User Commands

### Log Workouts

**Jump Rope (Mon/Wed/Fri):**
```
Log workout: Jump rope night
Log workout: Jump rope day, 25 sets of 35 skips
Log workout: Jump rope, only did 20 sets
```

**Body Weight (Tues/Thur/Sat):**
```
Log workout: Body weight day, push-ups 4x10, planks 3x30sec, squats 3x15
Log workout: Body weight, lunges 3x12, mountain climbers 3x20
Log workout: Body weight, push-ups 4x10 (only 3 sets)
```

### Query Workouts
```
How many workouts did I do this week?
How many jump rope workouts this month?
How many body weight exercises last week?
Show my workout history
```

### Workout Info
```
What's tonight's workout?
What type of workout is today?
```

### Health Data
```
Log health: Weight: 75.5kg
Log health: Walked 10000 steps
Log health: Slept 7.5 hours

How much did I walk this week?
What is my weight today?
```

### User Profile
```
Set profile: Age: 30, Sex: Male, Height: 175cm
Update profile: Activity: active
```

## API Endpoints

### POST /message
Receives messages from Discord bot.
```json
{
    "channel_id": "123456",
    "author": "username",
    "user_id": "987654",
    "content": "Log workout: Jump rope night"
}
```

### POST /proactive_message
Triggers proactive message from scheduler.
```json
{
    "channel_id": "123456",
    "message_content": "WORKOUT_REMINDER"
}
```
Use `WORKOUT_REMINDER` for automatic day-based reminders.

### GET /api/workout/today
Returns today's workout type.
```json
{"workout_type": "jump_rope"}
```

## Configuration

In `config.json`, each persona can have proactive scheduling:

```json
"proactive_scheduling": {
    "enabled": true,
    "interval_seconds": 7200,
    "time_window": { "start_hour": 18, "end_hour": 19 },
    "message_content": "WORKOUT_REMINDER"
}
```

Set `message_content` to `"WORKOUT_REMINDER"` for automatic day-based workout reminders.

## Direct Database Access

```bash
sqlite3 memory.db "SELECT * FROM workout_log;"
sqlite3 memory.db "SELECT * FROM jump_rope_session;"
sqlite3 memory.db "SELECT * FROM bodyweight_exercise;"
sqlite3 memory.db "SELECT * FROM health_log;"
sqlite3 memory.db "SELECT * FROM user_profile;"
```
