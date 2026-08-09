from database import get_connection


def add_event(district_id, disaster_type, event_date, risk_level, description=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO disaster_events (district_id, disaster_type, event_date, risk_level, description)
        VALUES (?, ?, ?, ?, ?)
    """, (district_id, disaster_type, event_date, risk_level, description))
    conn.commit()
    conn.close()


def get_events(district_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if district_id:
        cur.execute("SELECT * FROM disaster_events WHERE district_id = ? ORDER BY event_date DESC", (district_id,))
    else:
        cur.execute("SELECT * FROM disaster_events ORDER BY event_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_event(event_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM disaster_events WHERE event_id = ?", (event_id,))
    conn.commit()
    conn.close()
    