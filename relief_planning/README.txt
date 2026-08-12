MEMBER 4 - DYNAMIC STANDALONE RELIEF PLANNING

This standalone version does not require Member 3 or MySQL yet.

It uses CSV files in the data folder so Member 4 can run and be tested
independently.

FILES

member4_app.py
requirements.txt
data/
    district_information.csv
    relief_inventory.csv

PAGES

PAGE 1 - Requirements & Allocation
- Select a district.
- See district population, province and shelters.
- Use the affected-population slider.
- The number of affected people changes immediately with the slider.
- Food, water and medicine requirements change with the affected population.
- Existing inventory is compared with the calculated requirement.
- Allocation, shortage, surplus and coverage are calculated dynamically.
- Click "Update Final Analysis" to save the current scenario for Page 2.

PAGE 2 - Final Allocation & Shortage Analysis
- Uses the selected district and affected population from Page 1.
- Shows final required, allocated, shortage and surplus quantities.
- Shows coverage percentage.
- Shows required vs available vs allocated chart.
- Shows shortage chart when shortages exist.
- Shows shortage priorities.
- Shows allocation coverage.
- Shows cross-district need ranking.
- Allows the final allocation report to be downloaded as CSV.

REQUIREMENT RULES

Food = 2 meal packs per person
Water = 3 litres per person
Medicine = 1 kit per 25 people, rounded up

For comparing food with the current inventory:
1 meal pack = 0.25 kg rice.

HOW TO RUN

1. Open this folder in VS Code.

2. Open Terminal.

3. Run:
   pip install -r requirements.txt

4. Run:
   streamlit run member4_app.py

5. Open the Local URL shown by Streamlit.

LATER INTEGRATION

The current CSV loading can later be replaced by Member 3's database
functions. The requirement and allocation calculation functions are
kept separate so they can be reused during integration.

The app does not create or manage any database tables.
