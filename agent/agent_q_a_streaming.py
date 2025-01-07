import os
from typing import Any
import asyncio
import json

from llama_index.core.llms import ChatMessage
from llama_index.core import SimpleDirectoryReader
from llama_index.core.tools import ToolSelection
from llama_index.core.workflow import Event
from llama_index.multi_modal_llms.anthropic import AnthropicMultiModal
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Context

from retrievers.retriever_baseline import retrieve_pages
from agent.prompts.prompts import SYSTEM_PROMPT_MANUAL_QA_AGENT, USER_PROMPT_MANUAL_MULTIMODAL_QA_AGENT

# Custom events for streaming
class InitialProcessingEvent(Event):
    msg: str

class RetrievalEvent(Event):
    msg: str
    
class ProcessingEvent(Event):
    msg: str

class ProgressEvent(Event):
    content: str

class ManualQueryStreamingAgent(Workflow):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # initialize the LLM
        model = 'claude-3-5-sonnet-20240620'
        self.llm_mm = AnthropicMultiModal(
            model=model, 
            max_tokens=4096,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            system_prompt=SYSTEM_PROMPT_MANUAL_QA_AGENT,
            streaming=True  # Enable streaming
        )

        # initialize the memory
        self.memory = ChatMemoryBuffer.from_defaults(llm=self.llm_mm)
        self.sources = []

        # initialize the system message
        sys_msg = ChatMessage(role='system', content=SYSTEM_PROMPT_MANUAL_QA_AGENT)
        self.memory.put(sys_msg)

    @step()
    async def agent_director(self, ev: StartEvent, ctx: Context) -> StopEvent:
        # Signal initial processing
        ctx.write_event_to_stream(InitialProcessingEvent(msg="Starting query processing..."))
        
        # clear sources
        self.sources = []

        # get user input
        if isinstance(ev, StartEvent):
            user_input = ev.input

        # Signal retrieval start
        ctx.write_event_to_stream(RetrievalEvent(msg="Retrieving relevant documents..."))
        
        # Get relevant documents
        nodes_reranked, nodes_embed = retrieve_pages(user_input)

        industrial_technical_documentation_extract = "<technical_documentation_extract> \n\n"
        image_paths = []
        for node in nodes_reranked:
            industrial_technical_documentation_extract += f"Page_{node.node.metadata['page_number']}: \n {node.node.text}\n\n"
            image_paths.extend(node.node.metadata['image_paths'])
        industrial_technical_documentation_extract += "</technical_documentation_extract>"

        user_prompt = USER_PROMPT_MANUAL_MULTIMODAL_QA_AGENT.format(
            user_question=user_input,
            industrial_technical_documentation_extract=industrial_technical_documentation_extract
        )

        # Signal processing before LLM work
        ctx.write_event_to_stream(ProcessingEvent(msg="Processing retrieved information..."))

        # Load and process images
        with open('/Users/delonsaks/Documents/virfold/data/manuals/images_resized/filename_mapping.json', 'r') as f:
            filename_mapping = json.load(f)

        image_paths = [f'/Users/delonsaks/Documents/virfold/data/manuals/images_resized/{filename_mapping[os.path.basename(path)]}' for path in image_paths]
        image_documents = SimpleDirectoryReader(input_files=image_paths).load_data()

        # get chat history and prepare for LLM call
        user_msg = ChatMessage(role='user', content=user_prompt)
        self.memory.put(user_msg)
        chat_history = self.memory.get()

        # Stream LLM response
        response_text = ""
        async for response_chunk in await self.llm_mm.astream_complete(
            prompt=user_prompt,
            image_documents=image_documents
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