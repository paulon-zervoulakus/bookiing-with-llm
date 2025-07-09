from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver 
from langgraph.prebuilt import create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableConfig
from backend.langgraph.multi_graph_agent.states import SharedState
from langchain.tools import Tool
from sentence_transformers import SentenceTransformer
from backend.database import get_collection

import os
os.environ["CHROMA_TELEMETRY"] = "false"
# Setup persistence
def setup_persistence(persistence_type="memory"):
    """Setup persistence based on type"""
    if persistence_type == "memory":
        return MemorySaver()
    elif persistence_type == "sqlite":
        return SqliteSaver.from_conn_string("checkpoints.db")
    else:
        raise ValueError("persistence_type must be 'memory' or 'sqlite'")

checkpointer = setup_persistence()
# base_llm = ChatOllama(model="mistral:7b", temperature=0)
base_llm = ChatOllama(model="llama3.1:8b", temperature=0)
# base_llm = ChatOllama(model="mistral:latest", temperature=0)
# base_llm = ChatOllama(model="llama3-groq-tool-use:8b", temperature=0)
config: RunnableConfig = {
    "configurable": {
        "thread_id": "example_pau_history",
        "session_id": "example_pau_history"
    }
}

# Your existing functions
def node_rag_query(state: SharedState) -> list:
    """This tool executes RAG query from the information regarding Canada citizenship."""
    input_message = state.get("input_message")

    if not input_message:
        return ["No inquiry to process"]

    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        question_embedding = model.encode([input_message]).tolist()[0]
        collection = get_collection()
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=3
        )
        relevant_chunks = results["documents"][0]
        print(f"\nRelevant Chunks: {relevant_chunks}")
        return relevant_chunks

    except Exception as e:
        print(f"\nSomething went wrong: {e}")
        return []

def extract_userinfo_from_booking_info(state: SharedState) -> dict:
    """This is a user information extractor from booking_info"""
    userinfo = {
        "name": state.get("booking_info",{}).get("name"),
        "email": state.get("booking_info",{}).get("email"),
        "schedule_date": state.get("booking_info",{}).get("schedule_date"),
        "schedule_time": state.get("booking_info",{}).get("schedule_time"),
    }
    if state["booking_info"]:
        return userinfo
    else:
        return {}

# Define tools
tools = [
    Tool(
        name="extract_userinfo_from_booking_info",
        func=extract_userinfo_from_booking_info,
        description="Extracts user information (name, email, schedule_date, schedule_time) from booking_info in the state."
    ),
    Tool(
        name="node_rag_query",
        func=node_rag_query,
        description="This tool executes RAG query from the information regarding Canada citizenship."
    ),
]

# Create the modern agent using LangGraph
# base_agent = create_react_agent(
#     model=base_llm,
#     tools=[tools],
#     checkpointer=checkpointer
# )
