import streamlit as st
import math
from datetime import datetime, date
from auth import load_authenticator
from logger import setup_logger

import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()

# Streamlit Interface
st.set_page_config(layout='wide')

st.markdown(
    """
    <div style="text-align: center;">
        <h1 style="color: blue; font-size: 36px;">CARBON INTENSITY INDICATOR (CII)</h1>
        <h3 style="color: green; font-size: 16px;">
            The Carbon Intensity Indicator (CII) regulation is enforced as per Regulation 28 of MARPOL Annex VI,
            which mandates that ships must calculate and report their annual carbon intensity.
            The CII is calculated based on the ship's fuel consumption and distance traveled,
            and it is expressed in grams of CO2 emitted per ton-mile.
            The regulation aims to encourage the shipping industry to reduce its carbon footprint by promoting energy efficiency
            and the use of cleaner fuels.
            Ships are required to meet specific CII rating thresholds, which are determined by their size and type, 
            and they must report their CII annually to the relevant authorities. 
            Non-compliance with CII requirements can result in penalties, including fines and restrictions on port access.
        </h3>
        <h3 style="color: red; font-size: 16px;">
            It was officially adopted by the Marine Environment Protection Committee (MEPC) during its 76th session (MEPC 76) 
            in June 2021 under Resolution MEPC.328(76). The regulation is set to be implemented starting from January 1, 2023, 
            with the first annual reporting due by March 31, 2024. The CII regulation is part of the International Maritime Organization's (IMO)
            broader strategy to reduce greenhouse gas emissions from ships and combat climate change.
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# 1. Ship data dictionary (Base Reference Lines)
# -----------------------------
ship_data = {
    "Bulk Carrier": {
        "unit": "DWT",
        "ranges": {
            "279,000 DWT and above": {"a": 4745, "c": 0.622},
            "Less than 279,000 DWT": {"a": 4745, "c": 0.622},
        }
    },
    "Gas Carrier": {
        "unit": "DWT",
        "ranges": {
            "65,000 DWT and above": {"a": 14405e7, "c": 2.071},
            "Less than 65,000 DWT": {"a": 8104, "c": 0.639},
        }
    },
    "Tanker": {
        "unit": "DWT",
        "ranges": {
            "All sizes": {"a": 5247, "c": 0.610},
        }
    },
    "Container Ship": {
        "unit": "DWT",
        "ranges": {
            "All sizes": {"a": 1984, "c": 0.489},
        }
    },
    "General Cargo Ship": {
        "unit": "DWT",
        "ranges": {
            "20,000 DWT and above": {"a": 31948, "c": 0.792},
            "Less than 20,000 DWT": {"a": 588, "c": 0.3885},
        }
    },
    "Refrigerated Cargo Carrier": {
        "unit": "DWT",
        "ranges": {
            "All sizes": {"a": 4600, "c": 0.557},
        }
    },
    "Combination Carrier": {
        "unit": "DWT",
        "ranges": {
            "All sizes": {"a": 5119, "c": 0.622},
        }
    },
    "LNG Carrier": {
        "unit": "DWT",
        "ranges": {
            "100,000 DWT and above": {"a": 9.827, "c": 0.000},
            "65,000–100,000 DWT": {"a": 14479e10, "c": 2.673},
            "Less than 65,000 DWT": {"a": 14779e10, "c": 2.673},
        }
    },
    "Ro-Ro Cargo Ship (Vehicle Carrier)": {
        "unit": "GT",
        "ranges": {
            "57,700 GT and above": {"a": 3627, "c": 0.590},
            "30,000and above, but less than 57,700 GT": {"a": 3627, "c": 0.590},
            "Less than 30,000 GT": {"a": 330, "c": 0.329},
        }
    },
    "Ro-Ro Cargo Ship": {
        "unit": "GT",
        "ranges": {
            "All sizes": {"a": 1967, "c": 0.485},
        }
    },
    "Ro-Ro Passenger Ship": {
        "unit": "GT",
        "ranges": {
            "Standard": {"a": 2023, "c": 0.460},
            "High-speed craft (SOLAS Ch. X)": {"a": 4196, "c": 0.460},
        }
    },
    "Cruise Passenger Ship": {
        "unit": "GT",
        "ranges": {
            "All sizes": {"a": 930, "c": 0.383},
        }
    },
}

# 2. Boundary data dictionary
cii_wd_data = {
    "Bulk Carrier": [0.86, 0.94, 1.06, 1.18],
    "Gas Carrier (≥ 65,000 DWT)": [0.81, 0.91, 1.12, 1.44],
    "Gas Carrier (< 65,000 DWT)": [0.85, 0.95, 1.06, 1.25],
    "Tanker": [0.82, 0.93, 1.08, 1.28],
    "Container Ship": [0.83, 0.94, 1.07, 1.19],
    "General Cargo Ship": [0.83, 0.94, 1.06, 1.19],
    "Refrigerated Cargo Carrier": [0.78, 0.91, 1.07, 1.20],
    "Combination Carrier": [0.87, 0.96, 1.06, 1.14],
    "LNG Carrier (≥ 100,000 DWT)": [0.89, 0.98, 1.06, 1.13],
    "LNG Carrier (< 100,000 DWT)": [0.78, 0.92, 1.10, 1.37],
    "Ro-Ro Cargo Ship (Vehicle Carrier)": [0.86, 0.94, 1.06, 1.16],
    "Ro-Ro Cargo Ship": [0.76, 0.89, 1.08, 1.27],
    "Ro-Ro Passenger Ship": [0.76, 0.92, 1.14, 1.30],
    "Cruise Passenger Ship": [0.87, 0.95, 1.06, 1.16],
}

# Year & Date Controls
years = list(range(2023, 2030))
selected_year = st.selectbox("Select a year:", years)

# --- SINGLE SHIP SELECTION ZONE ---
ship_type = st.selectbox("Select Ship Type:", list(ship_data.keys()))

capacity_ranges = list(ship_data[ship_type]["ranges"].keys())
capacity_range = st.selectbox("Select Capacity Range:", capacity_ranges)

a = ship_data[ship_type]["ranges"][capacity_range]["a"]
c = ship_data[ship_type]["ranges"][capacity_range]["c"]
unit = ship_data[ship_type]["unit"]

capacity = st.number_input(f"Enter Ship Capacity ({unit}):", min_value=1.0, step=1.0)

# Shuttle Tanker Specific Flags Initialization
is_shuttle_tanker = False
af_tanker = 1.0

if ship_type == "Tanker":
    st.markdown("### Shuttle Tanker Operational Settings")
    is_shuttle_tanker = st.checkbox("Is this vessel a dedicated Shuttle Tanker? (Resolution MEPC.355(78))")
    if is_shuttle_tanker:
        af_tanker = st.number_input(
            "Enter Shuttle Tanker Alignment Factor (AF_Tanker):", 
            min_value=0.0, 
            max_value=1.0, 
            value=0.5, 
            step=0.01,
            help="Value between 0 and 1 representing operational profiles (typically extracted from official trial data or MEPC guidelines)."
        )
# ----------------------------------

# Initial Calculations
CIIref = 0.0
CIIref_y = 0.0

# Initialize boundary metrics so they exist in scope later
superior, lower, upper, inferior = 0.0, 0.0, 0.0, 0.0

if capacity > 0:
    CIIref = a * (capacity ** (-c))
    st.subheader("EEDI Reference Line Result")
    st.write(f"**Reference Line = {CIIref:.4f} g CO₂/ton-mile**")

    # Applying reduction factor mappings
    reduction_factors = {
        2023: 0.05, 2024: 0.07, 2025: 0.09, 2026: 0.11,
        2027: 0.13625, 2028: 0.1625, 2029: 0.18875, 2030: 0.215
    }
    factor = reduction_factors.get(selected_year, 0.0)
    CIIref_y = (1 - factor) * CIIref

    st.subheader(f"EEDI Reference Line Result for {selected_year}")
    st.write(f"**Reference Line = {CIIref_y:.4f} g CO₂/ton-mile**")

    # Dynamic Mapping to Boundary Vector
    wd_key = ship_type  # Default fallback mapping
    
    if ship_type == "Gas Carrier":
        if "65,000 DWT and above" in capacity_range:
            wd_key = "Gas Carrier (≥ 65,000 DWT)"
        else:
            wd_key = "Gas Carrier (< 65,000 DWT)"
            
    elif ship_type == "LNG Carrier":
        if "100,000 DWT and above" in capacity_range:
            wd_key = "LNG Carrier (≥ 100,000 DWT)"
        else:
            wd_key = "LNG Carrier (< 100,000 DWT)"

    wd_vector = cii_wd_data.get(wd_key)

    if wd_vector and CIIref_y > 0:
        superior = wd_vector[0] * CIIref_y
        lower = wd_vector[1] * CIIref_y
        upper = wd_vector[2] * CIIref_y
        inferior = wd_vector[3] * CIIref_y

        st.subheader("CII Rating Boundaries")
        st.write(f"**Superior Boundary (A/B):** {superior:.4f}")
        st.write(f"**Lower Boundary (B/C):** {lower:.4f}")
        st.write(f"**Upper Boundary (C/D):** {upper:.4f}")
        st.write(f"**Inferior Boundary (D/E):** {inferior:.4f}")

else:
    st.error("Please enter a valid ship capacity greater than 0.")

fuel_data = {
    "Diesel/Gas Oil": {"Cf": 3.206, "unit": "t-CO₂/t-Fuel"},
    "Light Fuel Oil (LFO)": {"Cf": 3.151, "unit": "t-CO₂/t-Fuel"},
    "Heavy Fuel Oil (HFO)": {"Cf": 3.114, "unit": "t-CO₂/t-Fuel"},
    "Liquefied Petroleum Gas (LPG) - Propane": {"Cf": 3.000, "unit": "t-CO₂/t-Fuel"},
    "Liquefied Petroleum Gas (LPG) - Butane": {"Cf": 3.030, "unit": "t-CO₂/t-Fuel"},
    "Liquefied Natural Gas (LNG)": {"Cf": 2.750, "unit": "t-CO₂/t-Fuel"},
    "Methanol": {"Cf": 1.375, "unit": "t-CO₂/t-Fuel"},
    "Ethanol": {"Cf": 1.913, "unit": "t-CO₂/t-Fuel"}
}

# --- ATTAINED CII INPUT & TRANSPORT SECTION ---
st.markdown("---")
st.subheader("Attained CII Calculation Inputs (Multi-Fuel & Voyage Adjustments)")

# Voyage/Distance Adjustments inputs (D_t - D_x)
col_dist1, col_dist2 = st.columns(2)
with col_dist1:
    distance_traveled = st.number_input(
        "Enter Total Distance Traveled (D_t) [Nautical Miles]:", 
        min_value=0.0, 
        step=0.1
    )
with col_dist2:
    distance_exempted = st.number_input(
        "Enter Exempted Voyage Distance (D_x) [Nautical Miles]:", 
        min_value=0.0, 
        step=0.1,
        help="Distance sailed for saving life at sea, securing ship safety, or due to damage (MARPOL Reg 28.14)."
    )

# Voyage Fuel Deductions Input (FC_voyage)
st.markdown("### Voyage and Standard Operational Deductions")
col_ded1, col_ded2 = st.columns(2)

with col_ded1:
    fc_voyage_tons = st.number_input(
        "Total Fuel Consumed during Exempted Voyages / Sea Trials (FC_voyage) [Metric Tons]:",
        min_value=0.0,
        step=0.1,
        help="Deductions for trials, or fuel used during MARPOL Regulation 28.14 exempted voyages."
    )

with col_ded2:
    # Standard Operational Adjustments (Disabled if Shuttle Tanker is checked to avoid regulatory double-counting)
    fc_operational_deductions = st.number_input(
        "Standard Operational Deductions (Boilers, Electrical Generation, etc.) [Metric Tons]:",
        min_value=0.0,
        step=0.1,
        disabled=is_shuttle_tanker,
        value=0.0,
        help="Standard corrections (G3 guidelines). Automated Warning: This field is disabled if dedicated Shuttle Tanker deductions are active to avoid double-counting."
    )
    if is_shuttle_tanker:
        st.caption("⚠️ *Standard operational corrections are deactivated because Shuttle Tanker alignment factors take precedence.*")

st.write("### Fuel Breakdown")
st.caption("Input the specific total annual metric tons consumed for each fuel type used over the year.")

# Create grid column system for clean fuel input layout
col_fuel1, col_fuel2 = st.columns(2)
total_co2_tons = 0.0

# Alternate fuel entry across two visual columns
for idx, (fuel_name, details) in enumerate(fuel_data.items()):
    with col_fuel1 if idx % 2 == 0 else col_fuel2:
        consumed = st.number_input(
            f"{fuel_name} Consumed (Metric Tons):",
            min_value=0.0,
            step=0.1,
            key=f"fuel_{idx}"
        )
        if consumed > 0:
            # Apply Shuttle Tanker deduction if activated:
            # TF_j = (1 - AF_Tanker) * FC_j  => Net Chargeable Fuel = FC_j - TF_j = AF_Tanker * FC_j
            if is_shuttle_tanker:
                chargeable_fuel = consumed * af_tanker
                co2_for_this_fuel = chargeable_fuel * details["Cf"]
                total_co2_tons += co2_for_this_fuel
                st.caption(
                    f"↳ **Shuttle Tanker Adjusted:** {chargeable_fuel:.1f} Tons "
                    f"emits ~**{co2_for_this_fuel:.2f}** t-CO₂ (Deducted {(consumed - chargeable_fuel):.1f} Tons via AF)"
                )
            else:
                co2_for_this_fuel = consumed * details["Cf"]
                total_co2_tons += co2_for_this_fuel
                st.caption(f"↳ Emits ~**{co2_for_this_fuel:.2f}** t-CO₂ ($C_F$: {details['Cf']})")

# --- CONSOLIDATED CALCULATION ENGINE ---
# Calculate valid total distance (D_t - D_x)
effective_distance = distance_traveled - distance_exempted

if total_co2_tons > 0 and effective_distance > 0 and capacity > 0:
    
    # Process Voyage and General Deductions (FC_voyage & standard corrections) 
    # Applying standard global tanker carbon conversion (3.114) for the general voyage exemptions
    total_deductions_tons = fc_voyage_tons + fc_operational_deductions
    if total_deductions_tons > 0:
        co2_deductions = total_deductions_tons * 3.114
        total_co2_tons = max(0.0, total_co2_tons - co2_deductions)
        
    total_co2_grams = total_co2_tons * 1e6  # Convert total metric tons of CO2 to grams
    ton_miles = capacity * effective_distance
    
    attained_cii = total_co2_grams / ton_miles
    
    st.markdown("---")
    st.subheader("Attained vs Required CII Performance")
    st.write(f"**Effective Distance (D_t - D_x):** {effective_distance:.1f} Nautical Miles")
    st.write(f"**Total Aggregated Corrected Emissions:** {total_co2_tons:.2f} Metric Tons of CO₂")
    st.write(f"**Your Attained CII:** {attained_cii:.4f} g CO₂/ton-mile")
    st.write(f"**Required CII for {selected_year}:** {CIIref_y:.4f} g CO₂/ton-mile")

    # --- DETERMINING THE CII BAND RATING ---
    if attained_cii <= superior:
        rating = "A"
        color = "#2E7D32"  # Dark Green
        description = "Superior performance"
    elif attained_cii <= lower:
        rating = "B"
        color = "#4CAF50"  # Light Green
        description = "Good performance"
    elif attained_cii <= upper:
        rating = "C"
        color = "#FBC02D"  # Amber/Yellow
        description = "Standard compliance"
    elif attained_cii <= inferior:
        rating = "D"
        color = "#F57C00"  # Orange
        description = "Minor inferior performance (Corrective Action Plan may be required if consecutive)"
    else:
        rating = "E"
        color = "#D32F2F"  # Red
        description = "Inferior performance (SEEMP Plan must be updated with corrective actions)"

    # Display Badge
    st.markdown("---")
    st.subheader("Final Operational CII Rating")
    st.markdown(
        f"""
        <div style="
            background-color: {color}; 
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
            color: white;
        ">
            <h1 style="margin: 0; font-size: 72px; font-weight: bold; color: white;">{rating}</h1>
            <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: 500;">Rating: {rating} ({description})</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
elif distance_traveled > 0 and effective_distance <= 0:
    st.error("Error: Exempted distance (D_x) cannot be greater than or equal to total distance traveled (D_t).")