import math
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Member 4 - Relief Planning",
    page_icon="🧺",
    layout="wide"
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

DISTRICT_CSV = os.path.join(DATA_DIR, "district_information.csv")
INVENTORY_CSV = os.path.join(DATA_DIR, "relief_inventory.csv")

MEALS_PER_PERSON = 2
WATER_LITERS_PER_PERSON = 3
PEOPLE_PER_MEDICINE_KIT = 25
KG_RICE_PER_MEAL_PACK = 0.25


@st.cache_data
def load_district_data():
    return pd.read_csv(DISTRICT_CSV)


@st.cache_data
def load_inventory_data():
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
        "Medicine (kits)": medicine_kits_needed
    }


def get_stock(inventory_df, item_name):
    row = inventory_df[inventory_df["Item"] == item_name]

    if row.empty:
        return 0.0

    return float(row["Current_Quantity"].iloc[0])


def build_allocation_report(aid_needed, inventory_df):
    rows = [
        {
            "Category": "Food",
            "Inventory Item": "Rice",
            "Unit": "kg",
            "Needed": round(aid_needed["Food (rice kg equivalent)"], 1),
            "Available": get_stock(inventory_df, "Rice")
        },
        {
            "Category": "Water",
            "Inventory Item": "Water",
            "Unit": "liters",
            "Needed": round(aid_needed["Water (litres)"], 1),
            "Available": get_stock(inventory_df, "Water")
        },
        {
            "Category": "Medicine",
            "Inventory Item": "Medicine Kits",
            "Unit": "kits",
            "Needed": aid_needed["Medicine (kits)"],
            "Available": get_stock(inventory_df, "Medicine Kits")
        }
    ]

    report = pd.DataFrame(rows)

    report["Allocated"] = report[["Needed", "Available"]].min(axis=1)
    report["Shortage"] = (
        report["Needed"] - report["Available"]
    ).clip(lower=0)

    report["Surplus"] = (
        report["Available"] - report["Needed"]
    ).clip(lower=0)

    report["Coverage %"] = (
        report["Allocated"] / report["Needed"] * 100
    ).round(1)

    report["Stock Used %"] = (
        report["Allocated"] / report["Available"].replace(0, float("nan")) * 100
    ).round(1).fillna(0)

    report["Status"] = report["Shortage"].apply(
        lambda value: "⚠️ SHORTAGE"
        if value > 0
        else "✅ SUFFICIENT"
    )

    report["Priority"] = report.apply(
        lambda row: get_priority(row["Shortage"], row["Needed"]),
        axis=1
    )

    return report


def get_priority(shortage, needed):
    if shortage <= 0:
        return "🟢 Covered"

    shortage_percentage = shortage / needed * 100

    if shortage_percentage > 50:
        return "🔴 Critical"
    if shortage_percentage > 20:
        return "🟠 Moderate"

    return "🟡 Minor"


def build_reallocation_report(district_df, affected_percent):
    rows = []

    for _, row in district_df.iterrows():
        population = int(row["Population"])
        people_affected = round(
            population * affected_percent / 100
        )

        aid = calculate_aid_needed(people_affected)

        rows.append({
            "District": row["District"],
            "Population": population,
            "People Affected": people_affected,
            "Rice Needed (kg)": round(
                aid["Food (rice kg equivalent)"], 1
            ),
            "Water Needed (L)": aid["Water (litres)"],
            "Medicine Kits Needed": aid["Medicine (kits)"]
        })

    result = pd.DataFrame(rows)

    return result.sort_values(
        "People Affected",
        ascending=False
    ).reset_index(drop=True)


def save_current_result(district, affected_percent, people_affected, report):
    st.session_state["selected_district"] = district
    st.session_state["affected_percent"] = affected_percent
    st.session_state["people_affected"] = people_affected
    st.session_state["allocation_report"] = report


