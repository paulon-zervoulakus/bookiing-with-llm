from datetime import datetime 
from langgraph.graph import StateGraph
from langchain.schema import SystemMessage, AIMessage, HumanMessage
from langchain.agents import AgentExecutor
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer, base_llm
from backend.langgraph.multi_graph_agent.states import SharedState
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from datetime import datetime
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional

def prompt_modifier(state):
    return [SystemMessage(content=f"""
You are Travis, an AI assistant specializing in Canadian immigration.
    
    IMPORTANT: 
    - Provide responses in plain text only, NEVER in HTML format
    - Answer questions directly and factually
    - Be concise and helpful
    - If you don't know the answer, say so rather than making something up
    
    Respond to the user's query in a helpful, informative way.
    """)]

# Node: fallback response builder
async def node_build_fallback_message(state: SharedState) -> SharedState:
    print(f"\n============================= node_build_fallback_message")

    print(f"\nTime check\n - before llm: node_build_fallback_message")
    start_time = datetime.now()
    
    response = await base_llm.ainvoke([
        *prompt_modifier(state),
        HumanMessage(content=state.get("input_message", ""))
    ])
    
    print(f"result_content: {response}")
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after llm: node_build_fallback_message - time: {elapsed:.3f}")
    
    # Extract content from response
    if hasattr(response, 'content'):
        ai_content = response.content
    else:
        ai_content = "I'm here to help with your Canadian immigration questions. How can I assist you today?"
    
    return {
        **state,
        "messages": [AIMessage(content=ai_content)]
    }

# Create a conversation history retrieval tool
def retrieve_conversation_history(state: SharedState, query: str) -> str:
    """
    Tool that retrieves relevant parts of conversation history based on semantic similarity.
    
    Args:
        state: Current state with message history
        query: The search query to find relevant history
        
    Returns:
        String with relevant conversation history
    """
    print(f"\n -> retrieve_conversation_history")
    # Get all messages from state
    all_messages = state.get("messages", [])
    
    if not all_messages or len(all_messages) < 2:  # Need at least one exchange
        return "No significant conversation history found."
    
    try:
        # Format messages for embedding
        message_texts = []
        for msg in all_messages:
            if isinstance(msg, HumanMessage):
                message_texts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                message_texts.append(f"Assistant: {msg.content}")
        
        # Encode query and messages
        model = SentenceTransformer("paraphrase-MiniLM-L3-v2")
        query_embedding = model.encode([query]).tolist()[0]
        message_embeddings = model.encode(message_texts).tolist()
        
        # Find most similar messages
        similarities = []
        for i, embedding in enumerate(message_embeddings):
            # Calculate cosine similarity
            dot_product = sum(a*b for a, b in zip(query_embedding, embedding))
            magnitude1 = sum(a*a for a in query_embedding) ** 0.5
            magnitude2 = sum(b*b for b in embedding) ** 0.5
            similarity = dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 > 0 else 0
            similarities.append((i, similarity))
        
        # Sort by similarity (descending) and get top 3
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_k = min(3, len(message_texts))
        top_indices = [idx for idx, _ in similarities[:top_k]]
        
        # Format conversation snippets chronologically
        top_indices.sort()
        
        # Create context blocks with clear separators
        conversation_snippets = []
        current_block = []
        
        for i in top_indices:
            # If we're starting a new human-AI exchange
            if i > 0 and i % 2 == 0 and current_block:
                conversation_snippets.append("\n".join(current_block))
                current_block = []
                
            current_block.append(message_texts[i])
            
            # If this is an AI response, add it to the current block
            if i % 2 != 0 and current_block:
                conversation_snippets.append("\n".join(current_block))
                current_block = []
        
        # Add any remaining messages
        if current_block:
            conversation_snippets.append("\n".join(current_block))
            
        # Join all snippets with clear conversation separators
        if conversation_snippets:
            return "RELEVANT CONVERSATION HISTORY:\n\n" + "\n\n---\n\n".join(conversation_snippets)
        else:
            return "No relevant conversation history found."
            
    except Exception as e:
        print(f"Error retrieving conversation history: {e}")
        return "Error processing conversation history."

# Create a graph node that uses this tool
async def node_build_fallback_with_history_tool(state: SharedState) -> SharedState:
    """Process fallback responses with optional history retrieval"""
    print(f"\n============================= node_build_fallback_with_history_tool")

    # Define our history retrieval tool
    tools = [
        Tool(
            name="retrieve_conversation_history",
            func=lambda query: retrieve_conversation_history(state, query),
            description="""
Retrieves relevant parts of the conversation history based on a search query.
Use this tool ONLY when the user is clearly referring to something mentioned earlier in the conversation,
such as asking follow-up questions, referring to previous answers, or saying things like "tell me more about that".
"""
        )
    ]
    
    # Create the agent using the simple approach - let create_react_agent handle the prompt
    agent = create_react_agent(
        model=base_llm,
        tools=tools,
        state_schema=None,  # Let it use default state schema
        # Don't pass a custom prompt - let it use the default one
    )

    print(f"\nTime check\n - before llm: node_fallback_with_history_tool")
    start_time = datetime.now()
    
    # Invoke the agent directly with the proper input format
    # The create_react_agent expects messages in a specific format
    result = await agent.ainvoke({
        "messages": [
            SystemMessage(content="""
You are Travis, an AI assistant specializing in Canadian immigration.

FIRST, analyze if the user's query:
1. Is self-contained and can be answered directly
2. Refers to previous conversation and requires history context

IMPORTANT INSTRUCTIONS:
- If the query seems to reference previous conversation (e.g., "tell me more about that", "what about X?", "you mentioned Y earlier"), use the retrieve_conversation_history tool to get relevant context.
- If the query is self-contained, answer directly without retrieving history.
- When using history, incorporate it naturally in your response - don't just repeat it.
- Be concise, helpful and factual.
- Refer to yourself as Travis.

Example queries that NEED history:
- "Tell me more about that visa requirement you mentioned"
- "What did you say about language tests?"
- "Can you elaborate on the last point?"

Example queries that DON'T need history:
- "What are the requirements for Express Entry?"
- "How long does PR processing take?"
- "What's the capital of Canada?"
"""),
            HumanMessage(content=state.get("input_message", ""))
        ]
    })

    # Extract the AI message from the result
    if "messages" in result and result["messages"]:
        last_message = result["messages"][-1]
        if isinstance(last_message, AIMessage):
            ai_content = last_message.content
        else:
            ai_content = str(last_message)
    else:
        ai_content = "I'm here to help with your Canadian immigration questions. How can I assist you today?"
    
    # Create an AI message with the response
    ai_message = AIMessage(content=ai_content)
    
    # Update the state with the new message
    current_messages = state.get("messages", []) + [ai_message]

    print(f"state: {state}")
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after llm: node_fallback_with_history_tool - time: {elapsed:.3f}")
    return {
        **state,
        "messages": current_messages
    }

# # Create the modern agent using LangGraph
# agent_fallback_composer = create_react_agent(
#     model=base_llm,
#     tools=[],
#     state_schema=None,  # Use default state schema
#     # Don't pass checkpointer here - it's handled by the graph
# )

# Add this node to your graph
graph_fallback = (
    StateGraph(SharedState)
    .add_node("node_build_fallback_with_history_tool", node_build_fallback_with_history_tool)
    .set_entry_point("node_build_fallback_with_history_tool")
    .compile(checkpointer=checkpointer)
)