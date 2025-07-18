""" Agent routes """
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.langgraph.multi_graph_agent.graph_main import build_main_graph
from backend.langgraph.multi_graph_agent.llm_setup import config
from backend.utils.authenticationUtils import AuthUser, get_current_user
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from backend.langgraph.multi_graph_agent.states import SharedState

graph = build_main_graph()

router = APIRouter(prefix="/api/bot", tags=["agent"])

class ChatRequest(BaseModel):
    query: str

def serialize_message(message):
    """Convert LangChain message objects to JSON-serializable format"""
    if isinstance(message, BaseMessage):
        return {
            "type": message.__class__.__name__,
            "content": message.content,
            "additional_kwargs": getattr(message, 'additional_kwargs', {}),
            "response_metadata": getattr(message, 'response_metadata', {})
        }
    return message

def serialize_any_value(value):
    """Recursively serialize any value that might contain messages"""
    if isinstance(value, BaseMessage):
        return serialize_message(value)
    elif isinstance(value, list):
        return [serialize_any_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: serialize_any_value(v) for k, v in value.items()}
    else:
        return value

def serialize_messages(messages):
    """Convert list of messages to JSON-serializable format"""
    if not messages:
        return []
    
    if isinstance(messages, list):
        return [serialize_message(msg) for msg in messages]
    else:
        return serialize_message(messages)

@router.post("/ai-stream")
async def stream_llm_query(
        req: ChatRequest,
        current_user: AuthUser = Depends(get_current_user)
):
    """Stream LLM query with streaming response"""
    # update_user_info(current_user.name, current_user.email)
    runnable_config: RunnableConfig ={
        "configurable": {
            "thread_id": current_user.sub,
            "session_id": current_user.sub,
            "user": {
                "name": current_user.name,
                "email": current_user.email,
            }
        }
    }
    init_state: SharedState = {
        "input_message": req.query,
        "human_inquiry": "",
        "chunk_answer_from_inquiry": "",
        "intent": []
    }

    async def llama_stream_response():
        """
        Args:
        """
        final_response = None
        async for chunk in graph.astream(init_state, runnable_config, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                if node_output:
                    result = {
                        'type': 'update',
                        'data': {
                            'node': node_name,
                            'short_message': node_output["short_message"] if "short_message" in node_output else "..."
                        }
                    }
                    # Properly format as SSE data
                    json_data = json.dumps(result)
                    yield f"data: {json_data}\n\n"

                    # Keep track of the final response
                    final_response = node_output

        booking_status = ""
        if final_response and "booking_status" in final_response:
            booking_status = final_response["booking_status"]

        # Serialize the final response messages
        ai_response = serialize_messages(final_response["messages"]) if final_response and "messages" in final_response else []

        # Yield the final result
        result = {
            "type": "final",
            "ai_response": ai_response,
            "booking_status": booking_status
        }
        json_data = json.dumps(result)
        yield f"data: {json_data}\n\n"

    return StreamingResponse(
        llama_stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.post("/agentic")
async def post_llm_query(
    req: ChatRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Post LLM query with streaming response"""
    # update_user_info(current_user.name, current_user.email)
    state = {
        "input_message": req.query,
        "human_inquiry": "",
        "chunk_answer_from_inquiry": "",
        "intent": []
    }

    async def generate_stream():
        """Generator function for streaming response"""
        final_response = None
        
        # Stream through the graph execution with different stream modes
        async for chunk in graph.astream(state, config, stream_mode="updates"):
            # Serialize the chunk data before sending
            serialized_chunk = {}
            for node_name, node_output in chunk.items():
                print(f"chunks: {node_name} - {node_output}\n")
                if node_output:
                    serialized_output = {}
                    for key, value in node_output.items():
                        if key == "messages":
                            serialized_output[key] = serialize_messages(value)
                        else:
                            serialized_output[key] = value
                    serialized_chunk[node_name] = serialized_output

            # Stream intermediate updates from each node
            yield f"data: {json.dumps({'type': 'update', 'data': serialized_chunk})}\n\n"
            
            # Keep track of the final response
            for node_name, node_output in chunk.items():
                if node_output:
                    final_response = node_output
        
        # Extract booking status from final response
        booking_status = ""
        if final_response and "booking_status" in final_response:
            booking_status = final_response["booking_status"]
        
        # Serialize the final response messages
        ai_response = serialize_messages(final_response["messages"]) if final_response and "messages" in final_response else []
        
        # Yield the final result
        result = {
            "type": "final",
            "ai_response": ai_response,
            "booking_status": booking_status
        }
        yield f"data: {json.dumps(result)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
            "Content-Type": "text/plain"
        }
    )