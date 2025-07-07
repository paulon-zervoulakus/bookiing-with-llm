from json import JSONDecodeError
from langgraph.graph import StateGraph
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from sentence_transformers import SentenceTransformer
from backend.langgraph.multi_graph_agent.states import SharedState
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer, config, base_llm
from backend.database import get_collection
from backend.database import get_collection
from datetime import datetime

async def node_human_question_scraper(state: SharedState) -> SharedState:
    print(f"\n=============================  node_human_question_scraper")
    print(f"\nTime check\n - before llm: node_human_question_scraper")
    start_time = datetime.now()

    system_msg = SystemMessage(content="""
You are a Migration Inquiry Analyzer with RAG decision capabilities.

FIRST, identify whether the user's message contains a question or inquiry about immigration or migration to Canada.

If NO inquiry is detected:
- Respond with an empty string: ""

If YES, an inquiry is detected:
- CLASSIFY the question as either:
  1. GENERAL KNOWLEDGE: Questions that can be answered with general knowledge about immigration processes, requirements, or procedures.
  2. SPECIFIC FACTS: Questions that require specific, up-to-date factual information, statistics, or time-sensitive details.

For GENERAL KNOWLEDGE questions:
- Return the query format: "GENERAL: [cleaned and rephrased for clear question]"

For SPECIFIC FACTS questions:
- Return the query format: "FACTS_NEEDED: [cleaned and rephrased for clear question]"

Examples:
- Input: "What documents do I need for a Canadian work visa?"
  → "GENERAL: required documents for Canadian work visa application"
  
- Input: "What is the current processing time for Express Entry applications?"
  → "FACTS_NEEDED: current processing time for Express Entry applications in Canada"
  
- Input: "What is the minimum points needed for Express Entry?"
  → "FACTS_NEEDED: minimum points threshold for Express Entry Canada"
  
- Input: "Do I need to pass a language test for immigration?"
  → "GENERAL: language test requirements for Canadian immigration"
    
- Input: "What is the center of canada?"
  → "GENERAL: What is the capital of Canada?"
  
- Input: "Hello I'm Alice, just saying hi"
  → ""
"""
)
    input_message = state.get("input_message").replace(":"," ")
    result = await base_llm.ainvoke([
        system_msg,
        HumanMessage(content=input_message)
    ])
    
    try:
        human_inquiry = result.content
    except Exception:
        human_inquiry = ""

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after llm: node_human_question_scraper - time: {elapsed:.3f}")
    # Set last_node before returning
    return { "human_inquiry": human_inquiry }

async def node_rag_query(state: SharedState) -> SharedState:
    """Node that executes RAG query using the existing tool"""
    print(f"\n-> node_rag_query")
    human_inquiry_list = state.get("human_inquiry", "").split(":")
    human_inquiry_value = human_inquiry_list[1].strip() if len(human_inquiry_list) > 1 else ""

    if not human_inquiry_value:
        return {
            "inquiry_answer": ToolMessage(content="No inquiry to process")
        }

    try:
        # Call the existing rag_query_vector tool directly
        # rag_results = await rag_query_vector(human_inquiry)

        model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
        question_embedding = model.encode([human_inquiry_value]).tolist()[0]
        collection = get_collection()
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=3
        )
        relevant_chunks = results["documents"][0]

        return {
            **state,
            "chunk_answer_from_inquiry": relevant_chunks
        }

    except JSONDecodeError as e:
        print(f"\nSomething wen't wrong: {e.msg}")
        return {
            **state,
            "chunk_answer_from_inquiry": ""
        }


