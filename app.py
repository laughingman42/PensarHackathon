import streamlit as st
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode # Use ToolNode for cleaner tool execution

from typing import TypedDict, Annotated, Sequence
import operator
import json # For printing tool results if needed
import traceback # Import traceback module

# Import database utility functions and the tool decorator
from db_utils import (
    get_customer_by_name,
    get_customer_by_id,
    get_accounts_for_customer,
    get_transactions_for_account
)
from langchain_core.tools import tool

# --- Configuration ---
MODEL_NAME = "llama3.2" # Or the specific llama3.2 variant you have installed with Ollama

# --- Define Tools using the @tool decorator ---
@tool
def get_customer_by_name_tool(name: str):
    """Finds a customer by their partial or full name (case-insensitive). Returns customer details if found, otherwise None."""
    return get_customer_by_name(name)

@tool
def get_customer_by_id_tool(customer_id: int):
    """Gets customer details based on their unique customer ID."""
    return get_customer_by_id(customer_id)

@tool
def get_accounts_for_customer_tool(customer_id: int):
    """Gets all accounts associated with a specific customer ID. Returns a list of accounts."""
    return get_accounts_for_customer(customer_id)

@tool
def get_transactions_for_account_tool(account_id: int, limit: int = 10):
    """Gets the most recent transactions for a specific account ID. Limit defaults to 10."""
    return get_transactions_for_account(account_id, limit=limit)

# List of tools for the agent
tools = [
    get_customer_by_name_tool,
    get_customer_by_id_tool,
    get_accounts_for_customer_tool,
    get_transactions_for_account_tool
]

# --- LangGraph State Definition ---
class AgentState(TypedDict):
    # The `add` operator delegates tasks RunnableWhenConfigurationIsAvailable
    messages: Annotated[Sequence[HumanMessage | AIMessage | ToolMessage], operator.add]

# --- LangGraph Nodes ---
def should_continue(state: AgentState) -> str:
    """Determines whether to continue the graph or end.

    Args:
        state (AgentState): The current graph state.

    Returns:
        str: "tools" if the agent should call tools, END otherwise.
    """
    last_message = state['messages'][-1]
    # If the LLM makes a tool call, then we route to the tool node
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    # Otherwise, we stop (reply to the user)
    return END

def call_model(state: AgentState):
    """Invokes the Ollama model with the current conversation state and available tools."""
    messages = state['messages']
    try:
        # Bind tools to the LLM. This informs the LLM about available tools.
        llm = ChatOllama(model=MODEL_NAME).bind_tools(tools)
        response = llm.invoke(messages)
        # We return a list, because this will get added to the existing list
        return {"messages": [response]}
    except Exception as e:
        st.error(f"Error calling Ollama model: {e}")
        print("--- ERROR TRACEBACK ---") # Add a marker
        print(traceback.format_exc()) # Print the full traceback
        print("--- END TRACEBACK ---")
        # Return an error message within the flow
        return {"messages": [AIMessage(content=f"Sorry, I encountered an error calling the model: {e}")]}

# Use the prebuilt ToolNode for executing tools
tool_node = ToolNode(tools)

# --- LangGraph Graph Definition ---
# Using MemorySaver for state persistence
memory = MemorySaver()
builder = StateGraph(AgentState)

# Define the nodes
builder.add_node("agent", call_model)
builder.add_node("tools", tool_node) # Add the prebuilt tool execution node

# Set the entry point
builder.set_entry_point("agent")

# Add the conditional edge
builder.add_conditional_edges(
    "agent",
    should_continue, # Function to decide routing
    {
        "tools": "tools", # If should_continue returns "tools", route to the tool_node
        END: END      # If should_continue returns END, finish the graph run
    }
)

# Add edge from tool node back to agent node (so model can process tool results)
builder.add_edge("tools", "agent")

# Compile the graph
graph = builder.compile(checkpointer=memory)

# --- Streamlit App ---
st.set_page_config(page_title=f"Banking Chat ({MODEL_NAME})", layout="wide")
st.title(f"LangGraph Banking Chat with Ollama ({MODEL_NAME}) and Tools")

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    # Using a fixed thread_id for simplicity in this single-user example
    st.session_state.thread_id = "banking_chat_1"

# Display past messages
for msg_data in st.session_state.messages:
    with st.chat_message(msg_data["role"]):
        st.markdown(msg_data["content"])
        # Optionally display tool calls/results stored in session state if needed
        if msg_data.get("tool_calls"):
             st.json(msg_data["tool_calls"])
        if msg_data.get("tool_results"):
             st.json(msg_data["tool_results"])


# Get user input
if prompt := st.chat_input("Ask about customers, accounts, or transactions..."):
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
            # Invoke the graph, streaming events
            final_ai_response = None
            tool_calls_info = []
            tool_results_info = []

            # Stream events to see intermediate steps (optional)
            # for event in graph.stream(graph_input, config=config, stream_mode="values"):
            #     # event is the full state dictionary at each step
            #     # You could inspect event['messages'][-1] here for tool calls/results
            #     # st.write(event) # Uncomment to see the full state at each step
            #     pass # Keep it simple for now, just get the final result

            # Run the graph and get the final state
            # Using batch for simplicity to get final state directly
            final_state = graph.batch([graph_input], config=config)[0]

            if final_state and final_state.get("messages"):
                 # The final response from the AI should be the last message
                 final_message = final_state["messages"][-1]
                 if isinstance(final_message, AIMessage):
                     final_ai_response = final_message.content

                 # Store tool interactions from the *final* state for display (if any occurred)
                 for msg in final_state["messages"]:
                     if isinstance(msg, AIMessage) and msg.tool_calls:
                          # Extract tool call details for potential display
                          calls = [{k: v for k, v in call.items() if k != 'type'} for call in msg.tool_calls]
                          tool_calls_info.extend(calls)
                     elif isinstance(msg, ToolMessage):
                         # Extract tool result details for potential display
                          tool_results_info.append({"tool_call_id": msg.tool_call_id, "content": msg.content})

            if final_ai_response:
                # Add AI response to session state and display it
                response_data = {"role": "assistant", "content": final_ai_response}
                # Add tool info if it exists
                if tool_calls_info:
                    response_data["tool_calls"] = tool_calls_info
                if tool_results_info:
                     response_data["tool_results"] = tool_results_info

                st.session_state.messages.append(response_data)

                with st.chat_message("assistant"):
                    st.markdown(final_ai_response)
                    # Optionally display concise tool info
                    if tool_calls_info or tool_results_info:
                         with st.expander("Tool Activity"):
                             if tool_calls_info:
                                 st.write("**Tool Calls:**")
                                 st.json(tool_calls_info)
                             if tool_results_info:
                                 st.write("**Tool Results:**")
                                 st.json(tool_results_info)
            else:
                 st.error("Failed to get a final response from the AI.")
                 st.session_state.messages.append({"role": "assistant", "content": "Sorry, I couldn't generate a final response."})

        except Exception as e:
            st.error(f"An error occurred during graph execution: {e}")
            st.session_state.messages.append({"role": "assistant", "content": f"An error occurred: {e}"})
