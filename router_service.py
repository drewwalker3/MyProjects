import json
import logging
import re
from openai import OpenAI
from time_utils import is_timestamp_active
from config import ASSISTANT_NAME, WAKE_PHRASES
from services.memory_service import (
    get_session_value,
    set_session_value,
    clear_session_value,
    get_conversation_history
)

client = OpenAI()
logger = logging.getLogger(__name__)


def make_open_website_command(site):
    return {
        "action": "open_website",
        "site": site
    }


def make_open_app_command(app):
    return {
        "action": "open_app",
        "app": app
    }


def make_search_command(query, engine="google"):
    return {
        "action": "search_web",
        "engine": engine,
        "query": query
    }


def make_add_task_command(task_text, priority="medium", due_date=None):
    return {
        "action": "add_task",
        "task": task_text,
        "priority": priority,
        "due_date": due_date
    }


def make_complete_task_command(task_text):
    return {
        "action": "complete_task",
        "task": task_text
    }


def make_add_reminder_command(reminder_text):
    return {
        "action": "add_reminder",
        "reminder": reminder_text
    }


def make_complete_reminder_command(reminder_text):
    return {
        "action": "complete_reminder",
        "reminder": reminder_text
    }


def make_file_action(action, file_path):
    return {
        "action": action,
        "file_path": file_path
    }


def make_error_action(action, error_text):
    return {
        "action": action,
        "error_text": error_text
    }


def is_conversational_request(clean):
    conversational_starters = [
        "how",
        "why",
        "what do you think",
        "what would you do",
        "explain",
        "tell me about",
        "compare",
        "help me understand",
        "what are some",
        "what should i",
        "can you explain"
    ]

    for starter in conversational_starters:
        if clean.startswith(starter):
            return True

    return False


def detect_clarification_need(clean):
    if clean.startswith("add ") and "task" not in clean and "reminder" not in clean:
        item_text = clean.replace("add ", "", 1).strip()
        if item_text:
            return {
                "mode": "clarification",
                "reply": "Do you want that as a task or a reminder?",
                "pending_text": item_text,
                "pending_options": ["add_task", "add_reminder"],
                "save_pending": True
            }

    if clean in ["remind me", "set a reminder"]:
        return {
            "mode": "clarification",
            "reply": "What would you like me to remind you about?",
            "pending_intent": "add_reminder",
            "missing_field": "reminder",
            "save_pending": True
        }
    
    if clean in ["open the file", "open a file", "open file"]:
        return {
            "mode": "clarification",
            "reply": "Which file do you want me to open?",
            "pending_intent": "open_file_in_vscode",
            "missing_field": "file_path",
            "save_pending": True
        }

    if clean in ["review the file", "review a file", "review file"]:
        return {
            "mode": "clarification",
            "reply": "Which file do you want me to review?",
            "pending_intent": "review_file",
            "missing_field": "file_path",
            "save_pending": True
        }

    if clean in ["analyze the file", "analyze a file", "analyze file"]:
        return {
            "mode": "clarification",
            "reply": "Which file do you want me to analyze?",
            "pending_intent": "analyze_file",
            "missing_field": "file_path",
            "save_pending": True
        }

    if clean in ["summarize the file", "summarize a file", "summarize file"]:
        return {
            "mode": "clarification",
            "reply": "Which file do you want me to summarize?",
            "pending_intent": "summarize_file",
            "missing_field": "file_path",
            "save_pending": True
        }

    return None


def build_conversational_reply(text):
    return {
        "mode": "conversation",
        "user_text": text
    }


def parse_memory_commands(clean):
    if clean.startswith("remember that "):
        memory_text = clean.replace("remember that ", "", 1).strip()

        if " is " in memory_text:
            key, value = memory_text.split(" is ", 1)
            return {
                "action": "remember",
                "key": key.strip().replace(" ", "_"),
                "value": value.strip()
            }

        return {
            "action": "remember",
            "key": "note",
            "value": memory_text
        }

    if "what do you remember about me" in clean or "what do you remember" in clean:
        return {"action": "recall_memory"}

    if clean.startswith("forget "):
        key = clean.replace("forget ", "", 1).strip().replace(" ", "_")
        return {
            "action": "forget_memory",
            "key": key
        }

    return None

def resolve_last_file_action(action_name):
    last_file = get_session_value("last_file")

    if not last_file:
        return {
            "mode": "clarification",
            "reply": "Which file are you referring to?",
            "pending_intent": action_name,
            "missing_field": "file_path",
            "save_pending": True
        }

    return {
        "action": action_name,
        "file_path": last_file
    }

def resolve_last_reply_followup(clean):
    last_reply = get_session_value("last_reply")

    if not last_reply:
        return None

    if clean in [
        "explain that more simply",
        "say that more simply",
        "make that simpler",
        "simplify that",
        "explain that simpler",
        "explain that more simpler",
        "say that simpler"
    ]:
        return {
            "mode": "conversation",
            "user_text": f"Explain this more simply: {last_reply}"
        }

    if clean in [
        "what do you mean by that",
        "explain that",
        "explain that more",
        "tell me more about that"
    ]:
        return {
            "mode": "conversation",
            "user_text": f"Explain this in more detail: {last_reply}"
        }

    if clean in [
        "summarize that shorter",
        "make that shorter",
        "shorten that"
    ]:
        return {
            "mode": "conversation",
            "user_text": f"Shorten this explanation: {last_reply}"
        }

    return None

