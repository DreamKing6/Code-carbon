import streamlit
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
dataFetcher = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key="AIzaSyBSQzLmawKZbc3H-msFrCkUgwifjRiJXk0")

prompt = ChatPromptTemplate.from_messages([
    ("system", """Extract the following data from the given data if possible
Number of ACs
Duration running of each AC
Number of Heaters
Duration running of each heater
Common electricity consumption by ACs per hour
Common electricity consumption by Heaters per hour
Duration of food cooked by Microwave
Common electricity consumption by Microwaves per hour
Duration of food cooked by induction stoves
Common electricity consumption by induction stoves
Duration of water pump motors running (motors)
Common electricity consumption by water pump motors per hour
Average electricity usage of a house per month

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
avg_ec_cons_house

Fill in datas in SI Units only unless explicitly said otherwise in the query for the respective data.
Do NOT add any extra text AT ALL, ONLY return the JSON with datas. If there's missing data, fill in 0 and return it. 
"""),
    ("user", "{input}")
])
parser = JsonOutputParser()
chain = prompt | dataFetcher | parser

streamlit.title("Electricity Watcher")
streamlit.header("Electricity Watcher")
streamlit.subheader("Monitor your electricity usage in your home and save MONEY!")
textInput = streamlit.text_area("Enter your daily activities! Describe how much ACs you have, and for how much times you run it, and the same with Heaters. Also input the duration of usage of microwaves, induction stoves, and water pump motors.")
if streamlit.button("Calculate ts"):
    res = chain.invoke({"input": textInput})
    print(res)
    streamlit.write(res)