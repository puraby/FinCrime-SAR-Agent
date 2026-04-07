import streamlit as st
from typing import Annotated
from typing_extensions import TypedDict

# Core LangChain/LangGraph imports (Zero vendor lock-in)
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# --- PAGE CONFIG ---
st.set_page_config(page_title="Fintech Detective", page_icon="🕵️‍♂️", layout="centered")

# --- 1. MODEL FACTORY (Isolated Provider Logic) ---
def get_llm_provider() -> BaseChatModel:
    """
    This is the ONLY place vendor-specific code lives. 
    To swap to a local model, Anthropic, etc., change only this function.
    """
    from langchain_databricks import ChatDatabricks
    return ChatDatabricks(
        endpoint="databricks-gpt-oss-120b",
        max_tokens=1000,
        streaming=True
    )

# --- 2. LANGGRAPH STATE DEFINITION ---
class State(TypedDict):
    messages: Annotated[list, add_messages]

# --- 3. TRULY AGNOSTIC GRAPH ---
@st.cache_resource
def build_agent_graph():
    # Inject the generic model interface
    llm = get_llm_provider()

    def chatbot_node(state: State):
        # The node just invokes a generic BaseChatModel. 
        # It has zero awareness of Databricks or OpenAI.
        return {"messages": [llm.invoke(state["messages"])]}

    workflow = StateGraph(State)
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_edge(START, "chatbot")
    workflow.add_edge("chatbot", END)

    return workflow.compile()

app_graph = build_agent_graph()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Agent Configuration")
    st.info("Currently running LangGraph in General Chat Mode.")
    st.divider()
    st.markdown("**Future Integrations:**")
    st.checkbox("Enable Financial Flagging Engine", disabled=True)
    st.slider("Agent Confidence Threshold", 0.0, 1.0, 0.85, disabled=True)

# --- MAIN UI ---
st.title("🕵️‍♂️ Fintech Detective Assistant")
st.markdown("Drop in financial data, queries, or reports for analysis.")

if "messages" not in st.session_state:
    st.session_state.messages = [
        AIMessage(content="Hello! I am ready to assist. What would you like to investigate today?")
    ]

for msg in st.session_state.messages:
    role = "assistant" if isinstance(msg, AIMessage) else "user"
    with st.chat_message(role):
        st.markdown(msg.content)

if prompt := st.chat_input("Enter your query here..."):
    user_msg = HumanMessage(content=prompt)
    st.session_state.messages.append(user_msg)
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            for chunk, metadata in app_graph.stream(
                {"messages": st.session_state.messages}, 
                stream_mode="messages"
            ):
                if metadata.get("langgraph_node") == "chatbot":
                    content = chunk.content
                    if content:
                        # 1. If the model returns a list of blocks (like OSS-120b or Claude)
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    full_response += item.get("text", "")
                                elif isinstance(item, str):
                                    full_response += item
                        # 2. If the model returns a standard string
                        elif isinstance(content, str):
                            full_response += content
                        
                        # Update UI
                        message_placeholder.markdown(full_response + "▌")
            
            # Remove the cursor block when finished
            message_placeholder.markdown(full_response)
            
            # Save to session state
            st.session_state.messages.append(AIMessage(content=full_response))
            
        except Exception as e:
            st.error(f"⚠️ Graph Execution Error: {e}")