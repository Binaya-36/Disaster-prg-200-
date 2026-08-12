import streamlit as st
from database import create_tables
import district_management as dm
import inventory_management as im
import disaster_events as de
import seed_data
import datetime

create_tables()
seed_data.seed_districts()
seed_data.seed_inventory()

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
        terrain = st.selectbox("Terrain", ["Mountain", "Hill", "Terai", "Valley", "Plain"])
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

        # Show the result of the last auto-stock action, if any, even after
        # the page has rerun (st.info calls right before st.rerun() would
        # otherwise disappear before anyone could read them).
        if st.session_state.get("last_stock_messages"):
            with st.container(border=True):
                st.markdown(f"**Stock distributed to '{st.session_state['last_stock_shelter_name']}':**")
                for msg in st.session_state["last_stock_messages"]:
                    st.write(f"- {msg}")
            if st.button("Dismiss"):
                st.session_state["last_stock_messages"] = None
                st.rerun()

        with st.expander("Add New Shelter"):
            shelter_name = st.text_input("Shelter Name")
            capacity = st.number_input("Capacity", min_value=0, step=10)
            occupancy = st.number_input(
                "Current Occupancy", min_value=0, step=10,
                help="Cannot exceed capacity."
            )
            auto_stock = st.checkbox(
                "Auto-stock with 5 essential relief items (Rice, Water, Medicine, Blankets, Tents) — pulled from Central Inventory",
                value=True
            )
            if st.button("Add Shelter"):
                if occupancy > capacity:
                    st.error(
                        f"Occupancy ({occupancy}) cannot exceed capacity ({capacity}). "
                        f"Lower the occupancy or raise the capacity."
                    )
                elif not shelter_name:
                    st.warning("Shelter name is required.")
                else:
                    new_shelter_id = dm.add_shelter(district_id, shelter_name, capacity, occupancy)
                    st.success(f"Shelter '{shelter_name}' added.")
                    if auto_stock:
                        stock_messages = im.seed_shelter_essentials(new_shelter_id, capacity, district_id=district_id)
                        # Stash in session_state so it survives the rerun below
                        # and is visible above, instead of flashing on screen.
                        st.session_state["last_stock_messages"] = stock_messages
                        st.session_state["last_stock_shelter_name"] = shelter_name
                    st.rerun()

        st.subheader(f"Shelters in {selected_name}")
        shelters = dm.get_shelters(district_id)
        for s in shelters:
            shelter_id, d_id, s_name, cap, occ = s
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.write(s_name)
            col2.write(f"Capacity: {cap}")
            fill_pct = f" ({occ / cap:.0%} full)" if cap else ""
            col3.write(f"Occupancy: {occ}{fill_pct}")
            if col4.button("Delete", key=f"del_shel_{shelter_id}"):
                dm.delete_shelter(shelter_id)
                st.rerun()

            # This is the part that was missing entirely: showing what stock
            # actually sits at this shelter after auto-stocking or manual
            # allocation, instead of only being visible as a deduction from
            # the district/central inventory numbers.
            with st.expander(f"View stock at {s_name}"):
                shelter_items = im.get_shelter_inventory(shelter_id)
                if shelter_items:
                    for item in shelter_items:
                        item_id, sku, i_d_id, i_s_id, i_name, qty, unit, threshold, last_restocked = item
                        ic1, ic2, ic3, ic4 = st.columns([2, 2, 2, 1])
                        ic1.write(i_name)
                        ic2.write(f"{qty:,} {unit}")
                        ic3.write(f"Last restocked: {last_restocked}")
                        if qty <= threshold:
                            ic4.error("Low")
                        else:
                            ic4.success("OK")
                else:
                    st.info("No stock recorded at this shelter yet.")

                # Manual top-up: previously the only way stock ever reached a
                # shelter was the one-time auto-stock at creation. This lets you
                # add more of any central item to an existing shelter any time
                # (e.g. the auto-stocked amount of Medicine Kits turns out to be
                # too little once you know more about the situation on the ground).
                st.markdown("**Add stock to this shelter**")
                central_items_for_shelter = im.get_central_inventory()
                if not central_items_for_shelter:
                    st.caption("No central inventory items available to allocate.")
                else:
                    shelter_item_lookup = {
                        f"{it[4]} — {it[5]:,} {it[6]} available": it for it in central_items_for_shelter
                    }
                    shelter_item_choice = st.selectbox(
                        "Item", list(shelter_item_lookup.keys()), key=f"shelter_item_select_{shelter_id}"
                    )
                    chosen = shelter_item_lookup[shelter_item_choice]
                    _, _, _, _, chosen_name, chosen_qty, chosen_unit, chosen_threshold, _ = chosen
                    headroom = max(chosen_qty - chosen_threshold, 0)
                    st.caption(
                        f"{chosen_qty:,} {chosen_unit} in central stock · minimum reserve: {chosen_threshold:,} {chosen_unit} · "
                        f"safely allocatable: {headroom:,} {chosen_unit}"
                    )
                    shelter_add_qty = st.number_input(
                        "Quantity to add", min_value=0, step=1, key=f"shelter_add_qty_{shelter_id}"
                    )
                    shelter_allow_dip = st.checkbox(
                        "Allow dipping into central reserve", value=False, key=f"shelter_allow_dip_{shelter_id}"
                    )
                    if st.button("Add Stock", key=f"shelter_add_stock_btn_{shelter_id}"):
                        if shelter_add_qty > 0:
                            success, message, amount = im.allocate_from_central_to_shelter(
                                item_name=chosen_name,
                                shelter_id=shelter_id,
                                district_id=district_id,
                                quantity=shelter_add_qty,
                                low_stock_threshold=chosen_threshold,
                                allow_reserve_dip=shelter_allow_dip,
                            )
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.warning("Enter a quantity greater than 0.")

