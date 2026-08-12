import streamlit as st
import pandas as pd
import os
import math
from datetime import datetime

#Configurations
DISTRICT_CSV = "district_information.csv"
INVENTORY_CSV = "relief_inventory.csv"
DISASTER_EVENTS_CSV = "historical_disaster_events.csv" 

MEALS_PER_PERSON = 2          # Food  = 2 meal packs per person
WATER_LITERS_PER_PERSON = 3   # Water = 3 litres per person
PEOPLE_PER_MEDICINE_KIT = 25  # Medicine = 1 kit per 25 people

# Inventory tracks "Rice (kg)", not "meal packs" — this is a simple,
# clearly-stated conversion assumption between the two.
KG_RICE_PER_MEAL_PACK = 0.25  # 1 meal pack ≈ 0.25 kg of rice


#Loading data
@st.cache_data
def load_district_data(path: str = DISTRICT_CSV) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data
def load_inventory_data(path: str = INVENTORY_CSV) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data
def load_disaster_events_data(path: str = DISASTER_EVENTS_CSV) -> pd.DataFrame:
    return pd.read_csv(path)


#Core logic and reusable functions
def calculate_aid_needed(population: int) -> dict:
    """Calculate relief aid required for a given number of people."""
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


def check_inventory(aid_needed: dict, inventory_df: pd.DataFrame) -> pd.DataFrame:
    """Compare aid needed against current inventory and flag shortages."""

    def get_stock(item_name: str) -> float:
        row = inventory_df[inventory_df["Item"] == item_name]
        return float(row["Current_Quantity"].iloc[0]) if not row.empty else 0.0

    rows = [
        {
            "Category": "Food", "Inventory Item": "Rice", "Unit": "kg",
            "Needed": round(aid_needed["Food (rice kg equivalent)"], 1),
            "Available": get_stock("Rice"),
        },
        {
            "Category": "Water", "Inventory Item": "Water", "Unit": "liters",
            "Needed": round(aid_needed["Water (litres)"], 1),
            "Available": get_stock("Water"),
        },
        {
            "Category": "Medicine", "Inventory Item": "Medicine Kits", "Unit": "kits",
            "Needed": aid_needed["Medicine (kits)"],
            "Available": get_stock("Medicine Kits"),
        },
    ]

    report = pd.DataFrame(rows)
    report["Shortfall"] = (report["Needed"] - report["Available"]).clip(lower=0)
    report["Status"] = report["Shortfall"].apply(
        lambda x: "⚠️ SHORTAGE" if x > 0 else "✅ SUFFICIENT"
    )
    return report


def build_shortage_report(report: pd.DataFrame) -> pd.DataFrame:
    """Return only the rows where supplies are NOT enough."""
    return report[report["Shortfall"] > 0].copy()


def build_used_supplies_report(event_row: pd.Series) -> pd.DataFrame:
    """
    Build a report of supplies used up for ONE specific disaster event.
    Rice and Water usage come directly from historical_disaster_events.csv.
    Medicine usage isn't tracked in that file, so it's estimated using
    the same 1-kit-per-25-people formula, clearly labeled as an estimate.
    """
    people_affected = int(event_row["People_Affected"])
    estimated_medicine_used = math.ceil(people_affected / PEOPLE_PER_MEDICINE_KIT)

    rows = [
        {"Item": "Rice", "Unit": "kg", "Quantity Used": event_row["Relief_Rice_kg"], "Source": "Recorded"},
        {"Item": "Water", "Unit": "liters", "Quantity Used": event_row["Relief_Water_liters"], "Source": "Recorded"},
        {"Item": "Medicine Kits", "Unit": "kits", "Quantity Used": estimated_medicine_used, "Source": "Estimated"},
    ]
    return pd.DataFrame(rows)


#New: comprehensive relief report helpers
def add_stock_consumption(report: pd.DataFrame) -> pd.DataFrame:
    """Add a '% Stock Consumed' column (Needed / Available * 100) to the inventory report."""
    report = report.copy()

    def pct(row):
        if row["Available"] == 0:
            return float("inf") if row["Needed"] > 0 else 0.0
        return round((row["Needed"] / row["Available"]) * 100, 1)

    report["% Stock Consumed"] = report.apply(pct, axis=1)
    return report


