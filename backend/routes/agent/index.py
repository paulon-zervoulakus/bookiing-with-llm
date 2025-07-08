from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.langgraph.multi_graph_agent.graph_main import build_main_graph, update_user_info
from backend.langgraph.multi_graph_agent.llm_setup import config
from backend.utils.authenticationUtils import AuthUser, get_current_user


graph = build_main_graph()

router = APIRouter(prefix="/api/bot", tags=["agent"])

class ChatRequest(BaseModel):
    query: str

@router.post("/agentic")
async def post_llm_query(
    req: ChatRequest,
    thread_id: str = "default-thread",
    current_user: AuthUser = Depends(get_current_user),
):
    update_user_info(current_user.name, current_user.email)
    state = {
        # "messages": [],
        # "booking_info": {"name":"", "email": ""},
        "input_message": req.query,
        "human_inquiry": "",
        "chunk_answer_from_inquiry": "",
        "booking_status": "",
        "intent": []
    }

    response = await graph.ainvoke(state, config)
    return {"ai_response":response["messages"], "booking_status":response["booking_status"]}