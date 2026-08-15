import math
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(APP_DIR)

CANDIDATE_PARENTS = [APP_DIR, REPO_ROOT]

for sibling_folder in ("Risk Engine", "weather"):
    for parent in CANDIDATE_PARENTS:
        sibling_path = os.path.join(parent, sibling_folder)
        if os.path.isdir(sibling_path) and sibling_path not in sys.path:
            sys.path.insert(0, sibling_path)
            break

from dotenv import load_dotenv
for candidate_dir in (APP_DIR, REPO_ROOT, os.path.join(APP_DIR, "weather")):
    candidate_env = os.path.join(candidate_dir, ".env")
    if os.path.isfile(candidate_env):
        load_dotenv(candidate_env, override=False)

# Imports all code
from database import get_connection, create_tables
from district_management import (
    get_districts, add_district, update_district, delete_district,
    get_shelters, add_shelter, update_shelter, delete_shelter,
)
from inventory_management import (
    get_central_inventory, add_central_item, restock_item, update_item, delete_item,
    get_low_stock_items, allocate_from_central, allocate_from_central_to_shelter,
    seed_shelter_essentials, get_shelter_inventory,
)
from disaster_events import get_events, add_event, delete_event
import seed_data  # imported as a module 
try:
    import risk_engine as risk
    RISK_ENGINE_AVAILABLE = True
except ImportError as e:
    RISK_ENGINE_AVAILABLE = False
    RISK_ENGINE_IMPORT_ERROR = str(e)

try:
    import weather_api  # module reference kept so we can set weather_api.API_KEY at runtime
    from weather_api import get_weather
    from weather_db import save_weather_reading, get_weather_history
    WEATHER_AVAILABLE = True
except ImportError as e:
    WEATHER_AVAILABLE = False
    WEATHER_IMPORT_ERROR = str(e)

# Setup
st.set_page_config(
    page_title="Smart Disaster Prediction & Relief Management System",
    page_icon="🚨",
    layout="wide",
)

create_tables()

DISTRICT_CSV = os.path.join(APP_DIR, "district_information.csv")
INVENTORY_CSV = os.path.join(APP_DIR, "relief_inventory.csv")

DISTRICT_COLS = ["ID", "Name", "Province", "Population", "Terrain",
                  "Shelter Count (CSV)", "Flood Prone", "Landslide Prone", "Vulnerability"]
INV_COLS = ["Item ID", "SKU", "District ID", "Shelter ID", "Item", "Quantity", "Unit", "Low Stock Threshold", "Last Restocked"]


