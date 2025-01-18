import streamlit as st
import sys
import os
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from agents.agent_q_a import ManualQueryAgent

# Create async function to run the agent
async def run_agent_query(query: str):
    agent = ManualQueryAgent(timeout=120, verbose=True)
    result = await agent.run(input=query)
    return result

# Create sync wrapper for the async function
def run_agent_sync(query: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(run_agent_query(query))
    loop.close()
    return result

def main():
    st.set_page_config(
        page_title="AI Document Assistant",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 AI Document Assistant")
    st.markdown("---")

    # User input
    user_query = st.text_input(
        "Ask your question:",
        placeholder="What would you like to know about?",
        key="user_input"
    )

    if st.button("Ask AI Assistant", type="primary"):
        if user_query:
            with st.spinner("Processing your question..."):
                try:
                    # Run the agent and get response
                    result = run_agent_sync(user_query)
                    
                    # Create two columns for the response
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown("### AI Response")
                        st.markdown(result["response"])
                    
                    with col2:
                        st.markdown("### Query Info")
                        st.info("""
                        This response was generated using:
                        - Claude 3.5 Sonnet
                        - OpenAI Embeddings
                        - Qdrant Vector Store
                        - Cohere Reranking
                        """)
                
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please enter a question.")

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
        st.markdown("### System Status")
        required_vars = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "COHERE_API_KEY",
            "QDRANT_API_KEY",
            "PHOENIX_API_KEY"
        ]
        
        for var in required_vars:
            if os.getenv(var):
                st.success(f"✅ {var} is set")
            else:
                st.error(f"❌ {var} is missing")

if __name__ == "__main__":
    main() 