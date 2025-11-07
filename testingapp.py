# app.py (Excerpt showing the new Gemini integration)

# ... (Existing imports and functions up to 'def parse_and_add_data') ...

# ---------------------------
# GEMINI AI TOOL DEFINITIONS
# ---------------------------

# Estimated Consumption Rates (for conversion from durations, based on typical appliance power)
# These are used when the user provides detailed activity text.
AC_KWH = 1.5 
HEATER_KWH = 2.0
MICROWAVE_KWH = 0.8
INDUCTION_STOVE_KWH = 2.0
FAN_KWH = 0.05
LIGHT_KWH = 0.01

# Assuming Water Pump Motor runs to supply 300L/hr of water
WATER_PUMP_LPH = 300

def returnPrompt(INPUT):
    # NOTE: Cleaned up the prompt slightly for clarity and structure, 
    # but kept all keys and the core instruction for JSON output.
    return f"""
    You are an expert data extractor. From the user's input describing their daily activities, extract the following data.
    
    If the unit is not explicitly hours but duration is given (e.g., "30 minutes"), convert it to hours in the appropriate '... (In Hours)' key.
    
    If you can't obtain data for any of the keys, fill in 0 for that value.
    
    Keys to extract:
    1. Number of ACs: `num_acs`
    2. Duration running of each AC (In Hours): `duration_ac_hours`
    3. Number of Heaters: `num_heaters`
    4. Duration running of each heater (In Hours): `duration_heater_hours`
    5. Duration of food cooked by Microwave (In Hours): `duration_microwave_hours`
    6. Duration of food cooked by induction stoves (In hours): `duration_induction_stove_hours`
    7. Duration of water pump motors running (motors) (In hours): `duration_water_pump_motors`
    8. Number of Fans: `num_fans`
    9. Number of Lights: `num_lights`
    
    Provide the output in a single JSON object (with no other text, commentary, or markdown blocks) using only the snake_case keys provided below:
    
    {{
    "num_acs": <value>,
    "duration_ac_hours": <value>,
    "num_heaters": <value>,
    "duration_heater_hours": <value>,
    "duration_microwave_hours": <value>,
    "duration_induction_stove_hours": <value>,
    "duration_water_pump_motors": <value>,
    "num_fans": <value>,
    "num_lights": <value>
    }}
    
    The user input is: "{INPUT}"
    """

