from database import get_connection


# ---------- District functions ----------

def add_district(name, province, population, terrain, vulnerability_level="Unknown"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO districts (name, province, population, terrain, vulnerability_level)
        VALUES (?, ?, ?, ?, ?)
    """, (name, province, population, terrain, vulnerability_level))
    conn.commit()
    conn.close()


def get_districts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM districts")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_district_by_id(district_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM districts WHERE district_id = ?", (district_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_district(district_id, name, province, population, terrain, vulnerability_level):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE districts
        SET name = ?, province = ?, population = ?, terrain = ?, vulnerability_level = ?
        WHERE district_id = ?
    """, (name, province, population, terrain, vulnerability_level, district_id))
    conn.commit()
    conn.close()


def delete_district(district_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM districts WHERE district_id = ?", (district_id,))
    conn.commit()
    conn.close()


# ---------- Shelter functions ----------

def add_shelter(district_id, name, capacity, current_occupancy=0):
    """Returns the newly created shelter_id, so we can auto-stock it right after.

    Raises ValueError if occupancy exceeds capacity so bad data can never
    reach the database, even if a caller forgets to check in the UI layer.
    """
    if current_occupancy > capacity:
        raise ValueError(
            f"Occupancy ({current_occupancy}) cannot exceed capacity ({capacity})."
        )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shelters (district_id, name, capacity, current_occupancy)
        VALUES (?, ?, ?, ?)
    """, (district_id, name, capacity, current_occupancy))
    shelter_id = cur.lastrowid
    conn.commit()
    conn.close()
    return shelter_id


def get_shelters(district_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if district_id:
        cur.execute("SELECT * FROM shelters WHERE district_id = ?", (district_id,))
    else:
        cur.execute("SELECT * FROM shelters")
    rows = cur.fetchall()
    conn.close()
    return rows


def update_shelter(shelter_id, name, capacity, current_occupancy):
    if current_occupancy > capacity:
        raise ValueError(
            f"Occupancy ({current_occupancy}) cannot exceed capacity ({capacity})."
        )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE shelters
        SET name = ?, capacity = ?, current_occupancy = ?
        WHERE shelter_id = ?
    """, (name, capacity, current_occupancy, shelter_id))
    conn.commit()
    conn.close()


def delete_shelter(shelter_id):
    conn = get_connection()
    cur = conn.cursor()
    # Remove this shelter's inventory first (foreign key constraint)
    cur.execute("DELETE FROM inventory WHERE shelter_id = ?", (shelter_id,))
    # Now safe to delete the shelter itself
    cur.execute("DELETE FROM shelters WHERE shelter_id = ?", (shelter_id,))
    conn.commit()
    conn.close()