def parse_dev_commands(clean):
    if "list project files" in clean or "show project files" in clean:
        return {"action": "list_project_files"}

    if clean.startswith("summarize file "):
        file_path = clean.replace("summarize file ", "", 1).strip()
        return make_file_action("summarize_file", file_path)

    if clean.startswith("read log "):
        file_path = clean.replace("read log ", "", 1).strip()
        return make_file_action("read_log_file", file_path)

    if clean.startswith("explain this error "):
        error_text = clean.replace("explain this error ", "", 1).strip()
        return make_error_action("explain_error", error_text)

    if clean.startswith("analyze file "):
        file_path = clean.replace("analyze file ", "", 1).strip()
        return make_file_action("analyze_file", file_path)

    if clean.startswith("what does file ") and clean.endswith(" do"):
        file_path = clean.replace("what does file ", "", 1).rsplit(" do", 1)[0].strip()
        return make_file_action("analyze_file", file_path)

    if clean.startswith("inspect file "):
        file_path = clean.replace("inspect file ", "", 1).strip()
        return make_file_action("analyze_file", file_path)

    if clean.startswith("suggest improvements for file "):
        file_path = clean.replace("suggest improvements for file ", "", 1).strip()
        return make_file_action("suggest_file_improvements", file_path)

    if clean.startswith("review file "):
        file_path = clean.replace("review file ", "", 1).strip()
        return make_file_action("review_file", file_path)

    if clean.startswith("what should i improve in "):
        file_path = clean.replace("what should i improve in ", "", 1).strip()
        return make_file_action("suggest_file_improvements", file_path)

    if "summarize this backend" in clean or "summarize this project" in clean:
        return {"action": "summarize_backend"}

    if "what files matter most" in clean or "what are the most important files" in clean:
        return {"action": "get_key_project_files"}

    if "how does this project work" in clean or "explain this project" in clean:
        return {"action": "explain_project_flow"}
    
    if "review that again" in clean or "review it again" in clean:
        return resolve_last_file_action("review_file")

    if "open that file" in clean or "open it" in clean:
        return resolve_last_file_action("open_file_in_vscode")

    if "summarize that file" in clean or "summarize it" in clean:
        return resolve_last_file_action("summarize_file")

    if "analyze that file" in clean or "analyze it" in clean:
        return resolve_last_file_action("analyze_file")

    if "what looks messy in this backend" in clean or "what looks messy in this project" in clean:
        return {"action": "detect_project_issues"}

    if "what should i refactor next" in clean:
        return {"action": "suggest_next_refactor"}

    if "what are likely weak points in this project" in clean or "what are weak points in this backend" in clean:
        return {"action": "detect_project_issues"}

    if "what files should i refactor" in clean or "what are the best refactor targets" in clean:
        return {"action": "get_refactor_targets"}

    if "open my project in vs code" in clean or "open the project in vs code" in clean:
        return {"action": "open_project_in_vscode"}

    if "what was i working on" in clean or "what is my current session" in clean:
        return {"action": "session_summary"}

    if "review that file again" in clean or "review the last file again" in clean:
        return {"action": "review_last_file"}

    if "help me fix that error" in clean or "fix that error again" in clean:
        return {"action": "fix_last_error"}

    if "clear my session memory" in clean or "clear session memory" in clean or "clear session" in clean:
        return {"action": "clear_session_memory"}

    if "rerun last command" in clean or "run that again" in clean or "do that again" in clean:
        return {"action": "rerun_last_command"}

    if "show database counts" in clean or "show db counts" in clean:
        return {"action": "get_database_counts"}

    if "how many tasks and reminders do i have stored" in clean:
        return {"action": "get_database_counts"}

    if clean.startswith("open file "):
        file_path = clean.replace("open file ", "", 1).strip()
        return make_file_action("open_file_in_vscode", file_path)

    if clean.startswith("generate a fix checklist for this error "):
        error_text = clean.replace("generate a fix checklist for this error ", "", 1).strip()
        return make_error_action("generate_fix_checklist", error_text)

    if clean.startswith("generate a fix checklist for "):
        error_text = clean.replace("generate a fix checklist for ", "", 1).strip()
        return make_error_action("generate_fix_checklist", error_text)

    if clean.startswith("help me fix this error "):
        error_text = clean.replace("help me fix this error ", "", 1).strip()
        return make_error_action("help_fix_error", error_text)

    if clean.startswith("diagnose this error "):
        error_text = clean.replace("diagnose this error ", "", 1).strip()
        return make_error_action("diagnose_error", error_text)

    if clean.startswith("what is the root cause of "):
        error_text = clean.replace("what is the root cause of ", "", 1).strip()
        return make_error_action("suggest_root_cause", error_text)

    return None