def page_requirements_allocation(district_df, inventory_df):
    st.title("🧺 Relief Requirements & Allocation")
    st.caption(
        "Member 4 — Calculate relief requirements from the affected "
        "population and allocate available resources."
    )

    st.subheader("1. Select Affected District")

    district_names = sorted(
        district_df["District"].dropna().unique()
    )

    district_name = st.selectbox(
        "District",
        district_names
    )

    district_row = district_df[
        district_df["District"] == district_name
    ].iloc[0]

    population = int(district_row["Population"])

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "District Population",
        f"{population:,}"
    )

    col2.metric(
        "Province",
        district_row["Province"]
    )

    col3.metric(
        "Shelters",
        f"{int(district_row['Shelters']):,}"
    )

    st.subheader("2. Determine Affected Population")

    affected_percent = st.slider(
        "Percentage of district population affected",
        min_value=1,
        max_value=100,
        value=50,
        step=1,
        format="%d%%"
    )

    people_affected = round(
        population * affected_percent / 100
    )

    st.info(
        f"**{people_affected:,} people** are affected "
        f"({affected_percent}% of the district population)."
    )

    st.subheader("3. Relief Required")

    aid_needed = calculate_aid_needed(people_affected)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Food",
        f"{aid_needed['Food (meal packs)']:,} meal packs"
    )

    col2.metric(
        "Water",
        f"{aid_needed['Water (litres)']:,} litres"
    )

    col3.metric(
        "Medicine",
        f"{aid_needed['Medicine (kits)']:,} kits"
    )

    with st.expander("View calculation rules"):
        st.markdown(
            f"""
            - **Food:** {MEALS_PER_PERSON} meal packs per person
            - **Water:** {WATER_LITERS_PER_PERSON} litres per person
            - **Medicine:** 1 kit per {PEOPLE_PER_MEDICINE_KIT} people,
              rounded up
            - **Food inventory comparison:** 1 meal pack ≈
              {KG_RICE_PER_MEAL_PACK} kg rice
            """
        )

    st.subheader("4. Available Inventory & Allocation")

    report = build_allocation_report(
        aid_needed,
        inventory_df
    )

    display_report = report[
        [
            "Category",
            "Inventory Item",
            "Unit",
            "Needed",
            "Available",
            "Allocated",
            "Shortage",
            "Surplus",
            "Coverage %",
            "Status"
        ]
    ]

    st.dataframe(
        display_report,
        use_container_width=True,
        hide_index=True
    )

    shortage_count = int(
        (report["Shortage"] > 0).sum()
    )

    total_shortage = report["Shortage"].sum()

    if shortage_count == 0:
        st.success(
            "All calculated relief requirements can be covered "
            "by the current inventory."
        )
    else:
        st.warning(
            f"{shortage_count} item(s) have a shortage. "
            f"Total shortage across the calculated categories: "
            f"{total_shortage:,.1f} units."
        )

    st.subheader("5. Allocation Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Required",
        f"{report['Needed'].sum():,.1f}"
    )

    col2.metric(
        "Total Allocated",
        f"{report['Allocated'].sum():,.1f}"
    )

    col3.metric(
        "Total Shortage",
        f"{report['Shortage'].sum():,.1f}"
    )

    col4.metric(
        "Total Surplus",
        f"{report['Surplus'].sum():,.1f}"
    )

    if st.button(
        "Update Final Analysis",
        type="primary"
    ):
        save_current_result(
            district_name,
            affected_percent,
            people_affected,
            report
        )
        st.success(
            "Final allocation analysis updated. "
            "Open Page 2 from the sidebar."
        )

    st.caption(
        "The final analysis page uses the current slider value and "
        "inventory values. Change the slider and click the update "
        "button to refresh the saved analysis."
    )


