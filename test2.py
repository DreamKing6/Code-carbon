import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

import google.generativeai as genai
genai.configure(api_key="AIzaSyBTcd_mND7B_WCb1lmpo5CBRXRXh19GPS0")
model = genai.GenerativeModel("gemini-2.5-flash")

#dataFetcher = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key="AIzaSyBTcd_mND7B_WCb1lmpo5CBRXRXh19GPS0", convert_system_message_to_human=True)
def returnPrompt(INPUT):
    return f"""Extract the following data from the given data if possible. 
Number of ACs
Duration running of each AC (In Hours)
Number of Heaters
Duration running of each heater (In Hours)
Duration of food cooked by Microwave (In Hours)
Duration of food cooked by induction stoves (In hours)
Duration of water pump motors running (motors) (In hours)
Number of Fans
Number of Lights

The user input is: "{INPUT}"

You also need to give me these datas separately, not derived from user input, but using your own sources. The datas are:
Common electricity consumption by ACs per hour in Kilo-watt-hours (kWh)
Common electricity consumption by Heaters per hour in Kilo-watt-hours (kWh)
Common electricity consumption by Microwaves per hour in Kilo-watt-hours (kWh)
Common electricity consumption by induction stoves in Kilo-watt-hours (kWh)
Common electricity consumption by water pump motors per hour in Kilo-watt-hours (kWh)
Common electricity consumption by a light in a hour in Kilo-watt-hours (kWh)
Average electricity usage of a house per month in Kilo-watt-hours (kWh)

If you can't obtain data for any of the keys mentioned above, fill in 0 for that value.
You MUST return the response to me in JSON format strictly, and the keys are in order as follows, with respect to the legend previously given.
num_of_acs
duration_acs
num_heaters
duration_heaters
avg_ec_cons_AC
avg_ec_cons_heaters
duration_MW
avg_ec_cons_MW
duration_induction_stove
avg_ec_cons_induction_stove
duration_water_pump_motors
avg_ec_cons_water_pump_motors
num_lights
num_fans
avg_ec_cons_lights
avg_ec_cons_fans
avg_ec_cons_house

Fill in datas in SI Units only unless explicitly said otherwise in the query for the respective data.
Do NOT add any extra text AT ALL, ONLY return the JSON with datas. If there's missing data, fill in 0 and return it. 
"""

# Initialize session state
if "username" not in st.session_state:
    st.session_state.username = None
if "user_data" not in st.session_state:
    st.session_state.user_data = pd.DataFrame(columns=["Date", "Consumption"])

# Username entry page
def username_page():
    st.title(" Enter Your Username")
    username = st.text_input("Username")
    if st.button("Continue"):
        if username.strip():
            st.session_state.username = username.strip()
            st.success(f"Welcome, {username}!")
        else:
            st.error("Please enter a valid username.")

# Main app for data entry and visualization
def data_entry_page():
    st.title(f" Electrical Consumption Tracker for {st.session_state.username}")

    st.subheader(" Enter Consumption Data")
    date = st.date_input("Date")
    textInput = st.text_area("Enter your daily activities! Describe how much ACs you have, and for how much times you run it, and the same with Heaters. Also input the duration of usage of microwaves, induction stoves, and water pump motors.")
    
    if st.button("Add Entry"):
        res = model.generate_content(returnPrompt(textInput))
        info = dict(eval((res.text).strip("```").lstrip("json")))
        #BaseEntry = pd.DataFrame([[date, info["avg_ec_cons_house"]]], columns=["Date", "Consumption"])
        #st.session_state.user_data = pd.concat([st.session_state.user_data, BaseEntry], ignore_index=True)
        AC=(info["num_of_acs"] * info["duration_acs"] * info["avg_ec_cons_AC"]) * 30
        Heaters=(info["num_heaters"] * info["duration_heaters"] * info["avg_ec_cons_heaters"]) * 30
        indcStv = (info["duration_induction_stove"] * info["avg_ec_cons_induction_stove"]) * 30
        MW = ((info["duration_MW"] * info["avg_ec_cons_MW"])) * 30
        WP = (info["duration_water_pump_motors"] * info["avg_ec_cons_water_pump_motors"]) * 30
        totalUnits = ((info["num_lights"] * info["avg_ec_cons_lights"]) + (info["num_fans"] * info["avg_ec_cons_fans"]) ) *24 * 30
        print(AC, Heaters, indcStv, MW, WP, totalUnits)
        new_entry = pd.DataFrame([[date, totalUnits+MW+WP+indcStv+Heaters+AC]], columns=["Date", "Consumption"])
        st.session_state.user_data = pd.concat([st.session_state.user_data, new_entry], ignore_index=True)
        st.success("Data added!")

    if not st.session_state.user_data.empty:
        st.subheader(" Consumption Graph")
        df = st.session_state.user_data.sort_values("Date")
        fig, ax = plt.subplots()
        ax.plot(df["Date"], df["Consumption"], marker="o", linestyle="--", color="blue")
        ax.plot(df["Date"], [info["avg_ec_cons_house"]]*len(df["Consumption"]), marker="*", linestyle="solid", color="red")
        ax.set_xlabel("Date")
        ax.set_ylabel("Consumption (kWh)")
        ax.set_title("Electrical Consumption Over Time")
        st.pyplot(fig)

# App flow
if st.session_state.username is None:
    username_page()
else:
    data_entry_page()