# ---------------- Inventory Management ----------------
elif page == "Inventory Management":
    st.header("Relief Inventory Management")

    # ---- Central / National Inventory ----
    st.subheader("Central / National Inventory")
    central_items = im.get_central_inventory()
    if central_items:
        for item in central_items:
            item_id, sku, d_id, s_id, i_name, qty, unit, threshold, last_restocked = item
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            col1.write(f"{i_name} ({sku})" if sku else i_name)
            col2.write(f"{qty:,} {unit}")
            col3.write(f"Min: {threshold:,}")
            col4.write(f"Last restocked: {last_restocked}")
            if qty <= threshold:
                col5.error("Low")
            else:
                col5.success("OK")
    else:
        st.info("No central inventory data found.")

    with st.expander("Restock an Existing Central Item"):
        if central_items:
            item_lookup = {f"{it[4]} ({it[6]})": it[0] for it in central_items}
            item_to_restock = st.selectbox("Select item", list(item_lookup.keys()), key="central_restock_select")
            restock_amt = st.number_input("Amount to add", min_value=0, step=100, key="central_restock_amt")
            if st.button("Restock Central Item"):
                if restock_amt > 0:
                    im.restock_item(item_lookup[item_to_restock], restock_amt)
                    st.success(f"Restocked {restock_amt} units.")
                    st.rerun()
                else:
                    st.warning("Enter an amount greater than 0.")
        else:
            st.info("No central items to restock yet — add one below.")

    with st.expander("Add a New Item Type to Central Inventory"):
        new_central_name = st.text_input("Item Name", key="new_central_name")
        new_central_qty = st.number_input("Starting Quantity", min_value=0, step=100, key="new_central_qty")
        new_central_unit = st.text_input("Unit (e.g. kg, liters, pieces)", key="new_central_unit")
        new_central_threshold = st.number_input("Low Stock Threshold", min_value=0, step=50, value=100, key="new_central_threshold")
        new_central_sku = st.text_input("SKU / Item Code (optional)", key="new_central_sku")
        if st.button("Add to Central Inventory"):
            if new_central_name and new_central_unit:
                im.add_central_item(
                    new_central_name, new_central_qty, new_central_unit,
                    new_central_threshold, sku=new_central_sku or None
                )
                st.success(f"'{new_central_name}' added to central inventory.")
                st.rerun()
            else:
                st.warning("Item name and unit are required.")

    st.divider()

    # ---- Allocate stock from Central to a District ----
    st.subheader("Allocate Stock to a District")
    districts = dm.get_districts()
    if not districts:
        st.warning("Add a district first.")
    elif not central_items:
        st.warning("Add central inventory items first before allocating.")
    else:
        district_options = {d[1]: d[0] for d in districts}
        selected_name = st.selectbox("Select District", list(district_options.keys()), key="alloc_district_select")
        district_id = district_options[selected_name]

        item_lookup = {f"{it[4]} — {it[5]:,} {it[6]} available": it[0] for it in central_items}
        item_to_allocate = st.selectbox("Select Item from Central Stock", list(item_lookup.keys()), key="alloc_item_select")

        # Show how much can be allocated before central stock dips below its
        # own minimum reserve, so it's not possible to unknowingly dump the
        # entire central supply into one district.
        selected_central = next(it for it in central_items if it[0] == item_lookup[item_to_allocate])
        _, _, _, _, sel_name, sel_qty, sel_unit, sel_threshold, _ = selected_central
        headroom = max(sel_qty - sel_threshold, 0)
        st.caption(
            f"{sel_qty:,} {sel_unit} in central stock · minimum reserve: {sel_threshold:,} {sel_unit} · "
            f"safely allocatable without touching reserve: {headroom:,} {sel_unit}"
        )

        alloc_qty = st.number_input("Quantity to Allocate", min_value=0, step=10, key="alloc_qty")
        allow_reserve_dip = st.checkbox(
            "Allow dipping into central reserve (only for a genuine emergency allocation)",
            value=False, key="alloc_allow_reserve_dip"
        )

        if st.button("Allocate to District"):
            if alloc_qty > 0:
                success, message = im.allocate_from_central(
                    item_lookup[item_to_allocate], district_id, alloc_qty,
                    allow_reserve_dip=allow_reserve_dip
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Enter a quantity greater than 0.")

    st.divider()

    # ---- District-level Inventory (view only, shows what's been allocated) ----
    st.subheader("District-Level Inventory")
    if districts:
        view_district_name = st.selectbox("View District", list(district_options.keys()), key="view_district_select")
        view_district_id = district_options[view_district_name]

        items = im.get_inventory(view_district_id)
        if items:
            for item in items:
                item_id, sku, d_id, s_id, i_name, qty, unit, threshold, last_restocked = item
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
        else:
            st.info(f"No stock allocated to {view_district_name} yet. Use 'Allocate Stock to a District' above.")

    st.divider()

    # ---- Low Stock Alerts ----
    st.subheader("Low Stock Alerts (All Items)")
    low_items = im.get_low_stock_items()
    if low_items:
        shelter_lookup = {s[0]: s[2] for s in dm.get_shelters()}
        district_lookup = {d[0]: d[1] for d in districts} if districts else {}
        for li in low_items:
            li_item_id, li_sku, li_d_id, li_s_id, li_name, li_qty, li_unit, li_threshold, li_last_restocked = li
            if li_s_id:
                location = f"Shelter: {shelter_lookup.get(li_s_id, li_s_id)}"
            elif li_d_id:
                location = f"District: {district_lookup.get(li_d_id, li_d_id)}"
            else:
                location = "Central Stock"
            st.warning(f"{li_name} is low at {location}: {li_qty} {li_unit} left (min: {li_threshold})")
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
                