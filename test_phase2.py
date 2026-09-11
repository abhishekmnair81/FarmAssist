import asyncio
import uuid
import re
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.graph import workflow

async def run_query(query: str):
    print(f"\n[{'='*40}]")
    print(f"User Query: {query}")
    print(f"[{'='*40}]")
    
    db_path = "/app/data/checkpoints.sqlite"
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
        
        # Clean reasoning
        stripped = re.sub(r'<think>.*?</think>', '', final_message, flags=re.DOTALL).strip()
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
