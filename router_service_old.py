import json
from openai import OpenAI

client = OpenAI()

def interpret_command(text):
    text_lower = text.lower().strip()
    print("RAW TEXT:", text_lower)

    # -----------------------------
    # REQUIRE WAKE WORD
    # -----------------------------
    if "hey jarvis" not in text_lower:
        print("MATCHED: ignore")
        return {"action": "ignore"}

    clean = text_lower.replace("hey jarvis", "", 1).strip()
    clean = clean.lstrip(", ").strip()
    print("CLEAN TEXT:", clean)

    # -----------------------------
    # WAKE ONLY
    # -----------------------------
    if clean == "":
        print("MATCHED: wake")
        return {"action": "wake"}

    # -----------------------------
    # MEMORY COMMANDS
    # -----------------------------
    if clean.startswith("remember that "):
        print("MATCHED: remember")
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
        print("MATCHED: recall_memory")
        return {"action": "recall_memory"}

    if clean.startswith("forget "):
        print("MATCHED: forget_memory")
        key = clean.replace("forget ", "", 1).strip().replace(" ", "_")
        return {
            "action": "forget_memory",
            "key": key
        }

    # -----------------------------
    # DEVELOPER COMMANDS
    # -----------------------------
    if "list project files" in clean or "show project files" in clean:
        return {"action": "list_project_files"}

    if clean.startswith("summarize file "):
        file_path = clean.replace("summarize file ", "", 1).strip()
        return {
            "action": "summarize_file",
            "file_path": file_path
        }

    if clean.startswith("read log "):
        file_path = clean.replace("read log ", "", 1).strip()
        return {
            "action": "read_log_file",
            "file_path": file_path
        }

    if clean.startswith("explain this error "):
        error_text = clean.replace("explain this error ", "", 1).strip()
        return {
            "action": "explain_error",
            "error_text": error_text
        }
    
    if clean.startswith("analyze file "):
        file_path = clean.replace("analyze file ", "", 1).strip()
        return {
            "action": "analyze_file",
            "file_path": file_path
        }

    if clean.startswith("what does file ") and clean.endswith(" do"):
        file_path = clean.replace("what does file ", "", 1).rsplit(" do", 1)[0].strip()
        return {
            "action": "analyze_file",
            "file_path": file_path
        }

    if clean.startswith("inspect file "):
        file_path = clean.replace("inspect file ", "", 1).strip()
        return {
            "action": "analyze_file",
            "file_path": file_path
        }
    
    if clean.startswith("suggest improvements for file "):
        file_path = clean.replace("suggest improvements for file ", "", 1).strip()
        return {
            "action": "suggest_file_improvements",
            "file_path": file_path
        }

    if clean.startswith("review file "):
        file_path = clean.replace("review file ", "", 1).strip()
        return {
            "action": "review_file",
            "file_path": file_path
        }

    if clean.startswith("what should i improve in "):
        file_path = clean.replace("what should i improve in ", "", 1).strip()
        return {
            "action": "suggest_file_improvements",
            "file_path": file_path
        }
    
    if "summarize this backend" in clean or "summarize this project" in clean:
        return {"action": "summarize_backend"}

    if "what files matter most" in clean or "what are the most important files" in clean:
        return {"action": "get_key_project_files"}

    if "how does this project work" in clean or "explain this project" in clean:
        return {"action": "explain_project_flow"}
    
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

    if clean.startswith("open file "):
        file_path = clean.replace("open file ", "", 1).strip()
        return {
            "action": "open_file_in_vscode",
            "file_path": file_path
        }

    if clean.startswith("generate a fix checklist for this error "):
        error_text = clean.replace("generate a fix checklist for this error ", "", 1).strip()
        return {
            "action": "generate_fix_checklist",
            "error_text": error_text
        }

    if clean.startswith("generate a fix checklist for "):
        error_text = clean.replace("generate a fix checklist for ", "", 1).strip()
        return {
            "action": "generate_fix_checklist",
            "error_text": error_text
        }
    
    if clean.startswith("help me fix this error "):
        error_text = clean.replace("help me fix this error ", "", 1).strip()
        return {
            "action": "help_fix_error",
            "error_text": error_text
        }

    if clean.startswith("diagnose this error "):
        error_text = clean.replace("diagnose this error ", "", 1).strip()
        return {
            "action": "diagnose_error",
            "error_text": error_text
        }

    if clean.startswith("what is the root cause of "):
        error_text = clean.replace("what is the root cause of ", "", 1).strip()
        return {
            "action": "suggest_root_cause",
            "error_text": error_text
        }


    # -----------------------------
    # TASK COMMANDS
    # -----------------------------
    if clean.startswith("add a high priority task to "):
        task_text = clean.replace("add a high priority task to ", "", 1).strip()
        due_date = None

        if " by " in task_text:
            task_text, due_date = task_text.split(" by ", 1)
            task_text = task_text.strip()
            due_date = due_date.strip()

        return {
            "action": "add_task",
            "task": task_text,
            "priority": "high",
            "due_date": due_date
        }

    if clean.startswith("add a medium priority task to "):
        task_text = clean.replace("add a medium priority task to ", "", 1).strip()
        due_date = None

        if " by " in task_text:
            task_text, due_date = task_text.split(" by ", 1)
            task_text = task_text.strip()
            due_date = due_date.strip()

        return {
            "action": "add_task",
            "task": task_text,
            "priority": "medium",
            "due_date": due_date
        }

    if clean.startswith("add a low priority task to "):
        task_text = clean.replace("add a low priority task to ", "", 1).strip()
        due_date = None

        if " by " in task_text:
            task_text, due_date = task_text.split(" by ", 1)
            task_text = task_text.strip()
            due_date = due_date.strip()

        return {
            "action": "add_task",
            "task": task_text,
            "priority": "low",
            "due_date": due_date
        }

    if clean.startswith("add a task to "):
        task_text = clean.replace("add a task to ", "", 1).strip()
        due_date = None

        if " by " in task_text:
            task_text, due_date = task_text.split(" by ", 1)
            task_text = task_text.strip()
            due_date = due_date.strip()

        return {
            "action": "add_task",
            "task": task_text,
            "priority": "medium",
            "due_date": due_date
        }

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

    if clean.startswith("remind me about "):
        reminder_text = clean.replace("remind me about ", "", 1).strip()
        return {
            "action": "add_reminder",
            "reminder": reminder_text
        }

    if "list my reminders" in clean or "what are my reminders" in clean:
        return {"action": "list_reminders"}

    if clean.startswith("complete reminder "):
        reminder_text = clean.replace("complete reminder ", "", 1).strip()
        return {
            "action": "complete_reminder",
            "reminder": reminder_text
        }

    if clean.startswith("add a task to "):
        task_text = clean.replace("add a task to ", "", 1).strip()
        return {
            "action": "add_task",
            "task": task_text
        }

    if clean.startswith("add task "):
        task_text = clean.replace("add task ", "", 1).strip()
        return {
            "action": "add_task",
            "task": task_text
        }

    if "list my tasks" in clean or "what are my tasks" in clean:
        return {"action": "list_tasks"}

    if clean.startswith("complete task "):
        task_text = clean.replace("complete task ", "", 1).strip()
        return {
            "action": "complete_task",
            "task": task_text
        }


    # -----------------------------
    # SIMPLE MULTI-COMMAND HANDLING
    # -----------------------------
    if " and " in clean:
        print("MATCHED: multi-command")
        parts = [part.strip() for part in clean.split(" and ") if part.strip()]
        commands = []

        for part in parts:
            if "time" in part:
                commands.append({"action": "tell_time"})

            elif "date" in part or "day" in part:
                commands.append({"action": "tell_date"})

            elif "youtube" in part:
                commands.append({"action": "open_website", "site": "youtube"})

            elif "google" in part and "search" not in part:
                commands.append({"action": "open_website", "site": "google"})

            elif "spotify" in part:
                commands.append({"action": "open_website", "site": "spotify"})

            elif "chatgpt" in part:
                commands.append({"action": "open_website", "site": "chatgpt"})

            elif "github" in part:
                commands.append({"action": "open_website", "site": "github"})

            elif "vscode" in part or "vs code" in part:
                commands.append({"action": "open_app", "app": "vscode"})

            elif part.startswith("search google for "):
                query = part.replace("search google for ", "", 1).strip()
                commands.append({
                    "action": "search_web",
                    "engine": "google",
                    "query": query
                })

            elif part.startswith("search for "):
                query = part.replace("search for ", "", 1).strip()
                commands.append({
                    "action": "search_web",
                    "engine": "google",
                    "query": query
                })

            elif part.startswith("search "):
                query = part.replace("search ", "", 1).strip()
                commands.append({
                    "action": "search_web",
                    "engine": "google",
                    "query": query
                })

            else:
                commands.append({
                    "action": "unknown",
                    "original_text": part
                })

        if commands:
            return commands

    # -----------------------------
    # LOCAL FAST RULES (single action)
    # -----------------------------
    if "time" in clean:
        print("MATCHED: tell_time")
        return {"action": "tell_time"}

    if "date" in clean or "day" in clean:
        print("MATCHED: tell_date")
        return {"action": "tell_date"}
    
    if "open my favorite site" in clean:
        return{"action": "open_favorite_site"}

    if "youtube" in clean:
        print("MATCHED: youtube")
        return {"action": "open_website", "site": "youtube"}

    if "google" in clean and "search" not in clean:
        print("MATCHED: google")
        return {"action": "open_website", "site": "google"}

    if "spotify" in clean:
        print("MATCHED: spotify")
        return {"action": "open_website", "site": "spotify"}

    if "chatgpt" in clean:
        print("MATCHED: chatgpt")
        return {"action": "open_website", "site": "chatgpt"}

    if "github" in clean:
        print("MATCHED: github")
        return {"action": "open_website", "site": "github"}

    if "vscode" in clean or "vs code" in clean:
        print("MATCHED: vscode")
        return {"action": "open_app", "app": "vscode"}

    if clean.startswith("search google for "):
        print("MATCHED: search google for")
        query = clean.replace("search google for ", "", 1).strip()
        return {
            "action": "search_web",
            "engine": "google",
            "query": query
        }

    if clean.startswith("search for "):
        print("MATCHED: search for")
        query = clean.replace("search for ", "", 1).strip()
        return {
            "action": "search_web",
            "engine": "google",
            "query": query
        }

    if clean.startswith("search "):
        print("MATCHED: search")
        query = clean.replace("search ", "", 1).strip()
        return {
            "action": "search_web",
            "engine": "google",
            "query": query
        }

# -----------------------------
# AI FALLBACK
# -----------------------------
    prompt = f"""
You are the command interpreter for a Jarvis-style assistant.

You must convert the user's speech into a JSON object or a JSON array of objects.

Rules:
- If the speech does NOT contain the phrase "hey jarvis", return:
  {{"action":"ignore"}}

- If the user only says "hey jarvis", return:
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
  "value": "github"
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

Important:
- Return ONLY valid JSON
- Do not explain anything
- Do not use markdown
- Preserve the wake-word rule
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
        print("MATCHED: ai_fallback")
        return json.loads(raw)

    except Exception:
        print("MATCHED: unknown")
        return {"action": "unknown", "original_text": text}