import streamlit
#from langchain_google_genai import ChatGoogleGenerativeAI
#from langchain.prompts import ChatPromptTemplate
#from langchain.output_parsers import JsonOutputParser
import json
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
avg_ec_cons_light
avg_ec_cons_fans
avg_ec_cons_house

Fill in datas in SI Units only unless explicitly said otherwise in the query for the respective data.
Do NOT add any extra text AT ALL, ONLY return the JSON with datas. If there's missing data, fill in 0 and return it. 
"""
#prompt = ChatPromptTemplate.from_messages([
#    ("system", returnPrompt("NULL")),
#    ("user", "{input}")
#])
#parser = JsonOutputParser()
#chain = prompt | dataFetcher 

streamlit.title("Electricity Watcher")
streamlit.header("Electricity Watcher")
streamlit.subheader("Monitor your electricity usage in your home and save MONEY!")
textInput = streamlit.text_area("Enter your daily activities! Describe how much ACs you have, and for how much times you run it, and the same with Heaters. Also input the duration of usage of microwaves, induction stoves, and water pump motors.")
if streamlit.button("Calculate ts"):
    res = model.generate_content(returnPrompt(textInput))
    streamlit.write(res.text)