def parse_task_commands(clean):
    if clean.startswith("add a high priority task to "):
        task_text = clean.replace("add a high priority task to ", "", 1).strip()
        due_date = None

        if " by " in task_text:
            task_text, due_date = task_text.split(" by ", 1)
            task_text = task_text.strip()
            due_date = due_date.strip()

        return make_add_task_command(task_text, priority="high", due_date=due_date)

    if clean.startswith("add a medium priority task to "):
        task_text = clean.replace("add a medium priority task to ", "", 1).strip()
        due_date = None

        if " by " in task_text:
            task_text, due_date = task_text.split(" by ", 1)
            task_text = task_text.strip()
            due_date = due_date.strip()

        return make_add_task_command(task_text, priority="medium", due_date=due_date)

    if clean.startswith("add a low priority task to "):
        task_text = clean.replace("add a low priority task to ", "", 1).strip()
        due_date = None

        if " by " in task_text:
            task_text, due_date = task_text.split(" by ", 1)
            task_text = task_text.strip()
            due_date = due_date.strip()

        return make_add_task_command(task_text, priority="low", due_date=due_date)

    if clean.startswith("add a task to "):
        task_text = clean.replace("add a task to ", "", 1).strip()
        due_date = None

        if " by " in task_text:
            task_text, due_date = task_text.split(" by ", 1)
            task_text = task_text.strip()
            due_date = due_date.strip()

        return make_add_task_command(task_text, priority="medium", due_date=due_date)

    if clean.startswith("add ") and clean.endswith(" to my tasks"):
        task_text = clean.replace("add ", "", 1).rsplit(" to my tasks", 1)[0].strip()
        return make_add_task_command(task_text)

    if clean.startswith("add ") and clean.endswith(" to my task list"):
        task_text = clean.replace("add ", "", 1).rsplit(" to my task list", 1)[0].strip()
        return make_add_task_command(task_text)

    if clean.startswith("put ") and clean.endswith(" on my task list"):
        task_text = clean.replace("put ", "", 1).rsplit(" on my task list", 1)[0].strip()
        return make_add_task_command(task_text)

    if clean.startswith("add task "):
        task_text = clean.replace("add task ", "", 1).strip()
        return make_add_task_command(task_text)

    if "what's due today" in clean or "what is due today" in clean:
        return {"action": "get_tasks_due_today"}

    if "what tasks are due today" in clean or "show me what's due today" in clean:
        return {"action": "get_tasks_due_today"}

    if "what's due tomorrow" in clean or "what is due tomorrow" in clean:
        return {"action": "get_tasks_due_tomorrow"}

    if "what tasks are due tomorrow" in clean or "show me what's due tomorrow" in clean:
        return {"action": "get_tasks_due_tomorrow"}

    if "what's due this week" in clean or "what is due this week" in clean:
        return {"action": "get_tasks_due_this_week"}

    if "what tasks are due this week" in clean or "show me what's due this week" in clean:
        return {"action": "get_tasks_due_this_week"}

    if "what am i behind on" in clean:
        return {"action": "get_overdue_tasks"}

    if "what tasks are overdue" in clean or "show my overdue tasks" in clean:
        return {"action": "get_overdue_tasks"}

    if "list my high priority tasks" in clean:
        return {"action": "list_tasks", "priority": "high"}

    if "list my medium priority tasks" in clean:
        return {"action": "list_tasks", "priority": "medium"}

    if "list my low priority tasks" in clean:
        return {"action": "list_tasks", "priority": "low"}

    if "list my tasks" in clean or "what are my tasks" in clean:
        return {"action": "list_tasks"}

    if "what tasks are due" in clean or "list my dated tasks" in clean:
        return {"action": "get_due_tasks"}

    if "what should i work on first" in clean:
        return {"action": "get_most_urgent_task"}

    if "what is most urgent" in clean:
        return {"action": "get_most_urgent_task"}

    if "give me today's plan" in clean or "give me my plan" in clean:
        return {"action": "get_daily_plan"}

    if "what should i do today" in clean:
        return {"action": "get_daily_plan"}

    if "how am i doing" in clean or "give me my productivity summary" in clean:
        return {"action": "get_productivity_summary"}

    if "what have i completed" in clean or "list my completed tasks" in clean:
        return {"action": "get_completed_tasks"}

    if "how many tasks do i have left" in clean or "how many tasks are left" in clean:
        return {"action": "get_task_counts"}

    if "what is due soon" in clean or "what's due soon" in clean:
        return {"action": "get_due_soon_tasks"}

    if clean.startswith("complete task "):
        task_text = clean.replace("complete task ", "", 1).strip()
        return make_complete_task_command(task_text)

    return None


