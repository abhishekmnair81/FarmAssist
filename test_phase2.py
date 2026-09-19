import asyncio
import os
import sys
import uuid
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.graph import workflow
from app.services.text_cleaner import clean_response_text

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

async def run_query(query: str):
    print(f"\n[{'='*40}]")
    print(f"User Query: {query}")
    print(f"[{'='*40}]")
    
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "checkpoints.sqlite")
    
    phone = "TEST_USER_" + str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        
        state_dict = {
            "messages": [HumanMessage(content=query)],
            "sender_phone": phone
        }
        
        state = await graph.ainvoke(state_dict, config=config)
        final_message = state["messages"][-1].content
        
        # Clean reasoning and special characters
        stripped = clean_response_text(final_message)
        print(f"Agent Response:\n{stripped}\n")

async def main():
    # Test 1: RAG Knowledge Base
    await run_query("How much subsidy do I get under PM-KUSUM for solar pumps?")
    
    # Test 2: Live Web Search
    await run_query("What is the current mandi price of tomato in Kolar?")
    
    # Test 3: Anti-Hallucination Fallback
    await run_query("What is the plot of the latest Marvel movie?")

if __name__ == "__main__":
    asyncio.run(main())
