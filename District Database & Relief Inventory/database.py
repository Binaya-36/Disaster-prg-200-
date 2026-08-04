import sqlite3

DB_NAME = "disaster_system.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # District table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS districts (
            district_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            province TEXT,
            population INTEGER,
            vulnerability_level TEXT DEFAULT 'Unknown'
        )
    """)

    # Shelter table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shelters (
            shelter_id INTEGER PRIMARY KEY AUTOINCREMENT,
            district_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            capacity INTEGER,
            current_occupancy INTEGER DEFAULT 0,
            FOREIGN KEY (district_id) REFERENCES districts (district_id)
        )
    """)

    # Inventory table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            district_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            unit TEXT,
            low_stock_threshold INTEGER DEFAULT 10,
            FOREIGN KEY (district_id) REFERENCES districts (district_id)
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database and tables created successfully.")
