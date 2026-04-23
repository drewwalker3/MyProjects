from database import get_connection


def add_task(task_text, priority="medium", due_date=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (task, completed, priority, due_date)
        VALUES (?, ?, ?, ?)
    """, (task_text, 0, priority, due_date))

    conn.commit()
    conn.close()

    message = f"Okay, I added the {priority} priority task: {task_text}"
    if due_date:
        message += f", due {due_date}"
    return message + "."


def list_tasks(priority_filter=None):
    conn = get_connection()
    cursor = conn.cursor()

    if priority_filter:
        cursor.execute("""
            SELECT * FROM tasks
            WHERE completed = 0 AND priority = ?
            ORDER BY id ASC
        """, (priority_filter,))
    else:
        cursor.execute("""
            SELECT * FROM tasks
            WHERE completed = 0
            ORDER BY id ASC
        """)

    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        return "You do not have any incomplete tasks."

    parts = []
    for i, task in enumerate(tasks, start=1):
        part = f"{i}. {task['task']} ({task['priority']} priority"
        if task["due_date"]:
            part += f", due {task['due_date']}"
        part += ")"
        parts.append(part)

    return "Here are your tasks: " + " ".join(parts)


def complete_task(task_text):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM tasks
        WHERE LOWER(task) = LOWER(?) AND completed = 0
        LIMIT 1
    """, (task_text,))
    task = cursor.fetchone()

    if not task:
        conn.close()
        return f"I could not find an incomplete task named '{task_text}'."

    cursor.execute("""
        UPDATE tasks
        SET completed = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (task["id"],))

    conn.commit()
    conn.close()

    return f"Okay, I marked '{task_text}' as complete."


def get_due_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM tasks
        WHERE completed = 0 AND due_date IS NOT NULL
        ORDER BY id ASC
    """)

    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        return "You do not have any tasks with due dates."

    parts = [
        f"{i+1}. {task['task']} (due {task['due_date']})"
        for i, task in enumerate(tasks)
    ]
    return "Here are your dated tasks: " + " ".join(parts)


def _priority_score(priority):
    if priority == "high":
        return 3
    if priority == "medium":
        return 2
    return 1


def get_most_urgent_task():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM tasks
        WHERE completed = 0
    """)

    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        return "You do not have any incomplete tasks."

    sorted_tasks = sorted(
        tasks,
        key=lambda t: (_priority_score(t["priority"]), 1 if t["due_date"] else 0),
        reverse=True
    )

    top = sorted_tasks[0]
    message = f"You should work on {top['task']} first because it is {top['priority']} priority"
    if top["due_date"]:
        message += f" and due {top['due_date']}"
    return message + "."


def get_daily_plan():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM tasks
        WHERE completed = 0
    """)

    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        return "You do not have any incomplete tasks for today."

    sorted_tasks = sorted(
        tasks,
        key=lambda t: (_priority_score(t["priority"]), 1 if t["due_date"] else 0),
        reverse=True
    )

    top_tasks = sorted_tasks[:3]
    parts = []

    for i, task in enumerate(top_tasks, start=1):
        line = f"{i}. {task['task']} ({task['priority']} priority"
        if task["due_date"]:
            line += f", due {task['due_date']}"
        line += ")"
        parts.append(line)

    return "Here is your plan: " + " ".join(parts)


def get_completed_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM tasks
        WHERE completed = 1
        ORDER BY id ASC
    """)

    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        return "You have not completed any tasks yet."

    parts = [f"{i+1}. {task['task']}" for i, task in enumerate(tasks)]
    return "Here are your completed tasks: " + " ".join(parts)


def get_task_counts():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM tasks")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS completed FROM tasks WHERE completed = 1")
    completed = cursor.fetchone()["completed"]

    conn.close()

    remaining = total - completed
    return f"You have {remaining} remaining tasks out of {total} total, and {completed} completed."


def get_productivity_summary():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()

    conn.close()

    if not tasks:
        return "You do not have any tasks yet."

    total = len(tasks)
    completed = len([t for t in tasks if t["completed"] == 1])
    remaining = total - completed
    high_remaining = len([
        t for t in tasks
        if t["completed"] == 0 and t["priority"] == "high"
    ])

    summary = f"You have completed {completed} out of {total} tasks, with {remaining} still remaining."

    if high_remaining > 0:
        summary += f" You still have {high_remaining} high priority tasks left."

    if completed > remaining:
        summary += " You are making solid progress."
    elif remaining > completed:
        summary += " You should focus on clearing your top priorities."
    else:
        summary += " You are fairly balanced right now."

    return summary


def get_due_soon_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM tasks
        WHERE completed = 0 AND due_date IS NOT NULL
        ORDER BY id ASC
    """)

    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        return "You do not have any tasks with due dates."

    parts = [
        f"{i+1}. {task['task']} (due {task['due_date']}, {task['priority']} priority)"
        for i, task in enumerate(tasks)
    ]
    return "Here is what is due soon: " + " ".join(parts)