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
            terrain TEXT,
            shelter_count INTEGER DEFAULT 0,
            flood_prone TEXT DEFAULT 'No',
            landslide_prone TEXT DEFAULT 'No',
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
    # district_id NULL + shelter_id NULL  -> central/national stock
    # district_id set + shelter_id NULL   -> district-level stock
    # shelter_id set                      -> stock physically at that shelter
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            district_id INTEGER,
            shelter_id INTEGER,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            unit TEXT,
            low_stock_threshold INTEGER DEFAULT 10,
            last_restocked TEXT,
            FOREIGN KEY (district_id) REFERENCES districts (district_id),
            FOREIGN KEY (shelter_id) REFERENCES shelters (shelter_id)
        )
    """)

    # Disaster event table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS disaster_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            district_id INTEGER NOT NULL,
            disaster_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            risk_level TEXT,
            description TEXT,
            FOREIGN KEY (district_id) REFERENCES districts (district_id)
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database and tables created successfully.")