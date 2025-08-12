from typing import Any, Dict, TypedDict, Annotated, Optional, List
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from .agents_nodes.email_cleaner import email_cleaner, create_email_cleaner_llm
from .agents_nodes.reply_extractor import reply_extractor, create_reply_extractor_llm
from .agents_nodes.reply_necessity_checker import reply_necessity_checker, create_reply_necessity_checker_llm
from .agents_nodes.load_cancellation_checker import load_cancellation_checker, create_load_cancellation_checker_llm
from .agents_nodes.warnings_analyzer import warnings_analyzer
from .agents_nodes.email_judger import judge_email, create_email_judger_llm
from .agents_nodes.email_generator import email_generator, create_email_generator_llm
from .agents_nodes.negotiation_email_generator import negotiation_email_generator, create_negotiation_email_generator_llm
from .agents_nodes.rate_analyzer import analyze_rate, create_rate_analyzer_llm
from .agents_nodes.counter_offer_generator import generate_counter_offer
from .agents_nodes.generate_email_after_acceptance import generate_email_after_acceptance
from .agents_nodes.question_answerer import question_answerer, create_question_answerer_llm
from .const import EmailHistoryStatus

class State(TypedDict):
    """State for the email processing workflow."""
    email_generator_agent_messages: Annotated[list, add_messages]
    reply: str
    updated_load_fields: Dict[str, Any]
    email_to_send: str
    email_judgement: Optional[Dict[str, Any]]
    company_info: Dict[str, Any]
    load_info: Dict[str, Any]
    generate_email_attempts: int = 0
    missing_fields: List[str] = []
    truck_info: Dict[str, Any]

def create_workflow():
    """Create and configure the workflow graph."""
    # Initialize LLMs
    email_cleaner_llm = create_email_cleaner_llm()
    rate_analyzer_llm = create_rate_analyzer_llm()
    extractor_llm = create_reply_extractor_llm()
    email_llm = create_email_generator_llm()
    reply_necessity_llm = create_reply_necessity_checker_llm()
    load_cancellation_llm = create_load_cancellation_checker_llm()
    email_judger_llm = create_email_judger_llm()
    negotiation_email_generator_llm = create_negotiation_email_generator_llm()
    question_answerer_llm = create_question_answerer_llm()

    graph_builder = StateGraph(State)

    # Info request nodes
    graph_builder.add_node("email_cleaner", lambda state: email_cleaner(state, email_cleaner_llm))
    graph_builder.add_node("load_cancellation_checker", lambda state: load_cancellation_checker(state, load_cancellation_llm))
    graph_builder.add_node("reply_extractor", lambda state: reply_extractor(state, extractor_llm))
    graph_builder.add_node("warnings_analyzer", warnings_analyzer)
    graph_builder.add_node("reply_necessity_checker", lambda state: reply_necessity_checker(state, reply_necessity_llm))
    graph_builder.add_node("email_generator", lambda state: email_generator(state, email_llm))
    graph_builder.add_node("email_judger", lambda state: judge_email(state, email_judger_llm))

    # Negotiation nodes
    graph_builder.add_node("negotiation_email_generator", lambda state: negotiation_email_generator(state, negotiation_email_generator_llm))
    graph_builder.add_node("rate_analyzer", lambda state: analyze_rate(state, rate_analyzer_llm))
    graph_builder.add_node("counter_offer_generator", lambda state: generate_counter_offer(state, negotiation_email_generator_llm))
    graph_builder.add_node("generate_email_after_acceptance", generate_email_after_acceptance)
    graph_builder.add_node("question_answerer", lambda state: question_answerer(state, question_answerer_llm))

    # Define the workflow edges
    graph_builder.add_edge(START, "email_cleaner")
    graph_builder.add_edge("email_cleaner", "load_cancellation_checker")
    graph_builder.add_edge("load_cancellation_checker", "reply_extractor")

    def after_reply_extractor(state: State) -> str:
        if len(state.get("updated_load_fields", {}).keys()) > 0:
            return "warnings_analyzer"

        if state.get("load_info", {}).get("emailHistory", {}).get("isInfoRequestFinished", False) and state.get("load_info", {}).get("emailHistory", {}).get("status") == EmailHistoryStatus.get("COLLECTED_INFO"):
            return END

        return "reply_necessity_checker"

    graph_builder.add_conditional_edges("reply_extractor", after_reply_extractor)
    graph_builder.add_edge("warnings_analyzer", "reply_necessity_checker")

    def split_negotiation_and_info_request(state: State) -> str:
        if state.get("updated_load_fields", {}).get("emailHistory.isInfoRequestFinished", False) or state.get("load_info", {}).get("emailHistory", {}).get("isInfoRequestFinished", False):
            if state.get("updated_load_fields", {}).get("emailHistory.isInfoRequestFinished", False):
                return "negotiation_email_generator"
            else:
                if state.get("load_info", {}).get("emailHistory", {}).get("status") == EmailHistoryStatus.get("FIRST_BID_ACCEPTED") or state.get("load_info", {}).get("emailHistory", {}).get("status") == EmailHistoryStatus.get("SECOND_BID_ACCEPTED"):
                    return END

                return "rate_analyzer"
        else:
            return "email_generator"
    graph_builder.add_conditional_edges("reply_necessity_checker", split_negotiation_and_info_request)

    def after_rate_analyzer(state: State) -> str:
        if state.get("updated_load_fields", {}).get("emailHistory.status") == EmailHistoryStatus.get("FIRST_BID_ACCEPTED") or state.get("updated_load_fields", {}).get("emailHistory.status") == EmailHistoryStatus.get("SECOND_BID_ACCEPTED"):
            return "generate_email_after_acceptance"

        if state.get("updated_load_fields", {}).get("emailHistory.status") == EmailHistoryStatus.get("FIRST_BID_REJECTED"):
            return "counter_offer_generator"

        if state.get("updated_load_fields", {}).get("emailHistory.status") == EmailHistoryStatus.get("SECOND_BID_REJECTED"):
            return END

        return "question_answerer"
    graph_builder.add_conditional_edges("rate_analyzer", after_rate_analyzer)

    graph_builder.add_edge("email_generator", "email_judger")
    # Add conditional edge for email regeneration
    def should_regenerate_email(state: State) -> str:
        if not state.get("email_judgement", {}).get("should_send", False):
            if state["generate_email_attempts"] <= 3:
                return "email_generator"
            else:
                return END

        return END
    graph_builder.add_conditional_edges("email_judger", should_regenerate_email, {"email_generator": "email_generator", END: END})

    graph_builder.add_edge("question_answerer", END)

    return graph_builder.compile()
