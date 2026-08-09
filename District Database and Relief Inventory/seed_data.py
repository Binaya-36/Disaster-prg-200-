import csv
from database import get_connection, create_tables


def derive_vulnerability(flood_prone, landslide_prone):
    """Simple starting-point logic; Member 2 can refine this later with weather data."""
    if flood_prone == "Yes" and landslide_prone == "Yes":
        return "High"
    elif flood_prone == "Yes" or landslide_prone == "Yes":
        return "Moderate"
    else:
        return "Low"


def seed_districts_from_csv(csv_path="district_information.csv"):
    create_tables()

    conn = get_connection()
    cur = conn.cursor()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0

        for row in reader:
            name = row["District"]
            province = row["Province"]
            terrain = row["Terrain"]
            population = int(row["Population"])
            shelter_count = int(row["Shelters"])
            flood_prone = row["Flood_Prone"]
            landslide_prone = row["Landslide_Prone"]
            vulnerability = derive_vulnerability(flood_prone, landslide_prone)

            cur.execute("""
                INSERT OR IGNORE INTO districts
                (name, province, population, terrain, shelter_count, flood_prone, landslide_prone, vulnerability_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, province, population, terrain, shelter_count, flood_prone, landslide_prone, vulnerability))

            count += 1

    conn.commit()
    conn.close()
    print(f"Seeded {count} districts from {csv_path}")


def seed_districts(csv_path="district_information.csv"):
    """Alias so app.py can call seed_data.seed_districts() directly."""
    seed_districts_from_csv(csv_path)


def seed_inventory_from_csv(csv_path="relief_inventory.csv"):
    create_tables()

    conn = get_connection()
    cur = conn.cursor()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0

        for row in reader:
            sku = row["Item_ID"]
            item_name = row["Item"]
            unit = row["Unit"]
            quantity = int(row["Current_Quantity"])
            threshold = int(row["Minimum_Stock"])
            last_restocked = row["Last_Restocked"]

            cur.execute("""
                INSERT OR IGNORE INTO inventory
                (sku, district_id, shelter_id, item_name, quantity, unit, low_stock_threshold, last_restocked)
                VALUES (?, NULL, NULL, ?, ?, ?, ?, ?)
            """, (sku, item_name, quantity, unit, threshold, last_restocked))

            count += 1

    conn.commit()
    conn.close()
    print(f"Seeded {count} central inventory items from {csv_path}")


def seed_inventory(csv_path="relief_inventory.csv"):
    """Alias so app.py can call seed_data.seed_inventory() directly."""
    seed_inventory_from_csv(csv_path)


if __name__ == "__main__":
    seed_districts_from_csv("district_information.csv")
    seed_inventory_from_csv("relief_inventory.csv")
    