def add_priority_flags(shortage_df: pd.DataFrame) -> pd.DataFrame:
    """
    Rank shortage rows by how critical the gap is, based on the % of the need
    that is NOT covered by current stock (Shortfall / Needed * 100).
    """
    shortage_df = shortage_df.copy()

    def pct_short(row):
        if row["Needed"] == 0:
            return 0.0
        return (row["Shortfall"] / row["Needed"]) * 100

    def priority(pct):
        if pct > 50:
            return "🔴 Critical"
        elif pct > 20:
            return "🟠 Moderate"
        else:
            return "🟡 Minor"

    shortage_df["% Short"] = shortage_df.apply(pct_short, axis=1).round(1)
    shortage_df["Priority"] = shortage_df["% Short"].apply(priority)
    return shortage_df.sort_values("% Short", ascending=False)


def build_reallocation_report(
    current_district: str,
    district_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    affected_percent: int,
) -> pd.DataFrame:
    """
    Compare the selected district's relief need against every other district's
    need. Relief inventory in this system is tracked as ONE shared pool (not
    per-district), so this ranks districts by estimated need so the shared
    stock can be prioritized/reallocated toward the districts that need it most.
    """
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

    realloc_df = pd.DataFrame(rows).sort_values("People Affected", ascending=False)
    realloc_df["Selected District"] = realloc_df["District"].apply(
        lambda d: "⭐ Selected" if d == current_district else ""
    )
    return realloc_df


