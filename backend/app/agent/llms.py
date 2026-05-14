import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()

llm = ChatOpenAI(
    base_url=os.getenv("LLM_API_BASE"),
    model=os.getenv("LLM_MODEL"),
    api_key=SecretStr(
        os.getenv("LLM_API_KEY"),
    ),
    streaming=True,
    temperature=0,
    top_p=1,
    seed=42,
    # Hard timeout per HTTP request. Without this, a streaming response that
    # the upstream forgets to terminate ([DONE] missing, socket left open)
    # blocks the worker forever, which deadlocks as_completed in the
    # streaming analysis pipeline. 180s covers the largest structure pass
    # we've seen (~130s for 57-clause contracts) with margin.
    timeout=180,
)
