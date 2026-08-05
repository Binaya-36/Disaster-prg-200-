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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shelters (district_id, name, capacity, current_occupancy)
        VALUES (?, ?, ?, ?)
    """, (district_id, name, capacity, current_occupancy))
    conn.commit()
    conn.close()


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
    cur.execute("DELETE FROM shelters WHERE shelter_id = ?", (shelter_id,))
    conn.commit()
    conn.close()