def page_final_analysis(district_df, inventory_df):
    st.title("📊 Final Allocation & Shortage Analysis")

    report = st.session_state.get(
        "allocation_report"
    )

    if report is None:
        st.info(
            "No allocation has been calculated yet. "
            "Go to Page 1, select a district, adjust the affected "
            "population slider, and click 'Update Final Analysis'."
        )
        return

    district = st.session_state["selected_district"]
    affected_percent = st.session_state["affected_percent"]
    people_affected = st.session_state["people_affected"]

    st.subheader("Current Scenario")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "District",
        district
    )

    col2.metric(
        "Affected Population",
        f"{people_affected:,}"
    )

    col3.metric(
        "Population Affected",
        f"{affected_percent}%"
    )

    st.caption(
        f"Analysis generated: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    st.divider()

    total_required = report["Needed"].sum()
    total_allocated = report["Allocated"].sum()
    total_shortage = report["Shortage"].sum()
    total_surplus = report["Surplus"].sum()

    average_coverage = report["Coverage %"].mean()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Required",
        f"{total_required:,.1f}"
    )

    col2.metric(
        "Allocated",
        f"{total_allocated:,.1f}"
    )

    col3.metric(
        "Shortage",
        f"{total_shortage:,.1f}"
    )

    col4.metric(
        "Surplus",
        f"{total_surplus:,.1f}"
    )

    col5.metric(
        "Avg. Coverage",
        f"{average_coverage:.1f}%"
    )

    st.subheader("Final Allocation")

    final_allocation = report[
        [
            "Category",
            "Inventory Item",
            "Unit",
            "Needed",
            "Available",
            "Allocated"
        ]
    ]

    st.dataframe(
        final_allocation,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Shortage & Surplus Results")

    shortage_results = report[
        [
            "Category",
            "Inventory Item",
            "Unit",
            "Shortage",
            "Surplus",
            "Coverage %",
            "Priority",
            "Status"
        ]
    ]

    st.dataframe(
        shortage_results,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("Resource Comparison")

    chart_data = report[
        ["Inventory Item", "Needed", "Available", "Allocated"]
    ].melt(
        id_vars="Inventory Item",
        var_name="Resource Status",
        value_name="Quantity"
    )

    comparison_chart = px.bar(
        chart_data,
        x="Inventory Item",
        y="Quantity",
        color="Resource Status",
        barmode="group",
        title="Required vs Available vs Allocated"
    )

    st.plotly_chart(
        comparison_chart,
        use_container_width=True
    )

    st.subheader("Shortage Analysis")

    shortage_data = report[
        report["Shortage"] > 0
    ][["Inventory Item", "Shortage"]]

    if shortage_data.empty:
        st.success(
            "No shortage exists for the current affected population."
        )
    else:
        shortage_chart = px.bar(
            shortage_data,
            x="Inventory Item",
            y="Shortage",
            title="Current Relief Shortages"
        )

        st.plotly_chart(
            shortage_chart,
            use_container_width=True
        )

        critical_items = report[
            report["Shortage"] > 0
        ].sort_values(
            "Shortage",
            ascending=False
        )

        st.markdown("**Priority Shortages**")

        st.dataframe(
            critical_items[
                [
                    "Inventory Item",
                    "Needed",
                    "Available",
                    "Shortage",
                    "Coverage %",
                    "Priority"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    st.subheader("Allocation Coverage")

    coverage_chart = px.bar(
        report,
        x="Inventory Item",
        y="Coverage %",
        text="Coverage %",
        title="Percentage of Required Relief Covered"
    )

    coverage_chart.update_yaxes(
        range=[0, max(100, float(report["Coverage %"].max()) + 10)]
    )

    st.plotly_chart(
        coverage_chart,
        use_container_width=True
    )

    st.subheader("Cross-District Need Ranking")

    ranking = build_reallocation_report(
        district_df,
        affected_percent
    )

    ranking["Selected District"] = ranking["District"].apply(
        lambda value: "⭐ Selected"
        if value == district
        else ""
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 Download Final Allocation Report",
        data=report.to_csv(index=False).encode("utf-8"),
        file_name=f"final_allocation_{district}.csv",
        mime="text/csv"
    )


def main():
    district_df = load_district_data()
    inventory_df = load_inventory_data()

    st.sidebar.title("Member 4")
    st.sidebar.caption("Relief Requirement & Resource Allocation")

    page = st.sidebar.radio(
        "Navigate",
        [
            "Requirements & Allocation",
            "Final Allocation & Shortage Analysis"
        ]
    )

    st.sidebar.divider()
    st.sidebar.info(
        "Standalone prototype. "
        "CSV files are used now and can be replaced by "
        "Member 3's database module during integration."
    )

    if page == "Requirements & Allocation":
        page_requirements_allocation(
            district_df,
            inventory_df
        )
    else:
        page_final_analysis(
            district_df,
            inventory_df
        )


if __name__ == "__main__":
    main()
