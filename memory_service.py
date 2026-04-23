from database import get_connection


def get_memory_value(key):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM memory WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()

    return row["value"] if row else None


def remember(key, value):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO memory (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
    """, (key, value))

    conn.commit()
    conn.close()

    return f"Okay, I will remember that {key} is {value}."


def recall_all():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT key, value FROM memory ORDER BY key ASC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "I do not remember anything yet."

    parts = [f"{row['key']} is {row['value']}" for row in rows]
    return "Here is what I remember: " + "; ".join(parts) + "."


def forget(key):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT key FROM memory WHERE key = ?", (key,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return f"I do not have anything stored for {key}."

    cursor.execute("DELETE FROM memory WHERE key = ?", (key,))
    conn.commit()
    conn.close()

    return f"Okay, I forgot {key}."


def set_session_value(key, value):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO session_memory (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
    """, (key, value))

    conn.commit()
    conn.close()


def get_session_value(key):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM session_memory WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()

    return row["value"] if row else None


def get_session_summary():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT key, value FROM session_memory ORDER BY key ASC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "I do not have any active developer session context yet."

    parts = [f"{row['key']} is {row['value']}" for row in rows]
    return "Here is your current session context: " + "; ".join(parts) + "."