def parse_reminder_commands(clean):
    if clean.startswith("remind me about "):
        reminder_text = clean.replace("remind me about ", "", 1).strip()
        return make_add_reminder_command(reminder_text)

    if clean.startswith("remind me to "):
        reminder_text = clean.replace("remind me to ", "", 1).strip()
        return make_add_reminder_command(reminder_text)

    if clean.startswith("set a reminder for "):
        reminder_text = clean.replace("set a reminder for ", "", 1).strip()
        return make_add_reminder_command(reminder_text)

    if clean.startswith("add a reminder to "):
        reminder_text = clean.replace("add a reminder to ", "", 1).strip()
        return make_add_reminder_command(reminder_text)

    if "list my reminders" in clean or "what are my reminders" in clean:
        return {"action": "list_reminders"}

    if clean.startswith("complete reminder "):
        reminder_text = clean.replace("complete reminder ", "", 1).strip()
        return make_complete_reminder_command(reminder_text)

    return None


def parse_multi_commands(clean):
    if " and " not in clean:
        return None

    parts = [part.strip() for part in clean.split(" and ") if part.strip()]
    commands = []

    for part in parts:
        if "time" in part:
            commands.append({"action": "tell_time"})

        elif "date" in part or "day" in part:
            commands.append({"action": "tell_date"})

        elif "youtube" in part:
            commands.append(make_open_website_command("youtube"))

        elif "google" in part and "search" not in part:
            commands.append(make_open_website_command("google"))

        elif "spotify" in part:
            commands.append(make_open_website_command("spotify"))

        elif "chatgpt" in part:
            commands.append(make_open_website_command("chatgpt"))

        elif "github" in part:
            commands.append(make_open_website_command("github"))
        
        elif "forex" in part:
            commands.append(make_open_website_command("forex"))

        elif "vscode" in part or "vs code" in part:
            commands.append(make_open_app_command("vscode"))

        elif "applemusic" in part or "apple music" in part:
            commands.append(make_open_app_command("applemusic"))

        elif part.startswith("search google for "):
            query = part.replace("search google for ", "", 1).strip()
            commands.append(make_search_command(query))

        elif part.startswith("search for "):
            query = part.replace("search for ", "", 1).strip()
            commands.append(make_search_command(query))

        elif part.startswith("search "):
            query = part.replace("search ", "", 1).strip()
            commands.append(make_search_command(query))

        else:
            commands.append({
                "action": "unknown",
                "original_text": part
            })

    return commands if commands else None


def parse_system_commands(clean):
    clean_for_match = clean.lower().strip()
    clean_for_match = clean_for_match.rstrip(".!?")
    clean_for_match = " ".join(clean_for_match.split())

    clean_for_match = clean_for_match.replace("for me", "").strip()
    clean_for_match = clean_for_match.replace("can you ", "").strip()
    clean_for_match = clean_for_match.replace("could you ", "").strip()

    # Time
    time_phrases = {
        "what time is it",
        "what's the time",
        "whats the time",
        "current time",
        "time now",
        "show me the time",
        "show me the clock",
        "tell me the time"
    }

    if clean_for_match in time_phrases:
        return {"action": "tell_time"}

    # Date
    date_phrases = {
        "what is today's date",
        "what is todays date",
        "what's today's date",
        "whats todays date",
        "what is the date",
        "what's the date",
        "whats the date",
        "tell me the date",
        "what day is it",
        "tell me the day",
        "what is today",
        "what day is today"
    }

    if clean_for_match in date_phrases:
        return {"action": "tell_date"}

    # Favorite site
    if clean_for_match in {
        "open my favorite site",
        "open favorite site",
        "launch my favorite site"
    }:
        return {"action": "open_favorite_site"}

    if "open youtube" in clean_for_match:
        return make_open_website_command("youtube")

    if "open google" in clean_for_match:
        return make_open_website_command("google")

    if "open github" in clean_for_match:
        return make_open_website_command("github")

    if "open chatgpt" in clean_for_match:
        return make_open_website_command("chatgpt")

    if "open spotify" in clean_for_match:
        return make_open_website_command("spotify")

    if "open apple music" in clean_for_match:
        return make_open_app_command("apple music")

    if (
        "open vscode" in clean_for_match
        or "open vs code" in clean_for_match
        or "open visual studio code" in clean_for_match
    ):
        return make_open_app_command("vscode")

    # Open websites with explicit intent
    youtube_open_phrases = {
        "open youtube",
        "open up youtube",
        "launch youtube",
        "pull up youtube",
        "go to youtube"
    }

    github_open_phrases = {
        "open github",
        "open up github",
        "launch github",
        "pull up github",
        "go to github"
    }

    chatgpt_open_phrases = {
        "open chatgpt",
        "open up chatgpt",
        "launch chatgpt",
        "pull up chatgpt",
        "go to chatgpt"
    }

    google_open_phrases = {
        "open google",
        "open up google",
        "launch google",
        "pull up google",
        "go to google"
    }

    applemusic_open_phrases = {
        "open apple music",
        "open up apple music",
        "launch apple music",
        "pull up apple music",
        "go to apple music"
    }

    spotify_open_phrases = {
        "open spotify",
        "open up spotify",
        "launch spotify",
        "pull up spotify",
        "go to spotify"
    }

    if clean_for_match in youtube_open_phrases:
        return make_open_website_command("youtube")

    if clean_for_match in github_open_phrases:
        return make_open_website_command("github")

    if clean_for_match in chatgpt_open_phrases:
        return make_open_website_command("chatgpt")

    if clean_for_match in google_open_phrases:
        return make_open_website_command("google")

    if clean_for_match in spotify_open_phrases:
        return make_open_website_command("spotify")

    if clean_for_match in applemusic_open_phrases:
        return make_open_app_command("apple music")

    # Open apps with explicit intent
    vscode_open_phrases = {
        "open vscode",
        "open vs code",
        "open visual studio code",
        "launch vscode",
        "launch vs code",
        "launch visual studio code",
        "pull up vscode",
        "pull up vs code"
    }

    if clean_for_match in vscode_open_phrases:
        return make_open_app_command("vscode")

    # Search commands
    if clean_for_match.startswith("search google for "):
        query = clean_for_match.replace("search google for ", "", 1).strip()
        if query:
            return make_search_command(query)

    if clean_for_match.startswith("search for "):
        query = clean_for_match.replace("search for ", "", 1).strip()
        if query:
            return make_search_command(query)

    if clean_for_match.startswith("search "):
        query = clean_for_match.replace("search ", "", 1).strip()
        if query:
            return make_search_command(query)

    return None

