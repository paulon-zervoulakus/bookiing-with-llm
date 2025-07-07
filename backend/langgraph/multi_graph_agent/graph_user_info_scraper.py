import json
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph
from backend.langgraph.multi_graph_agent.states import SharedState
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer, config, base_llm
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_core.output_parsers import JsonOutputParser

def prompt_modifier():
    return """
You are a STRICT Booking Information Extractor. You MUST follow these rules exactly:

CRITICAL RULES:
1. ONLY extract information that is EXPLICITLY stated in the user's message.
2. DO NOT invent, guess, or create any names or emails.
3. DO NOT use placeholders, examples, or fictional data.
4. If information is not explicitly provided, return the persistent booking info or null.

BOOKING EXTRACTION RULES:
- Name: Must be a proper full name explicitly stated (e.g., "My name is John Smith").
- Email: Must be a valid email address explicitly stated (e.g., "Contact me at john@email.com").
- Schedule Date: Accept both explicit dates (e.g., "August 15, 2020", "08/15/2020) or **natural date expressions** like:
  - "today"
  - "tomorrow"
  - "yesterday"
  - "next week"
  - "this weekend"
  - "next month"
  You MUST resolve these into proper date strings in the format MM/DD/YYYY **relative to the current date**.
- Schedule Time: Must be a specific time expression (e.g., "at 3:00 PM", "around 10 AM"). Convert to `HH:MM AM/PM` format.
- DO NOT extract: pronouns, usernames, partial info, or implied information.

RESPONSE FORMAT (JSON only, no explanations):
{{
  "name": "explicit_name_from_message_or_null",
  "email": "explicit_email_from_message_or_null",
  "schedule_date": "MM/DD/YYYY or null",
  "schedule_time": "HH:MM AM/PM or null"
}}"""

prompt = PromptTemplate(
    input_variables=["message"],
    template=prompt_modifier() + "\n\nInput: {message}\n→"
)
# chain = LLMChain(llm=base_llm, prompt=prompt)
intent_chain = prompt | base_llm | JsonOutputParser()

async def node_user_info_scraper(state: SharedState) -> SharedState:
    print(f"\n============================= node_user_info_scraper")

    existing_booking_info = state["booking_info"]  

    print(f"\nTime check\n - before llm: node_user_info_scraper")
    start_time = datetime.now()
    # result = await chain.ainvoke(state["input_message"])
    result = await intent_chain.ainvoke({"message": state["input_message"]})

    
    try:
        # print(f"\nuser_info before: {state['user_info']}")
        # extracted_info = json.loads(result["text"].strip())
        # print(f"\n====================ai_user_info_scraper:\nextracted_info: {extracted_info}")

        # Merge extracted info with existing info - only update non-null values
        updated_booking_info = existing_booking_info.copy() if existing_booking_info else {}

        for key, value in result.items():
            if value is not None:
                updated_booking_info[key] = value
        
        # print(f"user_info after merge: {updated_user_info}")
        
    except json.JSONDecodeError as e:
        print("JSON decode error, keeping existing user info: " + e.msg)        
        updated_booking_info = existing_booking_info if existing_booking_info else {}        

    print(f"\nBooking Info: {updated_booking_info}")
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after llm: node_user_info_scraper - time: {elapsed:.3f}")

    return {
        **state,
        "booking_info": updated_booking_info
    }


graph_user_info_scraper = (
    StateGraph(SharedState)
    .add_node("node_user_info_scraper", node_user_info_scraper)
    .set_entry_point("node_user_info_scraper")
    .compile(checkpointer=checkpointer)
)