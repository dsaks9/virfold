import os
from typing import Any
import asyncio
import json

from llama_index.core.llms import ChatMessage
from llama_index.core import SimpleDirectoryReader
from llama_index.core.tools import ToolSelection
from llama_index.core.workflow import Event
from llama_index.llms.openai import OpenAI
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Context

from agents.prompts.prompts import SYSTEM_PROMPT_INSULATION_AGENT, USER_PROMPT_INSULATION_AGENT

# Custom events for streaming
class InitialProcessingEvent(Event):
    content: str

class ProvidedParametersEvent(Event):
    content: str

class RequiredParametersEvent(Event):
    content: str

class AssumptionsEvent(Event):
    content: str

class CalculationPlanEvent(Event):
    content: str

class ProgressEvent(Event):
    content: str

class InsulationAgent(Workflow):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # initialize the LLM
        model = 'o1-preview-2024-09-12'
        self.llm = OpenAI(
            model=model, 
            max_completion_tokens=4096,
            api_key=os.getenv("OPENAI_API_KEY"),
            system_prompt=SYSTEM_PROMPT_INSULATION_AGENT
        )

        # initialize the memory
        self.memory = ChatMemoryBuffer.from_defaults(llm=self.llm)
        self.sources = []

        # initialize the system message
        sys_msg = ChatMessage(role='system', content=SYSTEM_PROMPT_INSULATION_AGENT)
        self.memory.put(sys_msg)

    @step()
    async def agent_director(self, ev: StartEvent, ctx: Context) -> StopEvent:
        # Signal initial processing
        ctx.write_event_to_stream(InitialProcessingEvent(content="Starting query processing..."))
        
        # clear sources
        self.sources = []

        # get user input
        if isinstance(ev, StartEvent):
            design_parameters = ev.input

        user_prompt = USER_PROMPT_INSULATION_AGENT.format(
            design_parameters=design_parameters,
        )

        # get chat history and prepare for LLM call
        user_msg = ChatMessage(role='user', content=user_prompt)
        self.memory.put(user_msg)
        chat_history = self.memory.get()

        # Stream LLM response
        full_response = ""  # Keep track of complete response
        section_response = ""  # For section processing
        current_section = None
        
        async for response_chunk in await self.llm.astream_complete(
            prompt=user_prompt,
        ):
            delta = response_chunk.delta
            full_response += delta  # Add to complete response
            section_response += delta  # Add to section processing

            # Check for section starts
            if current_section is None:
                for section in ["calculation_plan", "parameters_provided", "parameters_required", "assumptions"]:
                    start_tag = f"<{section}>"
                    if start_tag in section_response and section_response.find(start_tag) == section_response.rfind(start_tag):
                        current_section = section
                        # Find the start position after the tag
                        start_pos = section_response.find(start_tag) + len(start_tag)
                        # Reset the section content to what we have after the tag
                        section_content = section_response[start_pos:]
                        break
            
            # If we're in a section, check for end tag
            if current_section:
                end_tag = f"</{current_section}>"
                if end_tag in section_response:
                    # Find where the end tag starts
                    end_pos = section_response.find(end_tag)
                    # Get the content up to the end tag
                    section_content = section_response[section_response.find(f"<{current_section}>") + len(f"<{current_section}>"):end_pos]
                    
                    # Emit the appropriate event
                    event_map = {
                        "calculation_plan": CalculationPlanEvent,
                        "parameters_provided": ProvidedParametersEvent,
                        "parameters_required": RequiredParametersEvent,
                        "assumptions": AssumptionsEvent
                    }
                    
                    if current_section in event_map:
                        ctx.write_event_to_stream(event_map[current_section](content=section_content.strip()))
                    
                    # Remove the processed section from section_response to avoid duplicate processing
                    section_with_tags = section_response[section_response.find(f"<{current_section}>"):end_pos + len(end_tag)]
                    section_response = section_response.replace(section_with_tags, "")
                    current_section = None
            
            # Always stream progress
            ctx.write_event_to_stream(ProgressEvent(content=delta))

        # Store final response in memory
        assistant_msg = ChatMessage(role='assistant', content=full_response)
        self.memory.put(assistant_msg)

        return StopEvent(
            result={
                "response": full_response,  # Return the complete response
                "sources": [*self.sources]
            }
        ) 
    


if __name__ == "__main__":
    async def run_agent_with_stream(agent, query: str):
        """Run the agent and yield streaming events."""
        handler = agent.run(input=query)
        async for event in handler.stream_events():
            yield event
        
        # Get the final result and yield it as a StopEvent
        result = await handler
        yield result

    async def main():
        agent = InsulationAgent(timeout=3600, verbose=True)

        full_response = ""
        query = """
                - **Units System**: Metric
                - **Standard**: ISO 12241
                - **Pipe Material**: PB
                - **Pipe Diameter**: PB - 16 mm
                - **Thickness**: 6 - 1/4" mm
                - **Insulation**: ThermaSmart PRO Tubes
                - **Pipe Length**: 1 m
                - **Temperatures**:
                - Medium: 40°C
                - Ambient: 20°C
                """
        
        async for event in run_agent_with_stream(agent, query):
            if isinstance(event, ProvidedParametersEvent):
                print("\n=== Parameters Provided ===")
                print(event.content)
                print("===========================\n")
            elif isinstance(event, RequiredParametersEvent):
                print("\n=== Parameters Required ===")
                print(event.content)
                print("===========================\n")
            elif isinstance(event, AssumptionsEvent):
                print("\n=== Assumptions ===")
                print(event.content)
                print("==================\n")
            elif isinstance(event, CalculationPlanEvent):
                print("\n=== Calculation Plan ===")
                print(event.content)
                print("======================\n")
            elif isinstance(event, StopEvent):
                print("\n=== Final Response ===")
                print(event.result["response"])
                print("======================\n")
            elif isinstance(event, ProgressEvent):
                chunk = event.content
                full_response += chunk
                # Uncomment to see streaming progress
                # print("\n\n\n", f"Full Response: {full_response}", "\n\n\n")

    # Run the async main function
    asyncio.run(main())