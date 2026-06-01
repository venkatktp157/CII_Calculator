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

# # === Authentication ===
# authenticator = load_authenticator()
# name, auth_status, username = authenticator.login('Login', 'main')
# logger = setup_logger()

# if auth_status:
#     # === Password Reset Check ===
#     if authenticator.credentials["usernames"][username].get("password_reset", False):
#         st.warning("🔒 You are required to reset your password.")
#         if st.button("Change Password"):
#             authenticator.reset_password(username)
#             st.success("✅ Password updated. Please log in again.")
#             st.stop()
    
#     authenticator.logout('Logout', 'main')

#     st.write(f"Welcome *{name}* 👋")
#     logger.info(f"User {username} logged in successfully")

st.markdown(
    """
    <div style="text-align: center;">
        <h1 style="color: blue; font-size: 48px;">CARBON INTENSITY INDICATOR (CII)</h1>
        <h3 style="color: green; font-size: 20px;">
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
        <h3 style="color: red; font-size: 20px;">
            It was officially adopted by the Marine Environment Protection Committee (MEPC) during its 76th session (MEPC 76) 
            in June 2021 under Resolution MEPC.328(76). The regulation is set to be implemented starting from January 1, 2023, 
            with the first annual reporting due by March 31, 2024. The CII regulation is part of the International Maritime Organization's (IMO)
            broader strategy to reduce greenhouse gas emissions from ships and combat climate change.
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)

#ANNEX 15 RESOLUTION MEPC.353(78) (adopted on 10 June 2022) 2022 GUIDELINES ON THE REFERENCE LINES FOR 
#USE WITH OPERATIONAL CARBON INTENSITY INDICATORS (CII REFERENCE LINES GUIDELINES, G2) 
#MEPC 78/17/Add.1 Annex 15, page 4 
#Parameters for determining the 2019 ship type specific reference lines 
# List of ship types

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

#2022 GUIDELINES ON THE OPERATIONAL CARBON INTENSITY RATING OF SHIPS (CII RATING GUIDELINES, G4) 
#ANNEX 16 RESOLUTION MEPC.354(78) (adopted on 10 June 2022) 
#MEPC 78/17/Add/1 Annex 16, page 6 
# dd vectors for determining the rating boundaries of ship types 

# 2. Boundary data dictionary (Using simple mapping logic below)
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
# ----------------------------------

#Reduction factors for the required annual operational CII of ship  types.
#Reduction factor (Z%) for the CII relative to the 2019 reference line
#AMENDMENTS TO THE 2021 GUIDELINES ON THE OPERATIONAL CARBON INTENSITY REDUCTION FACTORS 
#RELATIVE TO REFERENCE LINES (CII REDUCTION  FACTORS GUIDELINES, G3) 
#RESOLUTION MEPC.400(83) (adopted on 11 April 2025), MEPC 83/17/Add.1 Annex 4, page 2 

# Initial Calculations
CIIref = 0.0
CIIref_y = 0.0

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

    # -----------------------------
    # Dynamic Mapping to Boundary Vector
    # -----------------------------
    wd_key = ship_type  # Default fallback mapping
    
    # Handle the exceptions where naming shifts based on size thresholds
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

    # Fetch the correct vector safely
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

#2018 GUIDELINES ON THE METHOD OF CALCULATION OF THE ATTAINED ENERGY EFFICIENCY DESIGN INDEX (EEDI) 
# FOR NEW SHIPS 
#ANNEX 5 RESOLUTION MEPC.308(73) (adopted on 26 October 2018)
#MEPC 73/19/Add.1 Annex 5, page 5 & 6

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

# --- FUEL CONSUMPTION SECTION ---
st.subheader("Attained CII Calculation Inputs")

# Create two columns for clean layout
col1, col2 = st.columns(2)

with col1:
    selected_fuel = st.selectbox("Select Fuel Type Used:", list(fuel_data.keys()))
    fuel_cf = fuel_data[selected_fuel]["Cf"]
    st.caption(f"IMO $C_F$ Factor: **{fuel_cf:.3f}** t-CO₂/t-Fuel")

with col2:
    fuel_consumed = st.number_input(
        "Enter Total Annual Fuel Consumed (Metric Tons):", 
        min_value=0.0, 
        step=0.1
    )
    distance_traveled = st.number_input(
        "Enter Total Distance Traveled (Nautical Miles):", 
        min_value=0.1, 
        step=0.1
    )

# Calculate Attained CII if capacity and inputs are provided
if fuel_consumed > 0 and distance_traveled > 0 and capacity > 0:
    # CO2 Emitted = Fuel * Cf
    total_co2_grams = fuel_consumed * fuel_cf * 1e6  # Converting tons to grams
    ton_miles = capacity * distance_traveled
    
    attained_cii = total_co2_grams / ton_miles
    
    st.markdown("---")
    st.subheader("Attained vs Required CII Performance")
    st.write(f"**Your Attained CII:** {attained_cii:.4f} g CO₂/ton-mile")
    st.write(f"**Required CII for {selected_year}:** {CIIref_y:.4f} g CO₂/ton-mile")

# Assuming you have already calculated:
# - attained_cii (g CO2 / ton-mile)
# - superior, lower, upper, inferior (the 4 boundary thresholds)

if fuel_consumed > 0 and distance_traveled > 0 and capacity > 0:
    
    # 1. Determine Rating and Color Theme
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

    # 2. Display the Custom Visual Rating Badge
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