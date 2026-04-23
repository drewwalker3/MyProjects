import json
from database import get_connection


def save_command_history(transcript, command, reply, source="voice"):
    conn = get_connection()
    cursor = conn.cursor()

    command_text = json.dumps(command)

    cursor.execute("""
        INSERT INTO command_history (transcript, command, reply, source)
        VALUES (?, ?, ?, ?)
    """, (transcript, command_text, reply, source))

    conn.commit()
    conn.close()

def get_recent_history(limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM command_history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return rows