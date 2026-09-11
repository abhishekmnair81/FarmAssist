import asyncio
from app.agent.graph import workflow
from langchain_core.messages import HumanMessage
from app.config import DB_PATH
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async def test():
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        state = await graph.ainvoke(
            {'messages': [HumanMessage(content='Hi')], 'sender_phone': 'test_bot_123'},
            config={'configurable': {'thread_id': 'test_123'}}
        )
        print("LLM OUTPUT:")
        print(repr(state['messages'][-1].content))

if __name__ == "__main__":
    asyncio.run(test())
