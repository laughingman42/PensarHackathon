import streamlit as st
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, Sequence
import operator

# --- Configuration ---
MODEL_NAME = "llama3.2" # Or the specific llama3.2 variant you have installed with Ollama

# --- LangGraph State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]

# --- LangGraph Node ---
def call_model(state: AgentState):
    """Invokes the Ollama model with the current conversation state."""
    try:
        llm = ChatOllama(model=MODEL_NAME)
        response = llm.invoke(state['messages'])
        # Ensure response is AIMessage if not already
        if not isinstance(response, AIMessage):
             response = AIMessage(content=str(response.content)) # Adapt based on actual response structure if needed
        return {"messages": [response]}
    except Exception as e:
        st.error(f"Error calling Ollama model: {e}")
        # Return an error message within the flow
        return {"messages": [AIMessage(content=f"Sorry, I encountered an error: {e}")]}

# --- LangGraph Graph Definition ---
# Using MemorySaver for state persistence (optional but good for potential future stateful features)
memory = MemorySaver()
builder = StateGraph(AgentState)
builder.add_node("agent", call_model)
builder.set_entry_point("agent")
builder.add_edge("agent", END) # Simple graph: call agent, then end the turn. Streamlit handles the loop.
graph = builder.compile(checkpointer=memory)

# --- Streamlit App ---
st.set_page_config(page_title=f"Chat with {MODEL_NAME}", layout="wide")
st.title(f"LangGraph Chat with Ollama ({MODEL_NAME})")

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    # Simple way to manage conversation state per session using a fixed ID
    # For multi-user or more complex scenarios, generate unique IDs
    st.session_state.thread_id = "streamlit_chat_1"

# Display past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input
if prompt := st.chat_input("What would you like to chat about?"):
    # Add user message to session state and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare input for the graph
    graph_input = {"messages": [HumanMessage(content=prompt)]}
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    # Streamlit spinner while processing
    with st.spinner("Thinking..."):
        try:
            # Invoke the graph
            # We stream the final state, which contains the accumulated messages
            final_state = None
            for event in graph.stream(graph_input, config=config):
                 # The final state is available under the key 'agent' after the node runs
                 if "agent" in event:
                     final_state = event["agent"]

            if final_state and final_state.get("messages"):
                # The last message in the state is the AI's response
                ai_response_message = final_state["messages"][-1]
                ai_response_content = ai_response_message.content

                # Add AI response to session state and display it
                st.session_state.messages.append({"role": "assistant", "content": ai_response_content})
                with st.chat_message("assistant"):
                    st.markdown(ai_response_content)
            else:
                 st.error("Failed to get a response from the AI.")
                 # Add error indication to chat history
                 st.session_state.messages.append({"role": "assistant", "content": "Sorry, I couldn't process that."})


        except Exception as e:
            st.error(f"An error occurred during graph execution: {e}")
            # Add error indication to chat history
            st.session_state.messages.append({"role": "assistant", "content": f"An error occurred: {e}"})

    # Persist the full conversation state back (optional, MemorySaver does this)
    # current_state = graph.get_state(config)
    # st.session_state.graph_state = current_state # Store if needed for complex restarts

