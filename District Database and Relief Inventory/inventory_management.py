from database import get_connection
from datetime import date
import math


# The 5 core relief items every shelter is automatically stocked with,
# expressed as a per-person ratio so the amount scales with each shelter's
# capacity instead of every shelter getting the same flat amount regardless
# of size. Figures are rough humanitarian-relief rules of thumb (e.g. water
# need per person per day) and can be tuned later.
ESSENTIAL_ITEMS = [
    {"item_name": "Rice",          "unit": "kg",     "per_person": 1.5,  "low_stock_pct": 0.2},
    {"item_name": "Water",         "unit": "liters", "per_person": 15,   "low_stock_pct": 0.2},
    {"item_name": "Medicine Kits", "unit": "kits",   "per_person": 0.1,  "low_stock_pct": 0.2},  # ~1 kit per 10 people
    {"item_name": "Blankets",      "unit": "pieces", "per_person": 1,    "low_stock_pct": 0.2},
    {"item_name": "Tents",         "unit": "units",  "per_person": 0.2,  "low_stock_pct": 0.2},   # ~1 tent per 5 people
]


def _essential_item_quantities(capacity):
    """Turns the per-person ratios above into concrete (target_qty, low_stock_threshold)
    numbers for one shelter, given that shelter's capacity. Always at least 1 unit
    of each item so a tiny shelter still gets something to work with."""
    resolved = []
    for item in ESSENTIAL_ITEMS:
        target_qty = max(1, math.ceil(item["per_person"] * capacity))
        threshold = max(1, round(target_qty * item["low_stock_pct"]))
        resolved.append({
            "item_name": item["item_name"],
            "unit": item["unit"],
            "target_qty": target_qty,
            "low_stock_threshold": threshold,
        })
    return resolved


def add_item(item_name, quantity, unit, low_stock_threshold=10,
             district_id=None, shelter_id=None, sku=None, last_restocked=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO inventory (sku, district_id, shelter_id, item_name, quantity, unit, low_stock_threshold, last_restocked)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (sku, district_id, shelter_id, item_name, quantity, unit, low_stock_threshold, last_restocked))
    conn.commit()
    conn.close()


def allocate_from_central_to_shelter(item_name, shelter_id, district_id, quantity,
                                      low_stock_threshold=10, allow_reserve_dip=True):
    """
    Moves stock from central/national inventory directly to a shelter.
    Deducts from central stock; adds to (or tops up) the shelter's item.

    allow_reserve_dip=True by default here because this function is also used
    for automatic essential-item seeding of a brand-new shelter, which should
    still partially stock the shelter even if central is low. When called from
    a manual "top up this shelter" action, pass allow_reserve_dip=False to get
    the same minimum-reserve protection as district-level allocation.

    Returns (success: bool, message: str, actual_amount_given: int).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Find the matching central item (district_id AND shelter_id both NULL)
    cur.execute("""
        SELECT item_id, quantity, unit, low_stock_threshold FROM inventory
        WHERE item_name = ? AND district_id IS NULL AND shelter_id IS NULL
    """, (item_name,))
    central_row = cur.fetchone()

    if not central_row:
        conn.close()
        return False, f"'{item_name}' not found in central inventory.", 0

    central_item_id, central_qty, unit, central_threshold = central_row

    if central_qty <= 0:
        conn.close()
        return False, f"Central stock of {item_name} is empty.", 0

    # Give only as much as central stock actually has (partial allocation if short)
    actual_amount = min(quantity, central_qty)

    if not allow_reserve_dip:
        headroom = max(central_qty - central_threshold, 0)
        if headroom <= 0:
            conn.close()
            return False, (
                f"Central {item_name} is already at or below its minimum reserve "
                f"({central_threshold} {unit}). Check 'allow reserve dip' to override."
            ), 0
        actual_amount = min(actual_amount, headroom)

    # Deduct from central
    cur.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_id = ?", (actual_amount, central_item_id))

    # Check if shelter already has this item
    cur.execute("""
        SELECT item_id FROM inventory WHERE shelter_id = ? AND item_name = ?
    """, (shelter_id, item_name))
    existing = cur.fetchone()

    today = date.today().isoformat()

    if existing:
        cur.execute("""
            UPDATE inventory SET quantity = quantity + ?, last_restocked = ?
            WHERE item_id = ?
        """, (actual_amount, today, existing[0]))
    else:
        # sku is intentionally None here -- sku belongs only to the original central record
        cur.execute("""
            INSERT INTO inventory (sku, district_id, shelter_id, item_name, quantity, unit, low_stock_threshold, last_restocked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (None, district_id, shelter_id, item_name, actual_amount, unit, low_stock_threshold, today))

    conn.commit()
    conn.close()

    if actual_amount < quantity:
        return True, f"Only {actual_amount} {unit} of {item_name} available (wanted {quantity}). Partially allocated.", actual_amount
    return True, f"Allocated {actual_amount} {unit} of {item_name} to shelter.", actual_amount


