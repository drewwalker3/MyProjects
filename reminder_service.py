from database import get_connection


def add_reminder(reminder_text):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reminders (text, done)
        VALUES (?, 0)
    """, (reminder_text,))

    conn.commit()
    conn.close()

    return f"Okay, I added a reminder for {reminder_text}."


def list_reminders():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM reminders
        WHERE done = 0
        ORDER BY id ASC
    """)

    reminders = cursor.fetchall()
    conn.close()

    if not reminders:
        return "You do not have any reminders."

    parts = [f"{i+1}. {reminder['text']}" for i, reminder in enumerate(reminders)]
    return "Here are your reminders: " + " ".join(parts)


def complete_reminder(reminder_text):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM reminders
        WHERE LOWER(text) = LOWER(?) AND done = 0
        LIMIT 1
    """, (reminder_text,))
    reminder = cursor.fetchone()

    if not reminder:
        conn.close()
        return f"I could not find a reminder for '{reminder_text}'."

    cursor.execute("""
        UPDATE reminders
        SET done = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (reminder["id"],))

    conn.commit()
    conn.close()

    return f"Okay, I marked reminder '{reminder_text}' as done."