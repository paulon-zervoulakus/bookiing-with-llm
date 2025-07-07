import pytest
from unittest.mock import AsyncMock, patch

from backend.langgraph.multi_graph_agent.graph_intent_classifier import node_intent_classifier, SharedState
from langgraph.graph import StateGraph
from backend.langgraph.multi_graph_agent.graph_intent_classifier import graph_intent_classifier
# Recompile the graph without a checkpointer for testing
test_graph_intent_classifier = (
    StateGraph(SharedState)
    .add_node("node_intent_classifier", node_intent_classifier)
    .set_entry_point("node_intent_classifier")
    .compile(checkpointer=None)
)
graph_intent_classifier = (
    StateGraph(SharedState)
    .add_node("node_intent_classifier", node_intent_classifier)
    .set_entry_point("node_intent_classifier")
    .compile(checkpointer=None)
)
@pytest.mark.asyncio
@patch("app.langgraph.multi_graph_agent.graph_intent_classifier.base_llm")
async def test_intent_classifier_identify(mock_base_llm):
    # Mock the LLM response
    mock_base_llm.ainvoke = AsyncMock(return_value=type("obj", (object,), {"content": '["identify"]'})())
    
    # Input state
    state = {"input_message": "Hi, I'm John"}
    
    # Run the graph
    result = await test_graph_intent_classifier.ainvoke(state)
    
    assert result["intent"] == ["identify"]

@pytest.mark.asyncio
# @patch("app.langgraph.multi_graph_agent.graph_intent_classifier.base_llm")
async def test_intent_classifier_multiple_intents():
    # mock_base_llm.ainvoke = AsyncMock(return_value=type("obj", (object,), {"content": '["identify", "bookings"]'})())
    state = {"input_message": "I want to move to Canada, what are my chances? Can you tell me how to book an appointment?"}
    result = await graph_intent_classifier.ainvoke(state)
    print(f"\nResult : {result}")
    # assert result["intent"] == ["identify", "bookings"]

@pytest.mark.asyncio
@patch("app.langgraph.multi_graph_agent.graph_intent_classifier.base_llm")
async def test_intent_classifier_fallback(mock_base_llm):
    mock_base_llm.ainvoke = AsyncMock(return_value=type("obj", (object,), {"content": 'not a json'})())
    state = {"input_message": "Random message"}
    result = await test_graph_intent_classifier.ainvoke(state)
    assert result["intent"] == ["fallback"]