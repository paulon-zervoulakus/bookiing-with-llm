from datetime import datetime
from json import JSONDecodeError
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from backend.langgraph.multi_graph_agent.states import SharedState
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer, base_llm

def prompt_modifier():
    return f"""
Your task is to analyze the user's question and provide a comprehensive, natural response.
You will use the "chunk_answer_from_inquiry" for a factual base and relevant information.

🎯 YOUR TASK:
1. **Directly answer the user's question** in a clear and relevant way
2. The factual information is provided in "chunk_answer_from_inquiry".
3. If the question is vague, offer helpful clarification or guidance

📌 RESPONSE RULES:
- Be warm, professional, and helpful — but concise
- If the user's name is available, greet them naturally once
- Avoid filler or irrelevant general advice
- Do not repeat the question
- Avoid paragraphs of general info unless they help the question

🛑 NEVER do the following:
- Avoid halucinating responses
- Return long-winded responses with generic advice
- Say "I hope this finds you well"

🤖 Refer to yourself as: Travis (your Agentic Assistant AI)

✅ Output a natural-sounding, complete response that **answers the user's question directly** and optionally follows up with help if needed.
"""

async def collate_end_inquiry(state: SharedState) -> SharedState:
    """Final node that generates AI response based on all processed information"""
    print(f"\n===== collate_end_inquiry =====")

    try:
        # Generate the final AI response
        print(f"============================= before llm: collate_end_inquiry")
        start_time = datetime.now()
        response = await agent_summary_builder.ainvoke({"input": state["human_inquiry"]})
        print(f"\n===== {response}")
        # With this:
        if response["messages"] and len(response["messages"]) > 0:
            last_message = response["messages"][-1]
            if hasattr(last_message, 'content'):
                ai_content = last_message.content
            else:
                ai_content = str(last_message)
        else:
            ai_content = "Thank you for your message. I'm here to help with your Canadian immigration questions. How can I assist you today?"

        ai_message = AIMessage(content=ai_content)

        print(f"result_content: {response}")
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"============================= after llm: collate_end_inquiry - time: {elapsed:.3f}")

        return {
            **state,
            "messages": [ai_message]
        }
        
    except JSONDecodeError as e:
        # Fallback response in case of error
        print(f"\nSomething wen't wrong: {e.msg}")
        fallback_message = AIMessage(content=f"Thank you for your message. I'm here to help with your Canadian immigration questions. How can I assist you today?")
        
        return {
            **state,
            "messages": [fallback_message]
        }


# def rag_query_tool(state: SharedState)-> str:
#     """Node that executes RAG query using the existing tool"""
#     input_message = state.get("human_inquiry", "").strip("?").strip("!").strip(".").strip("")
#
#     if not input_message:
#         return "No inquiry to process"
#
#     try:
#         # Call the existing rag_query_vector tool directly
#         # rag_results = await rag_query_vector(human_inquiry)
#
#         model = SentenceTransformer("all-MiniLM-L6-v2")  # Removed await - not needed
#         question_embedding = model.encode([input_message]).tolist()[0]
#         collection = get_collection()
#         results = collection.query(
#             query_embeddings=[question_embedding],
#             n_results=3
#         )
#         relevant_chunks = results["documents"][0]
#
#         return relevant_chunks
#
#     except JSONDecodeError as e:
#         print(f"\nSomething wen't wrong: {e.msg}")
#         return ""


prompt = PromptTemplate(
    input_variables=["message"],
    template=prompt_modifier() + "\n\nInput: {message}\n→"
)
# Create the modern agent using LangGraph
agent_summary_builder = create_react_agent(
    model=base_llm,
    tools=[],
    prompt=prompt,
    checkpointer=checkpointer
)
graph_summary_inquiry = (
    StateGraph(SharedState)
    .add_node("collate_end_inquiry", collate_end_inquiry)
    .set_entry_point("collate_end_inquiry")
    .compile(checkpointer=checkpointer)
)