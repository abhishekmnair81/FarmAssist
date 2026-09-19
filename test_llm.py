import asyncio
import os
import sys
from app.agent.graph import workflow
from langchain_core.messages import HumanMessage
from app.services.text_cleaner import clean_response_text
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

async def run_test():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "checkpoints.sqlite")
    
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        state = await graph.ainvoke(
            {'messages': [HumanMessage(content='Hi')], 'sender_phone': 'test_bot_123'},
            config={'configurable': {'thread_id': 'test_123'}}
        )
        print("LLM RAW OUTPUT:")
        print(repr(state['messages'][-1].content))
        print("\nCLEANED OUTPUT:")
        print(clean_response_text(state['messages'][-1].content))

if __name__ == "__main__":
    asyncio.run(run_test())
