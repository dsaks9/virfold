import streamlit as st
import asyncio
from typing import AsyncGenerator
import sys
import os
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_insulation_streaming import (
    InsulationAgent,
    InitialProcessingEvent,
    ProvidedParametersEvent,
    RequiredParametersEvent,
    AssumptionsEvent,
    CalculationPlanEvent,
    ProgressEvent,
)
from llama_index.core.workflow import StopEvent

# Set page config for better appearance
st.set_page_config(
    page_title="Insulation Calculator",
    page_icon="🌡️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .main {
        padding: 2rem;
    }
    .stMarkdown {
        font-size: 1.1rem;
    }
    h1 {
        color: #1E88E5;
        padding-bottom: 1rem;
    }
    h3 {
        color: #0D47A1;
        padding-top: 1rem;
        margin-top: 2rem;
    }
    .stTextArea {
        font-family: monospace;
    }
    .result-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 5px solid #1E88E5;
    }
    .result-section ul {
        list-style-type: none;
        padding-left: 0;
        margin-top: 1rem;
    }
    .result-section li {
        margin-bottom: 0.8rem;
        line-height: 1.6;
    }
    .result-section p {
        margin-bottom: 0.8rem;
        line-height: 1.6;
    }
    .step-header {
        font-weight: bold;
        color: #1565C0;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }
    .parameter-item {
        margin-bottom: 1rem;
        padding-left: 1rem;
        border-left: 3px solid #90CAF9;
    }
    .numbered-item {
        margin-bottom: 1rem;
        padding-left: 2rem;
        position: relative;
    }
    .numbered-item::before {
        content: attr(data-number);
        position: absolute;
        left: 0;
        color: #1565C0;
        font-weight: bold;
    }
    .equation {
        margin: 1rem 0;
        padding: 0.5rem 0;
    }
    .bullet-item {
        display: flex;
        align-items: flex-start;
        margin-bottom: 1rem;
        gap: 0.5rem;
    }
    .bullet-item::before {
        content: "•";
        color: #1565C0;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

def format_latex(content: str) -> str:
    """Format LaTeX equations properly for Streamlit."""
    # Replace LaTeX delimiters with proper Streamlit markdown
    content = re.sub(r'\\\[(.*?)\\\]', r'$\1$', content)
    content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
    
    # Format inline math mode
    content = re.sub(r'\\text{(.*?)}', r'\1', content)
    
    return content

def format_content(content: str) -> str:
    """Format the content for better display."""
    # Format LaTeX equations
    content = format_latex(content)
    
    # Handle numbered lists (like assumptions)
    if any(line.strip().startswith(str(i) + ".") for i in range(1, 10) for line in content.split("\n")):
        lines = content.split("\n")
        formatted_lines = []
        for line in lines:
            match = re.match(r'(\d+)\.(.*)', line.strip())
            if match:
                number, text = match.groups()
                formatted_lines.append(
                    f'<div class="numbered-item" data-number="{number}.">{text.strip()}</div>'
                )
            else:
                formatted_lines.append(line)
        content = "\n".join(formatted_lines)
    
    # Format bullet points
    if content.strip().startswith("•") or content.strip().startswith("-"):
        lines = content.split("\n")
        formatted_lines = []
        for line in lines:
            if line.strip().startswith("•") or line.strip().startswith("-"):
                text = line.strip()[1:].strip()
                formatted_lines.append(f'<div class="bullet-item">{text}</div>')
            else:
                formatted_lines.append(line)
        content = "\n".join(formatted_lines)
    
    # Format parameters as list items with proper spacing
    if "Parameters" in content:
        lines = content.split("\n")
        formatted_lines = []
        current_param = []
        
        for line in lines:
            if line.strip().startswith("-"):
                if current_param:
                    formatted_lines.append(
                        f'<div class="parameter-item">{" ".join(current_param)}</div>'
                    )
                    current_param = []
                current_param.append(line.strip()[1:].strip())
            elif line.strip() and current_param:
                current_param.append(line.strip())
            else:
                if current_param:
                    formatted_lines.append(
                        f'<div class="parameter-item">{" ".join(current_param)}</div>'
                    )
                    current_param = []
                formatted_lines.append(line)
        
        if current_param:
            formatted_lines.append(
                f'<div class="parameter-item">{" ".join(current_param)}</div>'
            )
        
        content = "\n".join(formatted_lines)
    
    # Format calculation steps
    if "Step" in content:
        lines = content.split("\n")
        formatted_lines = []
        for line in lines:
            if line.strip().startswith("Step"):
                formatted_lines.append(f'<div class="step-header">{line.strip()}</div>')
            elif "=" in line and any(c in line for c in "{}[]()"):
                # This is likely an equation
                formatted_lines.append(f'<div class="equation">{line.strip()}</div>')
            else:
                formatted_lines.append(line)
        content = "\n".join(formatted_lines)
    
    return content

async def run_agent_with_stream(agent: InsulationAgent, query: str) -> AsyncGenerator:
    """Run the agent and yield streaming events."""
    handler = agent.run(input=query)
    async for event in handler.stream_events():
        yield event
    
    # Get the final result and yield it as a StopEvent
    result = await handler
    yield result

def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if 'calculation_plan' not in st.session_state:
        st.session_state.calculation_plan = ""
    if 'parameters_provided' not in st.session_state:
        st.session_state.parameters_provided = ""
    if 'parameters_required' not in st.session_state:
        st.session_state.parameters_required = ""
    if 'assumptions' not in st.session_state:
        st.session_state.assumptions = ""

def main():
    st.title("🌡️ Insulation Calculator")
    st.markdown("""
    This calculator helps you determine the optimal insulation parameters for your pipe system.
    Enter your design parameters below and click 'Calculate' to get detailed analysis.
    """)

    # Initialize session state
    initialize_session_state()

    # Create two columns for layout
    col1, col2 = st.columns([1, 2])

    with col1:
        # Input form with custom styling
        with st.form("insulation_form", clear_on_submit=False):
            st.markdown("### Input Parameters")
            # Example input template
            default_input = """- **Units System**: Metric
- **Standard**: ISO 12241
- **Pipe Material**: PB
- **Pipe Diameter**: PB - 16 mm
- **Thickness**: 6 - 1/4" mm
- **Insulation**: ThermaSmart PRO Tubes
- **Pipe Length**: 1 m
- **Temperatures**:
  - Medium: 40°C
  - Ambient: 20°C"""
            
            user_input = st.text_area(
                "Design Parameters",
                value=default_input,
                height=400,
                help="Enter your insulation design parameters here.",
                key="input_parameters"
            )
            
            submitted = st.form_submit_button("Calculate", use_container_width=True)

    with col2:
        if submitted:
            # Clear previous results
            st.session_state.calculation_plan = ""
            st.session_state.parameters_provided = ""
            st.session_state.parameters_required = ""
            st.session_state.assumptions = ""

            # Create containers for each section
            calc_container = st.empty()
            params_provided_container = st.empty()
            params_required_container = st.empty()
            assumptions_container = st.empty()

            # Initialize the agent
            agent = InsulationAgent(timeout=3600, verbose=True)

            async def process_events():
                async for event in run_agent_with_stream(agent, user_input):
                    if isinstance(event, CalculationPlanEvent):
                        st.session_state.calculation_plan = event.content
                        formatted_content = format_content(st.session_state.calculation_plan)
                        calc_container.markdown(f"""
                        <div class="result-section">
                            <h3>Calculation Plan</h3>
                            {formatted_content}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    elif isinstance(event, ProvidedParametersEvent):
                        st.session_state.parameters_provided = event.content
                        formatted_content = format_content(st.session_state.parameters_provided)
                        params_provided_container.markdown(f"""
                        <div class="result-section">
                            <h3>Parameters Provided</h3>
                            {formatted_content}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    elif isinstance(event, RequiredParametersEvent):
                        st.session_state.parameters_required = event.content
                        formatted_content = format_content(st.session_state.parameters_required)
                        params_required_container.markdown(f"""
                        <div class="result-section">
                            <h3>Parameters Required</h3>
                            {formatted_content}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    elif isinstance(event, AssumptionsEvent):
                        st.session_state.assumptions = event.content
                        formatted_content = format_content(st.session_state.assumptions)
                        assumptions_container.markdown(f"""
                        <div class="result-section">
                            <h3>Assumptions</h3>
                            {formatted_content}
                        </div>
                        """, unsafe_allow_html=True)

            # Run the async event processing
            with st.spinner("Initializing calculation..."):
                asyncio.run(process_events())

        # Show previous results if they exist
        elif any([
            st.session_state.calculation_plan,
            st.session_state.parameters_provided,
            st.session_state.parameters_required,
            st.session_state.assumptions
        ]):
            if st.session_state.calculation_plan:
                formatted_content = format_content(st.session_state.calculation_plan)
                st.markdown(f"""
                <div class="result-section">
                    <h3>Calculation Plan</h3>
                    {formatted_content}
                </div>
                """, unsafe_allow_html=True)
            
            if st.session_state.parameters_provided:
                formatted_content = format_content(st.session_state.parameters_provided)
                st.markdown(f"""
                <div class="result-section">
                    <h3>Parameters Provided</h3>
                    {formatted_content}
                </div>
                """, unsafe_allow_html=True)
            
            if st.session_state.parameters_required:
                formatted_content = format_content(st.session_state.parameters_required)
                st.markdown(f"""
                <div class="result-section">
                    <h3>Parameters Required</h3>
                    {formatted_content}
                </div>
                """, unsafe_allow_html=True)
            
            if st.session_state.assumptions:
                formatted_content = format_content(st.session_state.assumptions)
                st.markdown(f"""
                <div class="result-section">
                    <h3>Assumptions</h3>
                    {formatted_content}
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 