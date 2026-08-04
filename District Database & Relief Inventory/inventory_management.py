from database import get_connection


def add_item(district_id, item_name, quantity, unit, low_stock_threshold=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO inventory (district_id, item_name, quantity, unit, low_stock_threshold)
        VALUES (?, ?, ?, ?, ?)
    """, (district_id, item_name, quantity, unit, low_stock_threshold))
    conn.commit()
    conn.close()


def get_inventory(district_id=None):
    """Used by Member 4 to check stock before allocation."""
    conn = get_connection()
    cur = conn.cursor()
    if district_id:
        cur.execute("SELECT * FROM inventory WHERE district_id = ?", (district_id,))
    else:
        cur.execute("SELECT * FROM inventory")
    rows = cur.fetchall()
    conn.close()
    return rows


def update_item(item_id, item_name, quantity, unit, low_stock_threshold):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE inventory
        SET item_name = ?, quantity = ?, unit = ?, low_stock_threshold = ?
        WHERE item_id = ?
    """, (item_name, quantity, unit, low_stock_threshold, item_id))
    conn.commit()
    conn.close()


def delete_item(item_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()


def adjust_stock(item_id, change_amount):
    """Add or subtract stock, e.g. after Member 4 allocates resources."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE inventory SET quantity = quantity + ? WHERE item_id = ?",
                (change_amount, item_id))
    conn.commit()
    conn.close()


def get_low_stock_items():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM inventory WHERE quantity <= low_stock_threshold")
    rows = cur.fetchall()
    conn.close()
    return rows
