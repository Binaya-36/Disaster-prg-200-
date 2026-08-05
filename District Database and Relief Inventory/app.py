import streamlit as st
from database import create_tables
import district_management as dm
import inventory_management as im
import disaster_events as de
import seed_data
import datetime

create_tables()
seed_data.seed_districts()

st.set_page_config(page_title="District & Inventory Management", layout="wide")
st.title("District & Relief Inventory Management")

page = st.sidebar.radio("Go to", ["District Management", "Shelter Management", "Inventory Management", "Disaster Events"])

# ---------------- District Management ----------------
if page == "District Management":
    st.header("District Management")

    with st.expander("Add New District"):
        name = st.text_input("District Name")
        province = st.text_input("Province")
        population = st.number_input("Population", min_value=0, step=1000)
        terrain = st.selectbox("Terrain", ["Mountain", "Hill", "Terai"])
        vulnerability = st.selectbox("Vulnerability Level", ["Low", "Moderate", "High", "Severe", "Unknown"])
        if st.button("Add District"):
            dm.add_district(name, province, population, terrain, vulnerability)
            st.success(f"District '{name}' added.")
            st.rerun()

    st.subheader("Existing Districts")
    districts = dm.get_districts()
    for d in districts:
        district_id, name, province, population, terrain, shelter_count, flood_prone, landslide_prone, vulnerability = d
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([2, 1.5, 1.5, 1.2, 1, 1, 1, 1])
        col1.write(name)
        col2.write(province)
        col3.write(f"{population:,}")
        col4.write(terrain)
        col5.write(vulnerability)
        col6.write("🌊" if flood_prone == "Yes" else "—")
        col7.write("⛰️" if landslide_prone == "Yes" else "—")
        if col8.button("Delete", key=f"del_dist_{district_id}"):
            dm.delete_district(district_id)
            st.rerun()

# ---------------- Shelter Management ----------------
elif page == "Shelter Management":
    st.header("Shelter Management")

    districts = dm.get_districts()
    if not districts:
        st.warning("Add a district first.")
    else:
        district_options = {d[1]: d[0] for d in districts}
        selected_name = st.selectbox("Select District", list(district_options.keys()))
        district_id = district_options[selected_name]

        with st.expander("Add New Shelter"):
            shelter_name = st.text_input("Shelter Name")
            capacity = st.number_input("Capacity", min_value=0, step=10)
            occupancy = st.number_input("Current Occupancy", min_value=0, step=10)
            if st.button("Add Shelter"):
                dm.add_shelter(district_id, shelter_name, capacity, occupancy)
                st.success(f"Shelter '{shelter_name}' added.")
                st.rerun()

        st.subheader(f"Shelters in {selected_name}")
        shelters = dm.get_shelters(district_id)
        for s in shelters:
            shelter_id, d_id, s_name, cap, occ = s
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.write(s_name)
            col2.write(f"Capacity: {cap}")
            col3.write(f"Occupancy: {occ}")
            if col4.button("Delete", key=f"del_shel_{shelter_id}"):
                dm.delete_shelter(shelter_id)
                st.rerun()

# ---------------- Inventory Management ----------------
elif page == "Inventory Management":
    st.header("Relief Inventory Management")

    districts = dm.get_districts()
    if not districts:
        st.warning("Add a district first.")
    else:
        district_options = {d[1]: d[0] for d in districts}
        selected_name = st.selectbox("Select District", list(district_options.keys()))
        district_id = district_options[selected_name]

        with st.expander("Add New Inventory Item"):
            item_name = st.text_input("Item Name (e.g. Food, Water, Blankets, Tents)")
            quantity = st.number_input("Quantity", min_value=0, step=10)
            unit = st.text_input("Unit (e.g. kg, litres, pieces)")
            threshold = st.number_input("Low Stock Threshold", min_value=0, step=5, value=10)
            if st.button("Add Item"):
                im.add_item(district_id, item_name, quantity, unit, threshold)
                st.success(f"Item '{item_name}' added.")
                st.rerun()

        st.subheader(f"Inventory in {selected_name}")
        items = im.get_inventory(district_id)
        for item in items:
            item_id, d_id, i_name, qty, unit, threshold = item
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.write(i_name)
            col2.write(f"{qty} {unit}")
            if qty <= threshold:
                col3.error("Low stock")
            else:
                col3.success("OK")
            if col4.button("Delete", key=f"del_item_{item_id}"):
                im.delete_item(item_id)
                st.rerun()

        st.subheader("Low Stock Alerts (All Districts)")
        low_items = im.get_low_stock_items()
        if low_items:
            for li in low_items:
                st.warning(f"{li[2]} is low in district ID {li[1]}: {li[3]} {li[4]} left")
        else:
            st.info("No low stock items currently.")

# ---------------- Disaster Events ----------------
elif page == "Disaster Events":
    st.header("Disaster Event Records")

    districts = dm.get_districts()
    if not districts:
        st.warning("Add a district first.")
    else:
        district_options = {d[1]: d[0] for d in districts}
        selected_name = st.selectbox("Select District", list(district_options.keys()))
        district_id = district_options[selected_name]

        with st.expander("Log New Disaster Event"):
            disaster_type = st.selectbox("Disaster Type", ["Flood", "Landslide", "Storm", "Heatwave"])
            event_date = st.date_input("Event Date", value=datetime.date.today())
            risk_level = st.selectbox("Risk Level", ["Low", "Moderate", "High", "Severe"])
            description = st.text_area("Description (optional)")
            if st.button("Log Event"):
                de.add_event(district_id, disaster_type, str(event_date), risk_level, description)
                st.success(f"{disaster_type} event logged for {selected_name}.")
                st.rerun()

        st.subheader(f"Event History for {selected_name}")
        events = de.get_events(district_id)
        for e in events:
            event_id, d_id, d_type, e_date, risk, desc = e
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 1])
            col1.write(d_type)
            col2.write(e_date)
            col3.write(risk)
            col4.write(desc)
            if col5.button("Delete", key=f"del_event_{event_id}"):
                de.delete_event(event_id)
                st.rerun()
