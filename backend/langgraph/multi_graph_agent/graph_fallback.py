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
import re

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
    print(f"\n -> retrieve_conversation_history called with query: {query}")
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
        top_k = min(5, len(message_texts))
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
            result = "RELEVANT CONVERSATION HISTORY:\n\n" + "\n\n---\n\n".join(conversation_snippets)
            print(f"Retrieved history: {result[:200]}...")
            return result
        else:
            return "No relevant conversation history found."
            
    except Exception as e:
        print(f"Error retrieving conversation history: {e}")
        return "Error processing conversation history."

def detect_history_reference(message: str) -> bool:
    """
    Detect if the user is referring to previous conversation
    """
    # Convert to lowercase for case-insensitive matching
    message_lower = message.lower()
    
    # Patterns that indicate reference to previous conversation
    reference_patterns = [
        # Direct references
        r'\b(you said|you mentioned|you told me|you explained)\b',
        r'\b(mentioned earlier|said earlier|told me earlier)\b',
        r'\b(what about|tell me more about|elaborate on)\b',
        r'\b(that|this|it)\b.*\b(you mentioned|we discussed)\b',
        r'\b(earlier|before|previously|last time)\b',
        r'\b(continue|more details|more info|expand on)\b',
        r'\b(what did you say about|what was that about)\b',
        
        # Question words with reference context
        r'\b(what|how|why|when|where)\b.*\b(that|this|it)\b',
        r'\b(can you|could you)\b.*\b(tell me more|elaborate|explain more)\b',
        
        # Vague references that likely need context
        r'\b(that requirement|that process|that option|that method)\b',
        r'\b(those documents|those requirements|those steps)\b',
        r'\b(the one you|the thing you|the process you)\b'
    ]
    
    # Check if any pattern matches
    for pattern in reference_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False

async def node_build_fallback_with_history_logic(state: SharedState) -> SharedState:
    """Process fallback responses with history logic handled outside LLM"""
    print(f"\n============================= node_build_fallback_with_history_logic")

    print(f"\nTime check\n - before processing: node_build_fallback_with_history_logic")
    start_time = datetime.now()

    # Booking Information
    booking_info = state.get("booking_info", {})

    user_message = state.get("input_message", "")
    print(f"User message: {user_message}")
    
    # Detect if user is referring to previous conversation
    needs_history = detect_history_reference(user_message)
    print(f"Checking conversation: {needs_history}")
    
    # Retrieve history if needed
    history_context = ""
    if needs_history:
        print("Retrieving conversation history...")
        history_context = retrieve_conversation_history(state, user_message)
        print(f"History context retrieved: {len(history_context)} characters")
    
    # Build appropriate system prompt
    if needs_history and history_context and "No relevant conversation history found" not in history_context:
        system_prompt = f"""You are Travis, an AI assistant specializing in Canadian immigration.
        
The user or booking information is provided below if available:

{booking_info}  

The user is referring to something from our previous conversation. Here's the relevant context:

{history_context}

Based on this context, answer their current question naturally. Build on the previous information, provide clarification, or give additional details as appropriate. Don't just repeat what was said before - enhance and expand on it.

IMPORTANT: 
- Provide responses in plain text only, NEVER in HTML format
- Synthesize your response short, concise and informative
- Reference the previous conversation naturally in your response
"""
    else:
        system_prompt = f"""You are Travis, an AI assistant specializing in Canadian immigration.

The user or booking information is provided below if available:

{booking_info}  

IMPORTANT: 
- Provide responses in plain text only, NEVER in HTML format
- Answer questions directly and factually
- Synthesize your response short, concise and informative
- If you don't know the answer, say so rather than making something up
"""

    # Step 4: Call LLM with appropriate context
    response = await base_llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ])
    
    # Extract content from response
    if hasattr(response, 'content'):
        ai_content = response.content
    else:
        ai_content = "I'm here to help with your Canadian immigration questions. How can I assist you today?"
    
    ai_message = AIMessage(content=ai_content)
    current_messages = state.get("messages", []) + [ai_message]

    print(f"Final AI response: {ai_content[:100]}...")
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after processing: node_build_fallback_with_history_logic - time: {elapsed:.3f}")
    
    return {
        **state,
        "messages": current_messages
    }

# Update the graph to use the new node
graph_fallback = (
    StateGraph(SharedState)
    .add_node("node_build_fallback_with_history_logic", node_build_fallback_with_history_logic)
    .set_entry_point("node_build_fallback_with_history_logic")
    .compile(checkpointer=checkpointer)
)