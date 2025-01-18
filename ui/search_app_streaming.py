import streamlit as st
import sys
import os
import asyncio
from pathlib import Path
import json

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from agents.agent_q_a_streaming import ManualQueryStreamingAgent, InitialProcessingEvent, RetrievalEvent, ProcessingEvent, ProgressEvent, StopEvent

async def run_agent_with_stream(agent, query: str):
    """Run the agent and yield streaming events."""
    handler = agent.run(input=query)
    async for event in handler.stream_events():
        yield event
    
    # Get the final result and yield it as a StopEvent
    result = await handler
    yield result

# Helper function to format text for HTML display
def format_text_for_html(text):
    # First replace literal \n with actual newlines
    text = text.replace('\\n', '\n')
    
    # Handle bullet points and indentation
    text = text.replace('- ', '•&nbsp;')  # Replace dash bullets with proper bullets
    
    # Replace newlines with HTML breaks
    text = text.replace('\n', '<br>')
    
    # Handle multiple spaces (preserve indentation)
    text = text.replace('  ', '&nbsp;&nbsp;')
    
    # Add extra space after sections
    text = text.replace(':<br>', ':</p>')
    text = text.replace('implications:<br>', 'implications:</p>')
    
    return text

def main():
    st.set_page_config(
        page_title="System Component Documentation Assistant",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 System Component Documentation Assistant")
    st.markdown("---")

    # Initialize session state for messages if not exists
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Initialize agent if not exists
    if 'agent' not in st.session_state:
        st.session_state.agent = ManualQueryStreamingAgent(timeout=120, verbose=True)

    # Reset chat button
    if st.sidebar.button('Reset Chat'):
        st.session_state.messages = []
        st.session_state.agent = ManualQueryStreamingAgent(timeout=120, verbose=True)
        st.rerun()

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    user_query = st.chat_input(
        "Ask your question:",
        key="user_input"
    )

    if user_query:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_query})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)

        # Display assistant response with streaming
        with st.chat_message("assistant"):
            # Create two containers for different sections
            technical_container = st.container()
            response_container = st.container()
            
            full_response = ""
            status_placeholder = st.empty()  # Single status placeholder
            in_technical_section = False
            
            # Create empty elements for each section
            with technical_container:
                st.markdown("#### Technical Analysis")
                tech_placeholder = st.empty()
            
            with response_container:
                st.markdown("#### Detailed Response")
                resp_placeholder = st.empty()
            
            current_tech_content = ""
            current_resp_content = ""

            try:
                async def process_stream():
                    nonlocal full_response, in_technical_section
                    nonlocal current_tech_content, current_resp_content
                    
                    # Set initial status
                    status_placeholder.info("Starting query processing...")
                    
                    async for event in run_agent_with_stream(st.session_state.agent, user_query):
                        if isinstance(event, RetrievalEvent):
                            status_placeholder.info("Retrieving relevant documents...")
                        elif isinstance(event, ProcessingEvent):
                            status_placeholder.info("Processing retrieved information...")
                        elif isinstance(event, ProgressEvent):
                            chunk = event.content
                            full_response += chunk

                            # Handle section transitions and content
                            if "<technical_breakdown>" in chunk:
                                in_technical_section = True
                                chunk = chunk.replace("<technical_breakdown>", "").strip()
                            
                            if "</technical_breakdown>" in chunk:
                                parts = chunk.split("</technical_breakdown>")
                                
                                if parts[0].strip():
                                    current_tech_content += parts[0].strip()
                                    tech_placeholder.code(current_tech_content, language=None)
                                
                                in_technical_section = False
                                
                                if len(parts) > 1 and parts[1].strip():
                                    current_resp_content += parts[1].strip()
                                    resp_placeholder.markdown(current_resp_content)
                            else:
                                if chunk.strip():
                                    if in_technical_section:
                                        current_tech_content += chunk
                                        tech_placeholder.code(current_tech_content, language=None)
                                    else:
                                        current_resp_content += chunk
                                        resp_placeholder.markdown(current_resp_content)

                        elif isinstance(event, StopEvent):
                            status_placeholder.empty()

                    return full_response

                # Run the streaming process
                full_response = asyncio.run(process_stream())
                
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response
                })

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    # Add helpful information in the sidebar
    with st.sidebar:
        st.markdown("### About")
        st.markdown("""
        This AI assistant uses advanced language models and document retrieval to:
        - Understand your questions
        - Search through technical documentation
        - Provide detailed, accurate answers
        - Consider relevant images and diagrams
        """)
        
        st.markdown("### Tips for Better Results")
        st.markdown("""
        - Be specific in your questions
        - Include relevant technical terms
        - Ask one question at a time
        - Mention specific components or systems if applicable
        """)

        # Add environment variable check
        st.markdown("### System Component Documentation Available")
        required_vars = [
            "COMPRESSOR",
            "HTF PUMP",
            "EVAPORATOR FAN MOTOR",
            # "QDRANT_API_KEY",
            # "PHOENIX_API_KEY"
        ]
        
        for var in required_vars:
            if os.getenv(var) or var == "COMPRESSOR":
                st.success(f"✅ {var} is set")
            else:
                st.error(f"❌ {var} is missing")

if __name__ == "__main__":
    main() 