def seed_shelter_essentials(shelter_id, capacity, district_id=None):
    """
    Stocks a brand-new shelter with the 5 core relief items, sized to that
    shelter's capacity, pulling directly from (and deducting) central/national
    inventory. Returns a list of messages describing what happened for each item.
    """
    messages = []
    for item in _essential_item_quantities(capacity):
        success, message, amount = allocate_from_central_to_shelter(
            item_name=item["item_name"],
            shelter_id=shelter_id,
            district_id=district_id,
            quantity=item["target_qty"],
            low_stock_threshold=item["low_stock_threshold"]
        )
        messages.append(message)
    return messages


def get_shelter_inventory(shelter_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM inventory WHERE shelter_id = ?", (shelter_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_inventory(district_id=None):
    """
    District-level stock only (excludes items assigned to a specific shelter).
    Used by Member 4 to check stock before allocation.
    """
    conn = get_connection()
    cur = conn.cursor()
    if district_id:
        cur.execute("SELECT * FROM inventory WHERE district_id = ? AND shelter_id IS NULL", (district_id,))
    else:
        cur.execute("SELECT * FROM inventory WHERE shelter_id IS NULL")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_central_inventory():
    """Returns only national/central stock (not tied to any district or shelter)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM inventory WHERE district_id IS NULL AND shelter_id IS NULL")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_central_item(item_name, quantity, unit, low_stock_threshold=10, sku=None):
    """Add a brand new item type directly to central/national stock."""
    add_item(
        item_name=item_name,
        quantity=quantity,
        unit=unit,
        low_stock_threshold=low_stock_threshold,
        district_id=None,
        shelter_id=None,
        sku=sku,
        last_restocked=date.today().isoformat()
    )


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


def restock_item(item_id, add_amount):
    """Increase stock and refresh the last_restocked date."""
    conn = get_connection()
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute("""
        UPDATE inventory
        SET quantity = quantity + ?, last_restocked = ?
        WHERE item_id = ?
    """, (add_amount, today, item_id))
    conn.commit()
    conn.close()


def adjust_stock(item_id, change_amount):
    """Add or subtract stock, e.g. after Member 4 allocates resources. Can be negative."""
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


def allocate_from_central(central_item_id, district_id, quantity, allow_reserve_dip=False):
    """
    Moves stock from central/national inventory to a specific district.
    Deducts from central stock; adds to (or creates) the matching district-level item.

    A minimum reserve equal to the item's low_stock_threshold is protected:
    by default you cannot allocate an amount that would push central stock
    below that reserve. Pass allow_reserve_dip=True to override in a genuine
    emergency (e.g. Severe/High risk event already logged for the district).

    Returns (success: bool, message: str).
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT item_name, unit, quantity, low_stock_threshold FROM inventory WHERE item_id = ?",
        (central_item_id,)
    )
    central_row = cur.fetchone()

    if not central_row:
        conn.close()
        return False, "Central item not found."

    item_name, unit, central_qty, threshold = central_row

    if quantity <= 0:
        conn.close()
        return False, "Quantity must be greater than 0."

    if quantity > central_qty:
        conn.close()
        return False, f"Not enough central stock. Only {central_qty} {unit} of {item_name} available."

    reserve_after = central_qty - quantity
    if reserve_after < threshold and not allow_reserve_dip:
        available_above_reserve = max(central_qty - threshold, 0)
        conn.close()
        return False, (
            f"That would drop central {item_name} below its minimum reserve of {threshold} {unit}. "
            f"Only {available_above_reserve} {unit} can be allocated without dipping into reserve."
        )

    # Deduct from central stock
    cur.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_id = ?", (quantity, central_item_id))

    # Check if this district already has this item at district-level (no shelter)
    cur.execute("""
        SELECT item_id, quantity FROM inventory
        WHERE district_id = ? AND shelter_id IS NULL AND item_name = ?
    """, (district_id, item_name))
    existing = cur.fetchone()

    today = date.today().isoformat()

    if existing:
        existing_item_id, existing_qty = existing
        cur.execute("""
            UPDATE inventory SET quantity = quantity + ?, last_restocked = ?
            WHERE item_id = ?
        """, (quantity, today, existing_item_id))
    else:
        # sku is intentionally None here -- sku belongs only to the original central record
        cur.execute("""
            INSERT INTO inventory (sku, district_id, shelter_id, item_name, quantity, unit, low_stock_threshold, last_restocked)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
        """, (None, district_id, item_name, quantity, unit, 10, today))

    conn.commit()
    conn.close()
    return True, f"Allocated {quantity} {unit} of {item_name} to district. {reserve_after} {unit} remain in central reserve."