def ai_estimate_and_add_data(text_input: str, user_id: int, current_date: date, hh_size: int, conn):
    """
    Uses the Gemini API to get structured usage estimates, calculates total usage, 
    and saves it to the database.
    """
    
    if not text_input or text_input.strip() == "":
        st.error("Please provide a description of your activities for the AI to estimate.")
        return False
    
    try:
        # 1. Generate Content (using the function defined by the user)
        prompt = returnPrompt(text_input)
        
        # Use a model that supports function calling or direct JSON output well
        response = model.generate_content(
            prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # 2. Parse JSON response
        data = json.loads(response.text.strip())
        
    except Exception as e:
        st.error(f"AI estimation failed or response format was incorrect: {e}. Raw response: {response.text if 'response' in locals() else 'N/A'}")
        return False

    try:
        # 3. Calculate Total Electricity (kWh)
        total_elec_kWh = 0.0
        
        # AC (num_acs * duration * kwh_per_ac)
        total_elec_kWh += data.get('num_acs', 0) * data.get('duration_ac_hours', 0) * AC_KWH
        
        # Heaters (num_heaters * duration * kwh_per_heater)
        total_elec_kWh += data.get('num_heaters', 0) * data.get('duration_heater_hours', 0) * HEATER_KWH
        
        # Appliances
        total_elec_kWh += data.get('duration_microwave_hours', 0) * MICROWAVE_KWH
        total_elec_kWh += data.get('duration_induction_stove_hours', 0) * INDUCTION_STOVE_KWH
        
        # Motors (This is a major consumer, use it for base electricity)
        motor_duration = data.get('duration_water_pump_motors', 0)
        total_elec_kWh += motor_duration * WATER_PUMP_LPH / WATER_PUMP_LPH # assuming 1kW pump, which simplifies. Let's use 1kW for simplicity or WATER_PUMP_LPH * KWH_PER_LITER_WATER_PUMP 
        
        # Ambient usage (Fans and lights) - assume fans/lights are per person or per room, simplify here by taking fixed units.
        # This part is highly variable, but for estimation:
        total_elec_kWh += data.get('num_fans', 0) * FAN_KWH * 8 # 8 hours run time
        total_elec_kWh += data.get('num_lights', 0) * LIGHT_KWH * 8 # 8 hours run time

        # 4. Calculate Total Water (Liters)
        # Assuming water use is primarily from the pump running time.
        # If the pump ran for X hours, it delivered X * WATER_PUMP_LPH
        # We add a base human usage estimate (50L per person for flushing, etc.)
        total_water_L = int(motor_duration * WATER_PUMP_LPH) + (hh_size * 50) 
        
        if total_elec_kWh <= 0:
            total_elec_kWh = 0.1 # Minimum usage to prevent 0
        
        # 5. Insert the estimated usage
        saved = add_usage(conn, user_id, current_date.strftime(DATE_FMT), 
                          total_elec_kWh, total_water_L, hh_size)
        
        if saved:
            return True, total_elec_kWh, total_water_L
        else:
            return False, None, None

    except Exception as e:
        st.error(f"Error during calculation or data insertion: {e}")
        return False, None, None

# ... (rest of the code - UI layout, etc.) ...


# MAIN DASHBOARD CONTENT

# ... (Existing code for titles, filters, etc.) ...

# ---------------------------
# CONVERSATIONAL INPUT SECTION
# ---------------------------

# ... (Existing 'Quick Data Entry & Analysis (Today)' section) ...

st.markdown("---") 

# ---------------------------
# AI ESTIMATION FROM DESCRIPTION
# ---------------------------
st.header("🤖 AI Usage Estimator (Activity Log)")
st.caption("Describe your day's activities (e.g., 'I ran two ACs for 4 hours, watched TV, and used the microwave for 15 minutes') to get a usage estimate.")

col_ai_input, col_ai_date = st.columns([3, 1])

with col_ai_input:
    ai_input = st.text_area(
        "Describe your daily activities:", 
        value="", 
        placeholder="e.g., I had the AC on in my room for 5 hours, cooked food on the induction stove for 30 minutes, and the water pump ran for 15 minutes.",
        key="ai_entry",
        height=100
    )
with col_ai_date:
    ai_date = st.date_input("For Date:", date.today(), key="ai_date")

ai_button = st.button("Estimate & Save via AI", type="secondary")

if ai_button and ai_input:
    
    # 1. Get Prediction BEFORE new data is added
    # (Existing prediction logic copied or refactored here to avoid repetition)
    
    # Simple prediction placeholder (replace with real logic from above if needed)
    df_user_temp = df_all[df_all["username"] == st.session_state.current_user]
    pred_elec = 5.0 
    if not df_user_temp.empty:
        p, _ = fit_linear_trend(df_user_temp, "electricity_units")
        if p is not None:
            pred_elec = p
        
    # 2. Estimate and Save
    with st.spinner("🤖 AI analyzing your activity..."):
        saved, latest_elec, latest_water = ai_estimate_and_add_data(
            ai_input, 
            st.session_state.current_user_id, 
            ai_date, 
            st.session_state.household_size, 
            conn
        )
    
    if saved:
        st.success(f"AI Estimated and Saved! Electricity: **{latest_elec:.2f} kWh**, Water: **{int(latest_water)} L** for {ai_date.strftime(DATE_FMT)}.")
        
        # 3. Generate Suggestions based on the new entry and old prediction
        temp_latest_data = pd.DataFrame({
            'electricity_units': [latest_elec], 
            'water_liters': [latest_water], 
            'household_size': [st.session_state.household_size]
        })

        st.subheader("✨ Instant Suggestions (AI Estimate)")
        
        if pred_elec is not None:
            score = eco_score(latest_elec, pred_elec)
            st.write(f"EcoScore based on this AI estimate: **{score}/100**")
        
        suggestions = generate_suggestions(latest_elec, pred_elec, temp_latest_data)
        for s in suggestions:
            st.write(f"• {s}")
            
        # 4. Rerun to refresh the entire dashboard graphs with the new data
        st.rerun() 

st.markdown("---")
# ---------------------------
# END AI ESTIMATION SECTION
# ---------------------------

# ... (The rest of the dashboard code continues here, displaying charts, leaderboard, etc.) ...