def _districts_table_is_empty():
    """Just a COUNT(*) against the existing districts table -- doesn't touch database.py."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM districts")
    count = cur.fetchone()[0]
    conn.close()
    return count == 0


def try_auto_seed():

    if not _districts_table_is_empty():
        return

    try:
        with st.spinner("Seeding database from CSV files..."):
            n_districts = seed_data.seed_districts(DISTRICT_CSV)
            n_items = seed_data.seed_inventory(INVENTORY_CSV)
        st.toast(f"Seeded {n_districts} districts and {n_items} inventory items.", icon="✅")
    except Exception as e:
        st.info(
            f"Auto-seeding from seed_data.py was skipped ({type(e).__name__}: {e}). "
            "This means seed_data.py expects CSV columns the real CSV files don't have -- "
            "that's a mismatch to flag with whoever owns seed_data.py. In the meantime you "
            "can add districts, shelters, and inventory manually from their pages below."
        )


try_auto_seed()


def ensure_weather_api_key():
    """
    weather_api.py already reads WEATHER_API_KEY from .env correctly (that's
    the right, secure approach -- never hardcode a key in source that's on a
    public repo). This is only a *fallback* for when no .env is found: it
    lets whoever is running the app (you, a teammate, your professor) paste a
    key in for just this session. It's never written to disk and never
    touches weather_api.py's source -- it just overrides the module-level
    variable that file already exposes, the same way any Python code can.
    Returns True if a usable key is available one way or another.
    """
    if weather_api.API_KEY:
        return True

    if "manual_weather_api_key" in st.session_state and st.session_state["manual_weather_api_key"]:
        weather_api.API_KEY = st.session_state["manual_weather_api_key"]
        return True

    st.warning(
        "No WEATHER_API_KEY found (no .env file, or it wasn't picked up). Any weather "
        "lookup will fail with a misleading 'City not found' message until a key is set. "
        "Preferred fix: create a `.env` file next to app.py containing "
        "`WEATHER_API_KEY=your_key_here`. As a fallback for this session only, you can "
        "paste a key below instead -- it is kept in memory only, never saved to disk."
    )
    manual_key = st.text_input("OpenWeatherMap API key (session only)", type="password", key="manual_weather_api_key_input")
    if manual_key:
        st.session_state["manual_weather_api_key"] = manual_key
        weather_api.API_KEY = manual_key
        st.rerun()
    return False


# Home
def page_home():
    st.title("🚨 Smart Disaster Prediction & Relief Management System")
    st.caption(
        "One dashboard combining weather-based risk prediction, district & shelter "
        "records, relief inventory, and relief-requirement planning."
    )
    st.divider()

    districts = get_districts()
    shelters = get_shelters()
    central_items = get_central_inventory()
    low_stock = get_low_stock_items()
    events = get_events()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Districts Tracked", len(districts))
    col2.metric("Registered Shelters", len(shelters))
    col3.metric("Central Inventory Items", len(central_items))
    col4.metric("Active Disaster Events", len(events))

    if low_stock:
        st.warning(f"⚠️ {len(low_stock)} inventory item(s) are at or below their low-stock threshold. See the Inventory page.")
    else:
        st.success("✅ No inventory items are currently low on stock.")

    if not RISK_ENGINE_AVAILABLE:
        st.error(f"risk_engine.py could not be imported ({RISK_ENGINE_IMPORT_ERROR}). "
                  "Check that the 'Risk Engine' folder is where app.py expects it.")
    if not WEATHER_AVAILABLE:
        st.error(f"weather_api.py / weather_db.py could not be imported ({WEATHER_IMPORT_ERROR}). "
                  "Check that the 'weather' folder is where app.py expects it.")
    elif not weather_api.API_KEY:
        st.info("⚠️ No weather API key configured yet -- see the Weather & Risk page.")

    st.divider()
    st.subheader("Where to go")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.info("**🌦️ Weather & Risk**\n\nFetch live weather for a district and run it through the risk engine.")
    c2.info("**🏘️ Districts & Shelters**\n\nManage district records and shelters, with auto-stocking of essentials.")
    c3.info("**📦 Inventory**\n\nCentral stock, restocking, and allocation to districts or shelters.")
    c4.info("**🧺 Relief Planning**\n\nCalculate relief requirements for an affected population and compare to stock.")
    c5.info("**📋 Disaster Events**\n\nSee every event the risk engine has logged, filterable by district.")
    st.caption("Use the sidebar to switch pages.")


# Weather and risk
def page_weather_risk():
    st.title("🌦️ Weather-Based Disaster Risk")

    if not RISK_ENGINE_AVAILABLE:
        st.error(f"risk_engine.py could not be imported ({RISK_ENGINE_IMPORT_ERROR}).")
        return
    if not WEATHER_AVAILABLE:
        st.error(f"weather_api.py / weather_db.py could not be imported ({WEATHER_IMPORT_ERROR}).")
        return

    st.caption("Fetches weather (live from the API, or entered manually), then runs it through "
               "the rule-based risk engine (flood / landslide / storm / heatwave).")

    known_districts = risk.list_known_districts()

    city = st.selectbox(
        "District / City",
        options=known_districts,
        index=known_districts.index("Kathmandu") if "Kathmandu" in known_districts else 0,
        help="Pick a known district for an accurate terrain-based landslide check, "
             "or type a new one below if it's not listed.",
    )
    custom_city = st.text_input("...or type a different district/city name (overrides the dropdown)", "")
    if custom_city.strip():
        city = custom_city.strip()

    source = st.radio(
        "Weather data source",
        ["Live API lookup", "Enter weather manually"],
        horizontal=True,
        help="Manual entry runs the risk engine on values you type in directly -- no API key needed.",
    )

    weather_data = None
    weather_query_name = city
    manual_rainfall_24h = None
    use_manual_rainfall_24h = False

    if source == "Live API lookup":
        key_ready = ensure_weather_api_key()

        col_input, col_options = st.columns([2, 1])
        with col_input:
            # Many Nepali district names (e.g. "Jhapa") aren't themselves recognized
            # by the weather API -- it only knows actual city/town names, and a
            # district's main town often has a different name. This lets the
            # weather lookup use the right town while the risk engine still gets
            # the correct terrain for the district selected above.
            weather_query_override = st.text_input(
                "Actual city/town name for weather lookup (only if the name above isn't found)",
                "",
                help="E.g. district 'Jhapa' → try 'Birtamod' or 'Chandragadhi' here. "
                     "Leave blank to just query the name above directly.",
            )
            weather_query_name = weather_query_override.strip() or city

        with col_options:
            use_manual_rainfall_24h = st.checkbox(
                "Enter 24h rainfall manually",
                help="The weather API only gives a 1-hour rainfall reading, but the flood/landslide "
                     "rules are calibrated for 24-hour totals. Check this to enter a real 24h figure.",
            )
            if use_manual_rainfall_24h:
                manual_rainfall_24h = st.number_input("24-hour rainfall total (mm)", min_value=0.0, max_value=2000.0, value=0.0, step=1.0)

        fetch = st.button("Get Weather & Assess Risk", type="primary", disabled=not key_ready)
        if not key_ready:
            st.caption("Button disabled until an API key is entered above.")

        if fetch:
            with st.spinner(f"Fetching weather for {weather_query_name}..."):
                api_result = get_weather(weather_query_name)

            if "error" in api_result:
                st.error(api_result["error"])
                st.caption(
                    "Note: this same message covers three different causes -- an unknown city/town "
                    f"name, an invalid API key, or a key that hasn't activated yet. If '{weather_query_name}' "
                    "isn't a real city/town, try the 'actual city/town name' field above (e.g. a "
                    "district's main town). If it IS a real place, double check the API key above is "
                    "correct and active (new OpenWeatherMap keys can take a little while to activate "
                    "after signup). Or switch to 'Enter weather manually' above to test the risk "
                    "engine without needing the API at all."
                )
            else:
                weather_data = api_result

    else:  # Enter weather manually
        st.info("Type in conditions directly -- this skips the weather API entirely, so no key is needed.")

        c1, c2, c3 = st.columns(3)
        temperature = c1.number_input("Temperature (°C)", value=25.0, step=0.5)
        humidity = c2.number_input("Humidity (%)", min_value=0, max_value=100, value=60, step=1)
        wind_speed = c3.number_input("Wind Speed (m/s)", min_value=0.0, value=3.0, step=0.5)

        c4, c5, c6 = st.columns(3)
        rainfall_1h = c4.number_input("Rainfall - last 1 hour (mm)", min_value=0.0, value=0.0, step=1.0)
        rainfall_24h = c5.number_input(
            "Rainfall - last 24 hours (mm)", min_value=0.0, value=0.0, step=1.0,
            help="This is the figure that actually drives the flood/landslide checks.",
        )
        pressure = c6.number_input("Pressure (hPa)", min_value=800, max_value=1100, value=1010, step=1)

        description = st.text_input("Conditions description (optional, for your own notes)", "manually entered")

        assess = st.button("Assess Risk", type="primary")
        if assess:
            weather_data = {
                "city": city,
                "temperature": temperature,
                "feels_like": temperature,
                "humidity": humidity,
                "pressure": pressure,
                "wind_speed": wind_speed,
                "rainfall": rainfall_1h,
                "description": description,
                "icon": None,  # no real icon for manual entries
            }
            manual_rainfall_24h = rainfall_24h
            use_manual_rainfall_24h = True
            weather_query_name = city

    if weather_data is not None:
        save_weather_reading(weather_data)

        if weather_data.get("icon"):
            icon_url = f"https://openweathermap.org/img/wn/{weather_data['icon']}@2x.png"
            wcol1, wcol2 = st.columns([1, 3])
            with wcol1:
                st.image(icon_url)
            with wcol2:
                st.subheader(f"Weather in {weather_data['city']}")
                st.write(f"☁️ {weather_data['description'].title()}")
        else:
            st.subheader(f"Weather in {weather_data['city']} (manually entered)")

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Temperature", f"{weather_data['temperature']}°C")
        m2.metric("Feels Like", f"{weather_data['feels_like']}°C")
        m3.metric("Humidity", f"{weather_data['humidity']}%")
        m4.metric("Wind Speed", f"{weather_data['wind_speed']} m/s")
        m5.metric("Rainfall (1h)", f"{weather_data['rainfall']} mm")
        m6.metric("Pressure", f"{weather_data['pressure']} hPa")
        st.caption(f"Last updated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")

        st.divider()
        st.subheader("🚨 Risk Assessment")

        # Terrain is looked up from the DISTRICT selected above (not from
        # whatever town name the weather API happened to resolve to), and
        # passed explicitly -- risk_engine.py supports this via its own
        # terrain= parameter, so weather can come from a nearby town's (or a
        # manually entered) reading while the risk assessment still reflects
        # the right district.
        district_terrain, _ = risk.get_terrain(city)
        result = risk.predict_from_weather_api(
            weather_data,
            wind_unit="m/s",
            rainfall_mm_24h=manual_rainfall_24h if use_manual_rainfall_24h else None,
            terrain=district_terrain,
        )

        if "error" in result:
            st.error(f"Risk engine could not assess this reading: {result['error']}")
        else:
            level_color = {"Low": "🟢", "Moderate": "🟡", "High": "🟠", "Severe": "🔴"}
            r1, r2, r3 = st.columns(3)
            r1.metric("Overall Risk Level", f"{level_color.get(result['risk_level'], '')} {result['risk_level']}")
            r2.metric("Risk Score", f"{result['risk_score']} / 100")
            r3.metric("Primary Hazard", result["disaster_type"])

            for warning in result.get("warnings", []):
                st.info(f"ℹ️ {warning}")

            if result["all_hazards"]:
                st.markdown("**Hazard breakdown**")
                hazard_df = pd.DataFrame(result["all_hazards"])[["disaster_type", "risk_score", "risk_level", "reason"]]
                hazard_df.columns = ["Hazard", "Score", "Level", "Reason"]
                st.dataframe(hazard_df, use_container_width=True, hide_index=True)
            else:
                st.success("No hazard thresholds were exceeded by this reading.")

            with st.expander("Recommended actions"):
                for line in result["recommendations"]:
                    st.markdown(f"- {line}")

            if result["event_triggered"]:
                st.warning(f"🔔 This reading triggered a **{result['risk_level']}** event and has been logged.")

                existing = {d[1]: d[0] for d in get_districts()}
                district_name = city
                if district_name not in existing:
                    add_district(district_name, province="Unknown", population=0, terrain=result["terrain"])
                    existing = {d[1]: d[0] for d in get_districts()}

                district_id = existing[district_name]
                add_event(
                    district_id=district_id,
                    disaster_type=result["disaster_type"],
                    event_date=result["event"]["event_date"],
                    risk_level=result["risk_level"],
                    description=result["reason"],
                )

    st.divider()

    st.subheader(f"Recent Weather History for {weather_query_name}")
    history = get_weather_history(city=weather_query_name, limit=10)
    if history:
        df = pd.DataFrame(history, columns=[
            "ID", "City", "Timestamp", "Temp (°C)", "Feels Like (°C)",
            "Humidity (%)", "Pressure (hPa)", "Wind Speed (m/s)",
            "Rainfall (mm)", "Description", "Icon",
        ])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"]).dt.strftime("%d-%m-%Y %H:%M")
        df["Description"] = df["Description"].str.title()
        display_df = df[["Timestamp", "Temp (°C)", "Feels Like (°C)", "Humidity (%)",
                          "Rainfall (mm)", "Wind Speed (m/s)", "Pressure (hPa)", "Description"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No history yet for this city. Fetch or assess weather above to start logging.")


# Districts and shelters
def page_districts_shelters():
    st.title("🏘️ Districts & Shelters")

    tab_districts, tab_shelters = st.tabs(["Districts", "Shelters"])

    with tab_districts:
        districts = get_districts()
        if districts:
            df = pd.DataFrame(districts, columns=DISTRICT_COLS)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No districts yet.")

        with st.expander("➕ Add a district"):
            with st.form("add_district_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                name = c1.text_input("Name")
                province = c2.text_input("Province")
                c3, c4 = st.columns(2)
                population = c3.number_input("Population", min_value=0, step=1)
                terrain = c4.selectbox("Terrain", ["mountain", "hill", "valley", "terai"])
                vulnerability = st.selectbox("Vulnerability Level", ["Low", "Moderate", "High", "Unknown"])
                if st.form_submit_button("Add District", type="primary"):
                    if not name.strip():
                        st.error("Name is required.")
                    else:
                        add_district(name.strip(), province.strip(), int(population), terrain, vulnerability)
                        st.success(f"Added {name}.")
                        st.rerun()

        if districts:
            with st.expander("✏️ Edit or delete a district"):
                names = {f"{d[1]} (ID {d[0]})": d for d in districts}
                choice = st.selectbox("Select district", list(names.keys()), key="edit_district_select")
                d = names[choice]
                with st.form("edit_district_form"):
                    c1, c2 = st.columns(2)
                    e_name = c1.text_input("Name", value=d[1])
                    e_province = c2.text_input("Province", value=d[2] or "")
                    c3, c4 = st.columns(2)
                    e_population = c3.number_input("Population", min_value=0, step=1, value=d[3] or 0)
                    terrain_options = ["mountain", "hill", "valley", "terai"]
                    e_terrain = c4.selectbox("Terrain", terrain_options,
                                              index=terrain_options.index(d[4]) if d[4] in terrain_options else 0)
                    vuln_options = ["Low", "Moderate", "High", "Unknown"]
                    e_vulnerability = st.selectbox("Vulnerability Level", vuln_options,
                                                    index=vuln_options.index(d[8]) if d[8] in vuln_options else 3)
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("Save Changes", type="primary"):
                        update_district(d[0], e_name.strip(), e_province.strip(), int(e_population), e_terrain, e_vulnerability)
                        st.success("Updated.")
                        st.rerun()
                    if b2.form_submit_button("🗑️ Delete District"):
                        delete_district(d[0])
                        st.warning(f"Deleted {d[1]}.")
                        st.rerun()

    with tab_shelters:
        districts = get_districts()
        if not districts:
            st.info("Add a district first before creating shelters.")
        else:
            district_names = {f"{d[1]} (ID {d[0]})": d[0] for d in districts}
            selected_label = st.selectbox("Filter by district", ["All districts"] + list(district_names.keys()))
            selected_district_id = None if selected_label == "All districts" else district_names[selected_label]

            shelters = get_shelters(selected_district_id)
            if shelters:
                shelter_df = pd.DataFrame(shelters, columns=["ID", "District ID", "Name", "Capacity", "Current Occupancy"])
                shelter_df["Occupancy %"] = (shelter_df["Current Occupancy"] / shelter_df["Capacity"].replace(0, pd.NA) * 100).round(1)
                st.dataframe(shelter_df, use_container_width=True, hide_index=True)
            else:
                st.info("No shelters found for this filter.")

            with st.expander("➕ Add a shelter (auto-stocks with essential relief items)"):
                with st.form("add_shelter_form", clear_on_submit=True):
                    target_district_label = st.selectbox("District", list(district_names.keys()), key="new_shelter_district")
                    target_district_id = district_names[target_district_label]
                    s_name = st.text_input("Shelter Name")
                    c1, c2 = st.columns(2)
                    s_capacity = c1.number_input("Capacity", min_value=1, step=1, value=100)
                    s_occupancy = c2.number_input("Current Occupancy", min_value=0, step=1, value=0)
                    if st.form_submit_button("Add Shelter", type="primary"):
                        if not s_name.strip():
                            st.error("Shelter name is required.")
                        elif s_occupancy > s_capacity:
                            st.error("Occupancy cannot exceed capacity.")
                        else:
                            new_shelter_id = add_shelter(target_district_id, s_name.strip(), int(s_capacity), int(s_occupancy))
                            messages = seed_shelter_essentials(new_shelter_id, int(s_capacity), target_district_id)
                            st.success(f"Added shelter '{s_name}' and stocked it from central inventory.")
                            for m in messages:
                                st.caption(f"• {m}")
                            st.rerun()

            if shelters:
                with st.expander("✏️ Edit / delete a shelter, or view its stock"):
                    shelter_names = {f"{s[2]} (ID {s[0]})": s for s in shelters}
                    s_choice = st.selectbox("Select shelter", list(shelter_names.keys()))
                    s = shelter_names[s_choice]

                    with st.form("edit_shelter_form"):
                        es_name = st.text_input("Name", value=s[2])
                        c1, c2 = st.columns(2)
                        es_capacity = c1.number_input("Capacity", min_value=1, step=1, value=s[3])
                        es_occupancy = c2.number_input("Current Occupancy", min_value=0, step=1, value=s[4])
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("Save Changes", type="primary"):
                            if es_occupancy > es_capacity:
                                st.error("Occupancy cannot exceed capacity.")
                            else:
                                update_shelter(s[0], es_name.strip(), int(es_capacity), int(es_occupancy))
                                st.success("Updated.")
                                st.rerun()
                        if b2.form_submit_button("🗑️ Delete Shelter"):
                            delete_shelter(s[0])
                            st.warning(f"Deleted {s[2]}.")
                            st.rerun()

                    st.markdown("**Current stock at this shelter**")
                    stock = get_shelter_inventory(s[0])
                    if stock:
                        stock_df = pd.DataFrame(stock, columns=["Item ID", "SKU", "District ID", "Shelter ID",
                                                                  "Item", "Quantity", "Unit", "Low Stock Threshold", "Last Restocked"])
                        st.dataframe(stock_df[["Item", "Quantity", "Unit", "Low Stock Threshold", "Last Restocked"]],
                                     use_container_width=True, hide_index=True)
                    else:
                        st.caption("No stock recorded for this shelter yet.")


# Inventory
def page_inventory():
    st.title("📦 Relief Inventory")

    tab_central, tab_allocate, tab_low = st.tabs(["Central Stock", "Allocate", "Low Stock Alerts"])

    with tab_central:
        items = get_central_inventory()
        if items:
            df = pd.DataFrame(items, columns=INV_COLS)
            st.dataframe(df[["SKU", "Item", "Quantity", "Unit", "Low Stock Threshold", "Last Restocked"]],
                         use_container_width=True, hide_index=True)
        else:
            st.info("No central inventory yet.")

        with st.expander("➕ Add a new central item"):
            with st.form("add_item_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                i_name = c1.text_input("Item Name")
                i_unit = c2.text_input("Unit", value="units")
                c3, c4 = st.columns(2)
                i_qty = c3.number_input("Starting Quantity", min_value=0, step=1)
                i_threshold = c4.number_input("Low Stock Threshold", min_value=0, step=1, value=10)
                i_sku = st.text_input("SKU (optional, auto-generated if left blank)")
                if st.form_submit_button("Add Item", type="primary"):
                    if not i_name.strip():
                        st.error("Item name is required.")
                    else:
                        sku = i_sku.strip() or None
                        add_central_item(i_name.strip(), int(i_qty), i_unit.strip(), int(i_threshold), sku)
                        st.success(f"Added {i_name} to central inventory.")
                        st.rerun()

        if items:
            with st.expander("✏️ Restock / edit / delete an item"):
                item_names = {f"{it[4]} ({it[1] or 'no SKU'})": it for it in items}
                choice = st.selectbox("Select item", list(item_names.keys()))
                it = item_names[choice]

                r1, r2 = st.columns(2)
                with r1:
                    st.markdown("**Restock**")
                    add_amount = st.number_input("Amount to add", min_value=0, step=1, key="restock_amount")
                    if st.button("Restock", type="primary"):
                        restock_item(it[0], int(add_amount))
                        st.success(f"Added {add_amount} {it[6]} to {it[4]}.")
                        st.rerun()

                with r2:
                    st.markdown("**Edit details**")
                    with st.form("edit_item_form"):
                        e_name = st.text_input("Item Name", value=it[4])
                        e_qty = st.number_input("Quantity", min_value=0, step=1, value=it[5])
                        e_unit = st.text_input("Unit", value=it[6])
                        e_threshold = st.number_input("Low Stock Threshold", min_value=0, step=1, value=it[7])
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("Save"):
                            update_item(it[0], e_name.strip(), int(e_qty), e_unit.strip(), int(e_threshold))
                            st.success("Updated.")
                            st.rerun()
                        if b2.form_submit_button("🗑️ Delete"):
                            delete_item(it[0])
                            st.warning(f"Deleted {it[4]}.")
                            st.rerun()

    with tab_allocate:
        st.caption("Move stock from central/national reserve to a district or directly to a shelter.")
        items = get_central_inventory()
        districts = get_districts()

        if not items:
            st.info("No central inventory to allocate from yet.")
        elif not districts:
            st.info("Add a district first.")
        else:
            target_type = st.radio("Allocate to", ["District", "Shelter"], horizontal=True)
            item_names = {f"{it[4]} — {it[5]} {it[6]} available": it for it in items}
            item_choice = st.selectbox("Item", list(item_names.keys()))
            chosen_item = item_names[item_choice]

            district_names = {f"{d[1]} (ID {d[0]})": d[0] for d in districts}

            if target_type == "District":
                dist_choice = st.selectbox("District", list(district_names.keys()))
                qty = st.number_input("Quantity to allocate", min_value=1, step=1)
                allow_dip = st.checkbox("Allow dipping into minimum reserve (emergency override)")
                if st.button("Allocate to District", type="primary"):
                    success, message = allocate_from_central(chosen_item[0], district_names[dist_choice], int(qty), allow_dip)
                    (st.success if success else st.error)(message)
                    if success:
                        st.rerun()
            else:
                dist_choice = st.selectbox("District (for the shelter's location)", list(district_names.keys()))
                shelters = get_shelters(district_names[dist_choice])
                if not shelters:
                    st.info("This district has no shelters yet.")
                else:
                    shelter_names = {f"{s[2]} (ID {s[0]})": s[0] for s in shelters}
                    shelter_choice = st.selectbox("Shelter", list(shelter_names.keys()))
                    qty = st.number_input("Quantity to allocate", min_value=1, step=1)
                    allow_dip = st.checkbox("Allow dipping into minimum reserve (emergency override)", key="shelter_dip")
                    if st.button("Allocate to Shelter", type="primary"):
                        success, message, amount = allocate_from_central_to_shelter(
                            item_name=chosen_item[4],
                            shelter_id=shelter_names[shelter_choice],
                            district_id=district_names[dist_choice],
                            quantity=int(qty),
                            allow_reserve_dip=allow_dip,
                        )
                        (st.success if success else st.error)(message)
                        if success:
                            st.rerun()

    with tab_low:
        low_items = get_low_stock_items()
        if low_items:
            st.warning(f"{len(low_items)} item(s) are at or below their low-stock threshold.")
            df = pd.DataFrame(low_items, columns=INV_COLS)
            st.dataframe(df[["SKU", "Item", "Quantity", "Unit", "Low Stock Threshold", "Last Restocked"]],
                         use_container_width=True, hide_index=True)
        else:
            st.success("Nothing is currently low on stock, anywhere in the system.")


# Relief planning
MEALS_PER_PERSON = 2
WATER_LITERS_PER_PERSON = 3
PEOPLE_PER_MEDICINE_KIT = 25
KG_RICE_PER_MEAL_PACK = 0.25


@st.cache_data
def load_district_csv():
    return pd.read_csv(DISTRICT_CSV)


@st.cache_data
def load_inventory_csv():
    return pd.read_csv(INVENTORY_CSV)


def calculate_aid_needed(population):
    meal_packs_needed = population * MEALS_PER_PERSON
    rice_kg_needed = meal_packs_needed * KG_RICE_PER_MEAL_PACK
    water_liters_needed = population * WATER_LITERS_PER_PERSON
    medicine_kits_needed = math.ceil(population / PEOPLE_PER_MEDICINE_KIT)
    return {
        "Food (meal packs)": meal_packs_needed,
        "Food (rice kg equivalent)": rice_kg_needed,
        "Water (litres)": water_liters_needed,
        "Medicine (kits)": medicine_kits_needed,
    }


def get_stock_csv(inventory_df, item_name):
    row = inventory_df[inventory_df["Item"] == item_name]
    return 0.0 if row.empty else float(row["Current_Quantity"].iloc[0])


def build_allocation_report(aid_needed, inventory_df):
    rows = [
        {"Category": "Food", "Inventory Item": "Rice", "Unit": "kg",
         "Needed": round(aid_needed["Food (rice kg equivalent)"], 1), "Available": get_stock_csv(inventory_df, "Rice")},
        {"Category": "Water", "Inventory Item": "Water", "Unit": "liters",
         "Needed": round(aid_needed["Water (litres)"], 1), "Available": get_stock_csv(inventory_df, "Water")},
        {"Category": "Medicine", "Inventory Item": "Medicine Kits", "Unit": "kits",
         "Needed": aid_needed["Medicine (kits)"], "Available": get_stock_csv(inventory_df, "Medicine Kits")},
    ]
    report = pd.DataFrame(rows)
    report["Allocated"] = report[["Needed", "Available"]].min(axis=1)
    report["Shortage"] = (report["Needed"] - report["Available"]).clip(lower=0)
    report["Surplus"] = (report["Available"] - report["Needed"]).clip(lower=0)
    report["Coverage %"] = (report["Allocated"] / report["Needed"] * 100).round(1)
    report["Stock Used %"] = (report["Allocated"] / report["Available"].replace(0, float("nan")) * 100).round(1).fillna(0)
    report["Status"] = report["Shortage"].apply(lambda v: "⚠️ SHORTAGE" if v > 0 else "✅ SUFFICIENT")
    report["Priority"] = report.apply(lambda row: get_priority(row["Shortage"], row["Needed"]), axis=1)
    return report


def get_priority(shortage, needed):
    if shortage <= 0:
        return "🟢 Covered"
    pct = shortage / needed * 100
    if pct > 50:
        return "🔴 Critical"
    if pct > 20:
        return "🟠 Moderate"
    return "🟡 Minor"


def build_reallocation_report(district_df, affected_percent):
    rows = []
    for _, row in district_df.iterrows():
        population = int(row["Population"])
        people_affected = round(population * affected_percent / 100)
        aid = calculate_aid_needed(people_affected)
        rows.append({
            "District": row["District"],
            "Population": population,
            "People Affected": people_affected,
            "Rice Needed (kg)": round(aid["Food (rice kg equivalent)"], 1),
            "Water Needed (L)": aid["Water (litres)"],
            "Medicine Kits Needed": aid["Medicine (kits)"],
        })
    result = pd.DataFrame(rows)
    return result.sort_values("People Affected", ascending=False).reset_index(drop=True)


def page_relief_planning():
    st.title("🧺 Relief Requirements & Allocation")
    st.caption("Calculate relief requirements from an affected population and compare against current stock levels.")

    district_df = load_district_csv()
    inventory_df = load_inventory_csv()

    tab1, tab2 = st.tabs(["1️⃣ Requirements & Allocation", "2️⃣ Final Allocation & Shortage Analysis"])

    with tab1:
        st.subheader("1. Select Affected District")
        district_names = sorted(district_df["District"].dropna().unique())
        district_name = st.selectbox("District", district_names)
        district_row = district_df[district_df["District"] == district_name].iloc[0]
        population = int(district_row["Population"])

        c1, c2, c3 = st.columns(3)
        c1.metric("District Population", f"{population:,}")
        c2.metric("Province", district_row["Province"])
        c3.metric("Shelters", f"{int(district_row['Shelters']):,}")

        st.subheader("2. Determine Affected Population")
        affected_percent = st.slider("Percentage of district population affected", 1, 100, 50, 1, format="%d%%")
        people_affected = round(population * affected_percent / 100)
        st.info(f"**{people_affected:,} people** are affected ({affected_percent}% of the district population).")

        st.subheader("3. Relief Required")
        aid_needed = calculate_aid_needed(people_affected)
        c1, c2, c3 = st.columns(3)
        c1.metric("Food", f"{aid_needed['Food (meal packs)']:,} meal packs")
        c2.metric("Water", f"{aid_needed['Water (litres)']:,} litres")
        c3.metric("Medicine", f"{aid_needed['Medicine (kits)']:,} kits")

        with st.expander("View calculation rules"):
            st.markdown(f"""
            - **Food:** {MEALS_PER_PERSON} meal packs per person
            - **Water:** {WATER_LITERS_PER_PERSON} litres per person
            - **Medicine:** 1 kit per {PEOPLE_PER_MEDICINE_KIT} people, rounded up
            - **Food inventory comparison:** 1 meal pack ≈ {KG_RICE_PER_MEAL_PACK} kg rice
            """)

        st.subheader("4. Available Inventory & Allocation")
        report = build_allocation_report(aid_needed, inventory_df)
        display_report = report[["Category", "Inventory Item", "Unit", "Needed", "Available",
                                  "Allocated", "Shortage", "Surplus", "Coverage %", "Status"]]
        st.dataframe(display_report, use_container_width=True, hide_index=True)

        shortage_count = int((report["Shortage"] > 0).sum())
        total_shortage = report["Shortage"].sum()
        if shortage_count == 0:
            st.success("All calculated relief requirements can be covered by the current inventory.")
        else:
            st.warning(f"{shortage_count} item(s) have a shortage. Total shortage: {total_shortage:,.1f} units.")

        st.subheader("5. Allocation Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Required", f"{report['Needed'].sum():,.1f}")
        c2.metric("Total Allocated", f"{report['Allocated'].sum():,.1f}")
        c3.metric("Total Shortage", f"{report['Shortage'].sum():,.1f}")
        c4.metric("Total Surplus", f"{report['Surplus'].sum():,.1f}")

        if st.button("Update Final Analysis", type="primary"):
            st.session_state["rp_selected_district"] = district_name
            st.session_state["rp_affected_percent"] = affected_percent
            st.session_state["rp_people_affected"] = people_affected
            st.session_state["rp_allocation_report"] = report
            st.success("Final allocation analysis updated. Open the 'Final Allocation & Shortage Analysis' tab.")

        st.caption("The final analysis tab uses the current slider value at the time you click the button above.")

    with tab2:
        report = st.session_state.get("rp_allocation_report")

        if report is None:
            st.info("No allocation has been calculated yet. Go to tab 1, select a district, adjust the slider, "
                    "and click 'Update Final Analysis'.")
        else:
            district = st.session_state["rp_selected_district"]
            affected_percent = st.session_state["rp_affected_percent"]
            people_affected = st.session_state["rp_people_affected"]

            st.subheader("Current Scenario")
            c1, c2, c3 = st.columns(3)
            c1.metric("District", district)
            c2.metric("Affected Population", f"{people_affected:,}")
            c3.metric("Population Affected", f"{affected_percent}%")
            st.caption(f"Analysis generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            st.divider()

            total_required = report["Needed"].sum()
            total_allocated = report["Allocated"].sum()
            total_shortage = report["Shortage"].sum()
            total_surplus = report["Surplus"].sum()
            average_coverage = report["Coverage %"].mean()

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Required", f"{total_required:,.1f}")
            c2.metric("Allocated", f"{total_allocated:,.1f}")
            c3.metric("Shortage", f"{total_shortage:,.1f}")
            c4.metric("Surplus", f"{total_surplus:,.1f}")
            c5.metric("Avg. Coverage", f"{average_coverage:.1f}%")

            st.subheader("Final Allocation")
            st.dataframe(report[["Category", "Inventory Item", "Unit", "Needed", "Available", "Allocated"]],
                         use_container_width=True, hide_index=True)

            st.subheader("Shortage & Surplus Results")
            st.dataframe(report[["Category", "Inventory Item", "Unit", "Shortage", "Surplus", "Coverage %", "Priority", "Status"]],
                         use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("Resource Comparison")
            chart_data = report[["Inventory Item", "Needed", "Available", "Allocated"]].melt(
                id_vars="Inventory Item", var_name="Resource Status", value_name="Quantity")
            st.plotly_chart(px.bar(chart_data, x="Inventory Item", y="Quantity", color="Resource Status",
                                    barmode="group", title="Required vs Available vs Allocated"),
                             use_container_width=True)

            st.subheader("Shortage Analysis")
            shortage_data = report[report["Shortage"] > 0][["Inventory Item", "Shortage"]]
            if shortage_data.empty:
                st.success("No shortage exists for the current affected population.")
            else:
                st.plotly_chart(px.bar(shortage_data, x="Inventory Item", y="Shortage", title="Current Relief Shortages"),
                                 use_container_width=True)
                critical_items = report[report["Shortage"] > 0].sort_values("Shortage", ascending=False)
                st.markdown("**Priority Shortages**")
                st.dataframe(critical_items[["Inventory Item", "Needed", "Available", "Shortage", "Coverage %", "Priority"]],
                             use_container_width=True, hide_index=True)

            st.subheader("Allocation Coverage")
            coverage_chart = px.bar(report, x="Inventory Item", y="Coverage %", text="Coverage %",
                                     title="Percentage of Required Relief Covered")
            coverage_chart.update_yaxes(range=[0, max(100, float(report["Coverage %"].max()) + 10)])
            st.plotly_chart(coverage_chart, use_container_width=True)

            st.subheader("Cross-District Need Ranking")
            ranking = build_reallocation_report(district_df, affected_percent)
            ranking["Selected District"] = ranking["District"].apply(lambda v: "⭐ Selected" if v == district else "")
            st.dataframe(ranking, use_container_width=True, hide_index=True)

            st.download_button("📥 Download Final Allocation Report", data=report.to_csv(index=False).encode("utf-8"),
                                file_name=f"final_allocation_{district}.csv", mime="text/csv")


# Disaster events
def page_disaster_events():
    st.title("📋 Disaster Events Log")
    st.caption("Events logged automatically by the risk engine (High/Severe readings), plus any added manually below.")

    districts = get_districts()
    district_names = {d[0]: d[1] for d in districts}

    filter_choice = st.selectbox("Filter by district", ["All districts"] + [d[1] for d in districts])
    filter_id = None
    if filter_choice != "All districts":
        filter_id = next(d[0] for d in districts if d[1] == filter_choice)

    events = get_events(filter_id)

    if events:
        df = pd.DataFrame(events, columns=["Event ID", "District ID", "Disaster Type", "Event Date", "Risk Level", "Description"])
        df["District"] = df["District ID"].map(district_names)
        display_df = df[["Event ID", "District", "Disaster Type", "Event Date", "Risk Level", "Description"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        with st.expander("🗑️ Delete an event"):
            options = {f"#{e[0]} — {district_names.get(e[1], '?')} — {e[2]} ({e[3]})": e[0] for e in events}
            choice = st.selectbox("Select event", list(options.keys()))
            if st.button("Delete Event"):
                delete_event(options[choice])
                st.warning("Event deleted.")
                st.rerun()
    else:
        st.info("No disaster events logged yet. High/Severe readings on the Weather & Risk page will appear here automatically.")

    with st.expander("➕ Add an event manually"):
        if not districts:
            st.info("Add a district first.")
        else:
            with st.form("manual_event_form", clear_on_submit=True):
                d_choice = st.selectbox("District", [d[1] for d in districts], key="manual_event_district")
                d_id = next(d[0] for d in districts if d[1] == d_choice)
                e_type = st.selectbox("Disaster Type", ["Flood", "Landslide", "Storm", "Heatwave", "Other"])
                e_date = st.date_input("Event Date")
                e_level = st.selectbox("Risk Level", ["Low", "Moderate", "High", "Severe"])
                e_desc = st.text_area("Description")
                if st.form_submit_button("Add Event", type="primary"):
                    add_event(d_id, e_type, e_date.isoformat(), e_level, e_desc)
                    st.success("Event added.")
                    st.rerun()


# Main
PAGES = {
    "🏠 Home": page_home,
    "🌦️ Weather & Risk": page_weather_risk,
    "🏘️ Districts & Shelters": page_districts_shelters,
    "📦 Inventory": page_inventory,
    "🧺 Relief Planning": page_relief_planning,
    "📋 Disaster Events": page_disaster_events,
}

st.sidebar.title("🚨 Disaster Relief System")
selection = st.sidebar.radio("Navigate", list(PAGES.keys()))
st.sidebar.divider()

PAGES[selection]()