#Streamlit UI
def render_relief_planning_page():
    st.title("🧺 Relief Planning")
    st.caption("Member 4 — Calculate aid required, check inventory, and report on supplies used")

    required_files = [DISTRICT_CSV, INVENTORY_CSV, DISASTER_EVENTS_CSV]
    missing = [f for f in required_files if not os.path.exists(f)]
    if missing:
        st.error(
            f"Missing required file(s): {', '.join(missing)}. "
            "Make sure all CSVs sit in the same folder as the app "
            "(or update the paths at the top of this file)."
        )
        st.stop()

    district_df = load_district_data()
    inventory_df = load_inventory_data()
    events_df = load_disaster_events_data()

    #  District selection 
    st.subheader("1. Select District")
    district_name = st.selectbox("District", sorted(district_df["District"].unique()))
    district_row = district_df[district_df["District"] == district_name].iloc[0]
    district_population = int(district_row["Population"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Population", f"{district_population:,}")
    col2.metric("Province", district_row["Province"])
    col3.metric("Shelters", int(district_row["Shelters"]))

    #  Affected population override 
    st.subheader("2. People Affected")
    st.write(
        "By default the full district population is used. Adjust below if you "
        "have a more specific estimate (e.g. from Member 2's risk module)."
    )
    affected_percent = st.slider("Percentage of district population affected", 1, 100, 100)
    people_affected = round(district_population * affected_percent / 100)
    st.write(f"**People affected used for calculation:** {people_affected:,}")

    #  Aid calculation 
    st.subheader("3. Aid Required")
    aid_needed = calculate_aid_needed(people_affected)

    a1, a2, a3 = st.columns(3)
    a1.metric("Food (meal packs)", f"{aid_needed['Food (meal packs)']:,}")
    a2.metric("Water (litres)", f"{aid_needed['Water (litres)']:,}")
    a3.metric("Medicine (kits)", f"{aid_needed['Medicine (kits)']:,}")

    with st.expander("Show formulas used"):
        st.markdown(
            f"""
            - **Food** = {MEALS_PER_PERSON} meal packs × population
              (≈ {KG_RICE_PER_MEAL_PACK} kg rice per meal pack, for inventory comparison)
            - **Water** = {WATER_LITERS_PER_PERSON} litres × population
            - **Medicine** = 1 kit per {PEOPLE_PER_MEDICINE_KIT} people (rounded up)
            """
        )

    #  Inventory check 
    st.subheader("4. Inventory Check")
    report = check_inventory(aid_needed, inventory_df)
    st.dataframe(report, use_container_width=True, hide_index=True)

    with st.expander("View raw relief inventory data"):
        st.dataframe(inventory_df, use_container_width=True, hide_index=True)

    #  Shortage report 
    st.subheader("5. Shortage Report")
    shortage_df = build_shortage_report(report)

    if shortage_df.empty:
        st.success("No shortages detected — current inventory can cover the estimated need.")
    else:
        st.error(f"Shortage detected in {len(shortage_df)} item(s):")
        st.dataframe(shortage_df, use_container_width=True, hide_index=True)
        st.download_button(
            label="📥 Download Shortage Report (CSV)",
            data=shortage_df.to_csv(index=False).encode("utf-8"),
            file_name=f"shortage_report_{district_name}.csv",
            mime="text/csv",
        )

    st.divider()

    #  Used-supplies report for a past disaster 
    st.subheader("6. Supplies Used — Past Disaster Report")
    st.write(
        "Select a recorded disaster event to see how much relief was "
        "actually used up during that event."
    )

    district_events = events_df[events_df["District"] == district_name]

    if district_events.empty:
        st.info(f"No recorded disaster events found for {district_name}.")
    else:
        event_labels = (
            district_events["Event_ID"] + " — " + district_events["Date"] + " — "
            + district_events["Disaster_Type"] + " (" + district_events["Severity"] + ")"
        )
        selected_label = st.selectbox("Disaster event", event_labels)
        selected_event = district_events.loc[event_labels == selected_label].iloc[0]

        e1, e2, e3 = st.columns(3)
        e1.metric("People Affected", f"{int(selected_event['People_Affected']):,}")
        e2.metric("Severity", selected_event["Severity"])
        e3.metric("Risk Score", int(selected_event["Risk_Score"]))

        used_report = build_used_supplies_report(selected_event)
        st.dataframe(used_report, use_container_width=True, hide_index=True)
        st.caption("Rice and Water figures are recorded values. Medicine Kits are estimated "
                   "using the same formula (1 kit per 25 people) since usage isn't tracked "
                   "in the historical data.")

        st.download_button(
            label="📥 Download Used Supplies Report (CSV)",
            data=used_report.to_csv(index=False).encode("utf-8"),
            file_name=f"used_supplies_{selected_event['Event_ID']}.csv",
            mime="text/csv",
        )

    st.divider()

    #  Comprehensive relief report (title/metadata, summary, % consumed,
    #  priority flags, cross-district reallocation, chart, assumptions) 
    st.subheader("7. Comprehensive Relief Report")

    st.markdown(
        f"**District:** {district_name} &nbsp;|&nbsp; "
        f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;|&nbsp; "
        f"**% Population Affected Used:** {affected_percent}%"
    )

    if shortage_df.empty:
        st.success(f"**Summary:** {people_affected:,} people affected — ✅ SUFFICIENT (no shortages)")
    else:
        st.error(f"**Summary:** {people_affected:,} people affected — ⚠️ SHORTAGE in {len(shortage_df)} item(s)")

    st.markdown("**Needed vs Available vs Shortfall (with % Stock Consumed)**")
    report_with_consumption = add_stock_consumption(report)
    st.dataframe(report_with_consumption, use_container_width=True, hide_index=True)

    if not shortage_df.empty:
        st.markdown("**Shortage Priority**")
        priority_df = add_priority_flags(shortage_df)
        st.dataframe(priority_df, use_container_width=True, hide_index=True)

    st.markdown("**Recommended Reallocation Across Districts**")
    st.caption(
        "Relief inventory in this system is tracked as one shared pool rather than "
        "per district, so this ranks all districts by estimated need so the shared "
        "stock can be prioritized toward the districts that need it most."
    )
    reallocation_df = build_reallocation_report(district_name, district_df, inventory_df, affected_percent)
    st.dataframe(reallocation_df, use_container_width=True, hide_index=True)

    st.markdown("**Needed vs Available (Chart)**")
    chart_data = report.set_index("Inventory Item")[["Needed", "Available"]]
    st.bar_chart(chart_data)

    with st.expander("Assumptions used in this report"):
        st.markdown(
            f"""
            - Food = {MEALS_PER_PERSON} meal packs per person (≈ {KG_RICE_PER_MEAL_PACK} kg rice per meal pack)
            - Water = {WATER_LITERS_PER_PERSON} litres per person
            - Medicine = 1 kit per {PEOPLE_PER_MEDICINE_KIT} people (rounded up)
            - Relief inventory is tracked as a single shared pool, not per-district
            """
        )


# Standalone run
if __name__ == "__main__":
    st.set_page_config(page_title="Relief Planning", page_icon="🧺", layout="wide")
    render_relief_planning_page()