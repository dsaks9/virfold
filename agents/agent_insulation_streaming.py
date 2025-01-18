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
    msg: str

class RetrievalEvent(Event):
    msg: str
    
class ProcessingEvent(Event):
    msg: str

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
        ctx.write_event_to_stream(InitialProcessingEvent(msg="Starting query processing..."))
        
        # clear sources
        self.sources = []

        # get user input
        if isinstance(ev, StartEvent):
            design_parameters = ev.input

        user_prompt = USER_PROMPT_INSULATION_AGENT.format(
            design_parameters=design_parameters,
        )

        # Signal processing before LLM work
        ctx.write_event_to_stream(ProcessingEvent(msg="Processing retrieved information..."))

                # get chat history and prepare for LLM call
        user_msg = ChatMessage(role='user', content=user_prompt)
        self.memory.put(user_msg)
        chat_history = self.memory.get()

        # Stream LLM response
        response_text = ""
        async for response_chunk in await self.llm.astream_complete(
            prompt=user_prompt,
        ):
            response_text += response_chunk.delta
            # Stream just the delta/chunk
            ctx.write_event_to_stream(ProgressEvent(content=response_chunk.delta))

        # Store final response in memory
        self.memory.put(response_text)

        return StopEvent(
            result={
                "response": response_text,
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
            if isinstance(event, RetrievalEvent):
                print("Retrieving relevant documents...")
            elif isinstance(event, ProcessingEvent):
                print("Processing retrieved information...")
            elif isinstance(event, ProgressEvent):
                chunk = event.content
                full_response += chunk
                print("\n\n\n", f"Full Response: {full_response}", "\n\n\n")

    # Run the async main function
    asyncio.run(main())