def matches_exact(clean, phrases):
    return clean in phrases


def starts_with_any(clean, prefixes):
    return any(clean.startswith(prefix) for prefix in prefixes)

def ai_fallback(text):
    prompt = f"""
You are the action parser for a Jarvis-style assistant.

You must convert the user's speech into a JSON object or a JSON array of objects for executable actions only.

Rules:

- If the user only says "hey rex", return:
  {{"action":"wake"}}

Allowed action values:
- ignore
- wake
- tell_time
- tell_date
- open_website
- open_app
- search_web
- remember
- recall_memory
- forget_memory
- unknown
- add_task
- list_tasks
- complete_task
- get_most_urgent_task
- get_daily_plan
- get_due_soon_tasks
- add_reminder
- list_reminders
- complete_reminder
- list_project_files
- summarize_file
- read_log_file
- explain_error
- analyze_file
- suggest_file_improvements
- review_file
- detect_project_issues
- suggest_next_refactor
- get_refactor_targets
- open_project_in_vscode
- open_file_in_vscode
- generate_fix_checklist
- diagnose_error
- suggest_root_cause
- help_fix_error
- session_summary
- review_last_file
- fix_last_error
- summarize_backend
- get_key_project_files
- explain_project_flow
- get_due_tasks
- get_completed_tasks
- get_task_counts
- get_productivity_summary
- open_favorite_site
- clear_session_memory
- rerun_last_command
- get_database_counts
- get_tasks_due_today
- get_tasks_due_tomorrow
- get_tasks_due_this_week
- get_overdue_tasks

Schemas:

1. tell_time
{{
  "action": "tell_time"
}}

2. tell_date
{{
  "action": "tell_date"
}}

3. open_website
{{
  "action": "open_website",
  "site": "youtube"
}}

4. open_app
{{
  "action": "open_app",
  "app": "vscode"
}}

5. search_web
{{
  "action": "search_web",
  "engine": "google",
  "query": "python internships"
}}

6. remember
{{
  "action": "remember",
  "key": "favorite_site",
  "value": "forex"
}}

7. recall_memory
{{
  "action": "recall_memory"
}}

8. forget_memory
{{
  "action": "forget_memory",
  "key": "favorite_site"
}}

9. unknown
{{
  "action": "unknown",
  "original_text": "..."
}}

10. add_task
{{
  "action": "add_task",
  "task": "finish my resume"
}}

11. list_tasks
{{
  "action": "list_tasks"
}}

12. complete_task
{{
  "action": "complete_task",
  "task": "finish my resume"
}}

13. get_most_urgent_task
{{
  "action": "get_most_urgent_task"
}}

14. get_daily_plan
{{
  "action": "get_daily_plan"
}}

15. get_due_soon_tasks
{{
  "action": "get_due_soon_tasks"
}}

16. add_reminder
{{
  "action": "add_reminder",
  "reminder": "finish my resume"
}}

17. list_reminders
{{
  "action": "list_reminders"
}}

18. complete_reminder
{{
  "action": "complete_reminder",
  "reminder": "finish my resume"
}}

19. list_project_files
{{
  "action": "list_project_files"
}}

20. summarize_file
{{
  "action": "summarize_file",
  "file_path": "app.py"
}}

21. read_log_file
{{
  "action": "read_log_file",
  "file_path": "backend.log"
}}

22. explain_error
{{
  "action": "explain_error",
  "error_text": "Connection refused"
}}

23. analyze_file
{{
  "action": "analyze_file",
  "file_path": "app.py"
}}

24. suggest_file_improvements
{{
  "action": "suggest_file_improvements",
  "file_path": "app.py"
}}

25. review_file
{{
  "action": "review_file",
  "file_path": "router_service.py"
}}

26. detect_project_issues
{{
  "action": "detect_project_issues"
}}

27. suggest_next_refactor
{{
  "action": "suggest_next_refactor"
}}

28. get_refactor_targets
{{
  "action": "get_refactor_targets"
}}

29. open_project_in_vscode
{{
  "action": "open_project_in_vscode"
}}

30. open_file_in_vscode
{{
  "action": "open_file_in_vscode",
  "file_path": "app.py"
}}

31. generate_fix_checklist
{{
  "action": "generate_fix_checklist",
  "error_text": "connection refused"
}}

32. diagnose_error
{{
  "action": "diagnose_error",
  "error_text": "connection refused"
}}

33. suggest_root_cause
{{
  "action": "suggest_root_cause",
  "error_text": "connection refused"
}}

34. help_fix_error
{{
  "action": "help_fix_error",
  "error_text": "connection refused"
}}

35. session_summary
{{
  "action": "session_summary"
}}

36. review_last_file
{{
  "action": "review_last_file"
}}

37. fix_last_error
{{
  "action": "fix_last_error"
}}

38. summarize_backend
{{
  "action": "summarize_backend"
}}

39. get_key_project_files
{{
  "action": "get_key_project_files"
}}

40. explain_project_flow
{{
  "action": "explain_project_flow"
}}

41. get_due_tasks
{{
  "action": "get_due_tasks"
}}

42. get_completed_tasks
{{
  "action": "get_completed_tasks"
}}

43. get_task_counts
{{
  "action": "get_task_counts"
}}

44. get_productivity_summary
{{
  "action": "get_productivity_summary"
}}

45. open_favorite_site
{{
  "action": "open_favorite_site"
}}

46. clear_session_memory
{{
  "action": "clear_session_memory"
}}

47. rerun_last_command
{{
  "action": "rerun_last_command"
}}

48. get_database_counts
{{
  "action": "get_database_counts"
}}

49. get_tasks_due_today
{{
  "action": "get_tasks_due_today"
}}

50. get_tasks_due_tomorrow
{{
  "action": "get_tasks_due_tomorrow"
}}

51. get_tasks_due_this_week
{{
  "action": "get_tasks_due_this_week"
}}

52. get_overdue_tasks
{{
  "action": "get_overdue_tasks"
}}

If the user asks for multiple actions, return a JSON array.

Example:
[
  {{"action":"open_website","site":"youtube"}},
  {{"action":"open_website","site":"github"}}
]

Known website names:
- youtube
- google
- spotify
- chatgpt
- github

Known app names:
- vscode
- apple music

Important:
- Return ONLY valid JSON
- Do not explain anything
- Do not use markdown
- Preserve the wake-word rule
- If the request is conversational rather than an executable action, return unknown
- If you are unsure, return unknown

User speech:
{text}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )
        raw = response.output_text.strip()
        logger.info("MATCHED: ai_fallback")
        return json.loads(raw)

    except Exception as e:
        logger.exception("AI fallback failed: %s", e)
        return {"action": "unknown", "original_text": text}

def interpret_command(clean):
    if clean == "":
        return {"action": "wake"}

    for parser in [
        parse_preference_commands,
        parse_memory_commands,
        parse_dev_commands,
        parse_task_commands,
        parse_reminder_commands,
        parse_multi_commands,
        parse_system_commands,
    ]:
        result = parser(clean)
        if result is not None:
            return result

    return {"action": "unknown"}

def resolve_pending_clarification(clean):
    pending_text = get_session_value("pending_text")
    pending_options_raw = get_session_value("pending_options")
    pending_intent = get_session_value("pending_intent")
    missing_field = get_session_value("missing_field")

    pending_options = None
    if pending_options_raw:
        try:
            pending_options = json.loads(pending_options_raw)
        except Exception:
            pending_options = None

    if pending_text and pending_options:
        if clean in ["task", "a task"] and "add_task" in pending_options:
            clear_session_value("pending_text")
            clear_session_value("pending_options")
            clear_session_value("pending_intent")
            clear_session_value("missing_field")

            return {
                "mode": "action",
                "action": {
                    "action": "add_task",
                    "task": pending_text,
                    "priority": "medium",
                    "due_date": None
                }
            }

        if clean in ["reminder", "a reminder"] and "add_reminder" in pending_options:
            clear_session_value("pending_text")
            clear_session_value("pending_options")
            clear_session_value("pending_intent")
            clear_session_value("missing_field")

            return {
                "mode": "action",
                "action": {
                    "action": "add_reminder",
                    "reminder": pending_text
                }
            }

    if pending_intent == "add_reminder" and missing_field == "reminder":
        if clean:
            clear_session_value("pending_text")
            clear_session_value("pending_options")
            clear_session_value("pending_intent")
            clear_session_value("missing_field")

            return {
                "mode": "action",
                "action": {
                    "action": "add_reminder",
                    "reminder": clean
                }
            }
        
    if pending_intent in ["open_file_in_vscode", "review_file", "analyze_file", "summarize_file"] and missing_field == "file_path":
        if clean:
            clear_session_value("pending_text")
            clear_session_value("pending_options")
            clear_session_value("pending_intent")
            clear_session_value("missing_field")

            return {
                "mode": "action",
                "action": {
                    "action": pending_intent,
                    "file_path": clean
                }
            }

    return None

def detect_mixed_turn(clean):
    separators = [" then ", " and then "]

    for separator in separators:
        if separator in clean:
            left, right = clean.split(separator, 1)
            left = left.strip()
            right = right.strip()

            if is_conversational_request(left):
                action_result = interpret_command(f"hey {ASSISTANT_NAME} {right}")

                if isinstance(action_result, list):
                    return {
                        "mode": "mixed",
                        "conversation_text": left,
                        "action": action_result
                    }

                if action_result.get("action") != "unknown":
                    return {
                        "mode": "mixed",
                        "conversation_text": left,
                        "action": action_result
                    }

    return None

def resolve_conversation_followup(clean):
    last_reply = get_session_value("last_reply")
    conversation_history = get_conversation_history()

    if clean == "continue":
        if last_reply:
            return {
                "mode": "conversation",
                "user_text": f"Continue this explanation: {last_reply}"
            }

    if clean in ["go deeper", "go deeper on that", "expand on that"]:
        if last_reply:
            return {
                "mode": "conversation",
                "user_text": f"Go deeper on this explanation: {last_reply}"
            }

    if clean in ["what were we just talking about", "what are we talking about"]:
        if conversation_history:
            return {
                "mode": "conversation",
                "user_text": "Summarize what we were just talking about."
            }

    return None

def resolve_personality_prompt(clean):
    social_map = {
        "how are you": "How are you doing?",
        "how are you doing": "How are you doing?",
        "hows it going": "How's it going?",
        "how's it going": "How's it going?",
        "what's up": "What's up?",
        "whats up": "What's up?",
        "good morning": "Good morning",
        "good night": "Good night",
        "thank you": "Thank you",
        "thanks": "Thanks",
        "who are you": "Who are you?"
    }

    for phrase, prompt in social_map.items():
        if clean == phrase:
            return {
                "mode": "conversation",
                "user_text": prompt
            }

    return None

def resolve_reference_action(clean):
    clean_for_match = clean.rstrip(".!?").strip().lower()

    last_recommendation = get_session_value("last_recommendation")
    last_reply = get_session_value("last_reply")

    task_source = last_recommendation or last_reply
    if not task_source:
        return None

    if clean_for_match in [
        "add that as a task",
        "add that to my tasks",
        "turn that into a task",
        "make that a task"
    ]:
        return {
            "mode": "action",
            "action": {
                "action": "add_task",
                "task": task_source,
                "priority": "medium",
                "due_date": None
            }
        }

    if clean_for_match in [
        "remind me about that",
        "make that a reminder",
        "turn that into a reminder"
    ]:
        return {
            "mode": "action",
            "action": {
                "action": "add_reminder",
                "reminder": task_source
            }
        }

    return None

def resolve_ranked_reference_action(clean):
    clean_for_match = clean.rstrip(".!?").strip().lower()

    raw_suggestions = get_session_value("last_suggestions")
    if not raw_suggestions:
        return None

    try:
        suggestions = json.loads(raw_suggestions)
    except Exception:
        return None

    if not isinstance(suggestions, list) or not suggestions:
        return None

    ordinal_map = {
        "first": 0,
        "second": 1,
        "third": 2
    }

    selected_index = None
    for word, index in ordinal_map.items():
        if word in clean_for_match:
            selected_index = index
            break

    if selected_index is None:
        return None

    if selected_index >= len(suggestions):
        return None

    selected_text = suggestions[selected_index]

    if any(phrase in clean_for_match for phrase in [
        "make the",
        "turn the",
        "add the"
    ]) and "task" in clean_for_match:
        return {
            "mode": "action",
            "action": {
                "action": "add_task",
                "task": selected_text,
                "priority": "medium",
                "due_date": None
            }
        }

    if any(phrase in clean_for_match for phrase in [
        "make the",
        "turn the",
        "add the"
    ]) and "reminder" in clean_for_match:
        return {
            "mode": "action",
            "action": {
                "action": "add_reminder",
                "reminder": selected_text
            }
        }

    if "what" in clean_for_match and any(word in clean_for_match for word in ["first", "second", "third"]):
        return {
            "mode": "conversation",
            "user_text": f"Repeat this suggestion more clearly: {selected_text}"
        }

    return None

def resolve_best_suggestion_action(clean):
    clean_for_match = clean.rstrip(".!?").strip().lower()

    raw_suggestions = get_session_value("last_suggestions")
    if not raw_suggestions:
        return None

    try:
        suggestions = json.loads(raw_suggestions)
    except Exception:
        return None

    if not isinstance(suggestions, list) or not suggestions:
        return None

    if clean_for_match in [
        "pick the best one",
        "do the best one",
        "do whichever is best",
        "do whichever is most important",
        "pick the most important one"
    ]:
        joined = "\n".join(f"{i+1}. {item}" for i, item in enumerate(suggestions))

        return {
            "mode": "conversation",
            "user_text": (
                "Choose the single best and most important suggestion from this list, "
                "and explain briefly why:\n" + joined
            )
        }

    return None

def resolve_bulk_suggestion_action(clean):
    clean_for_match = clean.rstrip(".!?").strip().lower()

    raw_suggestions = get_session_value("last_suggestions")
    if not raw_suggestions:
        return None

    try:
        suggestions = json.loads(raw_suggestions)
    except Exception:
        return None

    if not isinstance(suggestions, list) or not suggestions:
        return None

    if clean_for_match in [
        "make all three tasks",
        "make all of them tasks",
        "turn all of them into tasks",
        "add all three to my tasks"
    ]:
        actions = []
        for item in suggestions[:3]:
            if isinstance(item, str) and item.strip():
                actions.append({
                    "action": "add_task",
                    "task": item.strip(),
                    "priority": "medium",
                    "due_date": None
                })

        if actions:
            return {
                "mode": "action",
                "action": actions
            }

    if clean_for_match in [
        "make all three reminders",
        "make all of them reminders",
        "turn all of them into reminders",
        "add all three to my reminders"
    ]:
        actions = []
        for item in suggestions[:3]:
            if isinstance(item, str) and item.strip():
                actions.append({
                    "action": "add_reminder",
                    "reminder": item.strip()
                })

        if actions:
            return {
                "mode": "action",
                "action": actions
            }

    return None

def parse_preference_commands(clean):
    clean_for_match = clean.lower().strip()
    clean_for_match = clean_for_match.rstrip(".!?")
    clean_for_match = " ".join(clean_for_match.split())

    if clean_for_match.startswith("call me "):
        title = clean_for_match.replace("call me ", "", 1).strip()
        if title:
            return {
                "action": "set_user_title",
                "title": title
            }

    if clean_for_match in [
        "keep your answers short",
        "keep your responses short",
        "be brief",
        "be more concise"
    ]:
        return {
            "action": "set_response_length",
            "length": "short"
        }

    if clean_for_match in [
        "give me longer answers",
        "give longer responses",
        "be more detailed",
        "give more detail"
    ]:
        return {
            "action": "set_response_length",
            "length": "long"
        }

    if clean_for_match.startswith("my favorite site is "):
        site = clean_for_match.replace("my favorite site is ", "", 1).strip()
        if site:
            return {
                "action": "set_favorite_site",
                "site": site
            }

    if clean_for_match.startswith("my preferred editor is "):
        editor = clean_for_match.replace("my preferred editor is ", "", 1).strip()
        if editor:
            return {
                "action": "set_preferred_editor",
                "editor": editor
            }

    if clean_for_match in [
        "use vscode by default",
        "use vs code by default"
    ]:
        return {
            "action": "set_preferred_editor",
            "editor": "vscode"
        }

    if clean_for_match in [
        "open my editor",
        "open my preferred editor"
    ]:
        return {
            "action": "open_preferred_editor"
        }

    if clean_for_match in [
        "open my favorite site",
        "open favorite site"
    ]:
        return {
            "action": "open_favorite_site"
        }

    return None

def interpret_message(text):
    if not isinstance(text, str) or not text.strip():
        return {"mode": "action", "action": {"action": "ignore"}}

    text_lower = text.lower().strip()
    logger.info("RAW TEXT: %s", text_lower)

    normalized = " ".join(text_lower.split())
    logger.info("NORMALIZED TEXT: %s", normalized)

    active_until = get_session_value("jarvis_active_until")
    session_active = is_timestamp_active(active_until)

    logger.info("ACTIVE UNTIL RAW = %r", active_until)
    logger.info("SESSION ACTIVE = %s", session_active)
    logger.info("NORMALIZED = %r", normalized)

    wake_phrase_used = None
    for phrase in WAKE_PHRASES:
        if phrase in normalized:
            wake_phrase_used = phrase
            break

    logger.info("WAKE PHRASE USED = %r", wake_phrase_used)

    wake_word_present = wake_phrase_used is not None

    if not wake_word_present and not session_active:
        return {"mode": "action", "action": {"action": "ignore"}}

    clean = normalized
    if wake_phrase_used:
        clean = clean.replace(wake_phrase_used, "", 1).strip()

    clean = clean.lstrip(", ").strip()
    logger.info("CLEAN TEXT: %s", clean)

    if clean == "":
        return {"mode": "action", "action": {"action": "wake"}}

    pending_result = resolve_pending_clarification(clean)
    if pending_result is not None:
        return pending_result

    reply_followup = resolve_last_reply_followup(clean)
    if reply_followup is not None:
        return reply_followup

    conversation_followup = resolve_conversation_followup(clean)
    if conversation_followup is not None:
        return conversation_followup

    personality_result = resolve_personality_prompt(clean)
    if personality_result is not None:
        return personality_result

    mixed_result = detect_mixed_turn(clean)
    if mixed_result is not None:
        return mixed_result

    clarification = detect_clarification_need(clean)
    if clarification is not None:
        return clarification

    action_result = interpret_command(clean)

    if isinstance(action_result, list):
        return {"mode": "action", "action": action_result}

    if isinstance(action_result, dict):
        if action_result.get("action") not in ["ignore", "unknown"]:
            return {"mode": "action", "action": action_result}

    return {"mode": "conversation", "user_text": clean}