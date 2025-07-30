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

CLASSIFICATION:
  1. GENERAL KNOWLEDGE: Basic conceptual questions about immigration processes, general explanations, or "what is" type questions.
  2. SPECIFIC FACTS: Questions about requirements, documents, processing times, fees, eligibility criteria, specific procedures, or any detailed factual information.

For GENERAL KNOWLEDGE questions:
- Return the query format: "GENERAL: [cleaned and rephrased for clear question]"

For SPECIFIC FACTS questions:
- Return the query format: "FACTS_NEEDED: [cleaned and rephrased for clear question]"

Examples:
- Input: "What is Express Entry?"
  → "GENERAL: explanation of Express Entry immigration system"
  
- Input: "What documents do I need for a Canadian work visa?"
  → "FACTS_NEEDED: required documents for Canadian work visa application"
  
- Input: "What are the requirements for migration to Canada?"
  → "FACTS_NEEDED: requirements for migration to Canada"
  
- Input: "What is the current processing time for Express Entry applications?"
  → "FACTS_NEEDED: current processing time for Express Entry applications in Canada"
  
- Input: "What is the minimum points needed for Express Entry?"
  → "FACTS_NEEDED: minimum points threshold for Express Entry Canada"
  
- Input: "Do I need to pass a language test for immigration?"
  → "FACTS_NEEDED: language test requirements for Canadian immigration"
    
- Input: "What is the capital of Canada?"
  → "GENERAL: What is the capital of Canada?"s
  
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
            **state,
            "inquiry_answer": "No inquiry to process"
        }

    try:
        collection = get_collection()
        
        # DEBUG: Check collection info
        print(f"Collection count: {collection.count()}")
        print(f"Collection name: {collection.name}")
        
        # DEBUG: Get a few sample documents to see what's in there
        sample_results = collection.peek(limit=3)
        print(f"Sample documents: {sample_results}")
        
        if collection.count() == 0:
            print("❌ ERROR: Vector database is empty!")
            return {
                **state,
                "chunk_answer_from_inquiry": ["No documents found in database"]
            }
        
        # Continue with your query
        model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
        question_embedding = model.encode([human_inquiry_value]).tolist()[0]
        
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=3
        )
        
        # DEBUG: Check what the query returned
        print(f"Query results structure: {results.keys()}")
        print(f"Documents found: {len(results.get('documents', [[]])[0])}")
        print(f"Distances: {results.get('distances', [[]])[0]}")
        
        relevant_chunks = results["documents"][0]
        print(f"\n\trelevant_chunks raw: {human_inquiry_value} - {relevant_chunks}")
        
        if not relevant_chunks:
            print("❌ No relevant documents found for this query")
            return {
                **state,
                "chunk_answer_from_inquiry": ["No relevant documents found"]
            }
        
        return {
            **state,
            "chunk_answer_from_inquiry": relevant_chunks
        }

    except Exception as e:
        print(f"\n❌ Error in RAG query: {str(e)}")
        return {
            **state,
            "chunk_answer_from_inquiry": [f"Error: {str(e)}"]
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
- Synthesize and shorten the response

🛑 NEVER do the following:
- Avoid halucinating responses
- Return long-winded responses with generic advice
- Say "I hope this finds you well"

🤖 Refer to yourself as: Travis (your Agentic Assistant AI)

✅ Output a natural-sounding, synthesize and short response that **answers the user's question directly**.
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
- If the user's name is available, greet them naturally once
- Avoid filler or irrelevant general advice
- Do not repeat the question
- Avoid paragraphs of general info unless they help the question
- Synthesize and shorten the response

🛑 NEVER do the following:
- Avoid halucinating responses
- Return long-winded responses with generic advice
- Say "I hope this finds you well"

🤖 Refer to yourself as: Travis (your Agentic Assistant AI)

✅ Output a natural-sounding, synthesize and short response that **answers the user's question directly**.
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
            "messages": current_messages,
            "chunk_answer_from_inquiry": chunk_data
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

def build_graph_human_question():
    return StateGraph(SharedState)\
        .add_node("node_human_question_scraper", node_human_question_scraper)\
        .add_node("node_rag_query", node_rag_query)\
        .add_node("node_summarize_response", node_summarize_response)\
        .add_node("end", lambda state: state)\
        .add_conditional_edges(
            "node_human_question_scraper",
            route_after_scraper,
            {
                "node_summarize_response":"node_summarize_response",
                "node_rag_query":"node_rag_query",
                "end":"end"
            }
        )\
        .add_edge("node_rag_query","node_summarize_response")\
        .set_entry_point("node_human_question_scraper")\
        .compile(checkpointer=checkpointer)