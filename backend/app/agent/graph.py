from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from .llms import llm


class FollowUpState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    contract_summary: str
    report_highlights: str
    remaining_rounds: int
    user_id: int
    contract_record_id: int


SYSTEM_PROMPT_TEMPLATE = """You are SpotClause, an AI document assistant. You help users understand contract documents by highlighting key clauses, identifying notable terms, and suggesting areas that may need attention.

## YOUR ROLE
- Answer questions ONLY related to the contract being reviewed
- Provide clear, actionable document insights in plain language
- Maintain a neutral position - do not favor either party (甲方/乙方)
- Always reference relevant document context when making claims
- Be concise but thorough

## RULES
1. NEVER engage in casual conversation, greetings, or small talk
2. NEVER answer questions unrelated to the contract (politics, weather, general knowledge, coding, etc.)
3. If asked an off-topic question, respond: "I can only answer questions related to this document. Please ask about the contract terms, clauses, or document details."
4. ALWAYS reference specific clauses from the contract when answering
5. When suggesting negotiation strategies, consider both parties' perspectives
6. Use the contract summary and report highlights as your primary source

## CONTRACT CONTEXT
{contract_summary}

## REPORT HIGHLIGHTS
{report_highlights}
"""

GUARDRAIL_PROMPT = """If the user's question is NOT related to documents, contract terms, suggested edits, clause analysis, or the specific document being reviewed, respond with:
"I can only answer questions related to this document. Please ask about the contract terms, clauses, or document details."

If the user asks about yourself (who you are, what you can do, etc.), respond briefly that you are SpotClause's document assistant and redirect to document questions.
"""


def create_follow_up_agent():
    def agent(state: FollowUpState):
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            contract_summary=state["contract_summary"],
            report_highlights=state["report_highlights"],
        ) + "\n\n" + GUARDRAIL_PROMPT

        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history
        for msg in state["messages"]:
            messages.append(msg)

        response = llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(FollowUpState)
    graph.add_node("agent", agent)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)
    return graph.compile()


follow_up_app = create_follow_up_agent()


def compress_context(messages: List[BaseMessage]) -> List[BaseMessage]:
    """Compress conversation context based on round count.
    - <= 4 rounds: keep all full text
    - 5-8 rounds: compress first 2 rounds to summary
    - 9-10 rounds: compress first 4 rounds to summary
    """
    total = len(messages)
    if total <= 4:
        return messages

    if total <= 8:
        # Compress first 2 rounds
        summary = "[Earlier conversation summarized] The user asked initial questions about the contract and received explanations about key terms and risks."
        return [SystemMessage(content=summary)] + messages[4:]

    # 9-10 rounds: compress first 4 rounds
    summary = "[Earlier conversation summarized] The user explored various aspects of the contract including terms, risks, and negotiation strategies. Key points were discussed."
    return [SystemMessage(content=summary)] + messages[8:]