def prompt_modifier(inquery_type):
    if inquery_type == "GENERAL":
        to_return = f"""
Your task is to analyze the user's question and provide a comprehensive, natural response.

🎯 YOUR TASK:
1. **Directly answer the user's question** in a clear and relevant way
3. If the question is vague, offer helpful clarification or guidance

📌 RESPONSE RULES:
- Be warm, professional, and helpful — but concise
- If the user's name is available, greet them naturally once
- Avoid filler or irrelevant general advice
- Do not repeat the question

🛑 NEVER do the following:
- Avoid halucinating responses
- Return long-winded responses with generic advice
- Say "I hope this finds you well"

🤖 Refer to yourself as: Travis (your Agentic Assistant AI)

✅ Output a natural-sounding, complete response that **answers the user's question directly** and optionally follows up with help if needed.
"""

    elif inquery_type == "FACTS_NEEDED":
        to_return = f"""
Your task is to analyze the user's question and provide a comprehensive, natural response.
You will use the "RELEVANT_INFORMATION" for a factual base and relevant information if available.

🎯 YOUR TASK:
1. **Directly answer the user's question** in a clear and relevant way
2. The factual information is provided in "RELEVANT_INFORMATION".
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

    return to_return

async def node_summarize_response(state: SharedState) -> SharedState:
    """Node that executes RAG query using the existing tool"""
    print(f"\n-> node_summarize_response")
    human_inquiry_list = state.get("human_inquiry", "").split(":")
    human_inquiry_type = human_inquiry_list[0].strip() if len(human_inquiry_list) > 1 else "GENERAL"
    human_inquiry_value = human_inquiry_list[1].strip() if len(human_inquiry_list) > 1 else ""
    if not human_inquiry_value:
        return {
            **state,
            "inquiry_answer": ToolMessage(content="No inquiry to process")
        }
    # Get the RAG results if they exist
    chunk_data = state.get("chunk_answer_from_inquiry", [])
    formatted_chunks = "\n\nRELEVANT_INFORMATION:\n".join(chunk_data) if isinstance(chunk_data, list) else "\n\nRELEVANT_INFORMATION:\n".join(str(chunk_data))

    system_content = prompt_modifier(human_inquiry_type)
    if formatted_chunks:
        system_content += "\n\n" + formatted_chunks

    system_msg = SystemMessage(content=system_content)
    print(f"\nTime check\n - before llm: node_summarize_response")
    start_time = datetime.now()

    result = await base_llm.ainvoke([
        system_msg,
        HumanMessage(content=human_inquiry_value)
    ])
    try:
        # Create a message object with the response
        ai_message = AIMessage(content=result.content)

        print(f"ai_message: {ai_message}")
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nTime check\n - after llm: node_summarize_response - time: {elapsed:.3f}")

        current_messages = state.get("messages", []) + [ai_message]
        return {
            **state,
            "messages": current_messages
        }
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Fallback response
        fallback_message = AIMessage(
            content="I apologize, but I wasn't able to process the information properly. Could you please rephrase your question?")
        current_messages = state.get("messages", []) + [fallback_message]

        return {
            **state,
            "messages": current_messages
        }


def route_after_scraper(state: SharedState) -> str:
    if state.get("human_inquiry"):
        human_inquiry_split = state.get("human_inquiry").split(":")
        if human_inquiry_split[0].strip() == "GENERAL":
            return "node_summarize_response"
        elif human_inquiry_split[0].strip() == "FACTS_NEEDED":
            return "node_rag_query"
        else:
            return "end"
    else:
        return "end"


graph_human_question = (
    StateGraph(SharedState)
    .add_node("node_human_question_scraper", node_human_question_scraper)
    .add_node("node_rag_query", node_rag_query)
    .add_node("node_summarize_response", node_summarize_response)
    .add_node("end", lambda state: state)
    .add_conditional_edges(
        "node_human_question_scraper",
        route_after_scraper,
        {
            "node_summarize_response":"node_summarize_response",
            "node_rag_query":"node_rag_query",
            "end":"end"
        }
    )
    .add_edge("node_rag_query","node_summarize_response")
    .set_entry_point("node_human_question_scraper")
    .compile(checkpointer=checkpointer)
)