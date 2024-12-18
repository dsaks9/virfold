import nest_asyncio
from typing import Any
import boto3
import json
import asyncio
import os

from llama_index.core.llms import ChatMessage
from llama_index.core import SimpleDirectoryReader
from llama_index.core.tools import ToolSelection, ToolOutput
from llama_index.core.workflow import Event
from llama_index.core.tools import FunctionTool
from llama_index.multi_modal_llms.anthropic import AnthropicMultiModal
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools.types import BaseTool
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Context

from retrievers.retriever_baseline import retrieve_pages

from agent.prompts.prompts import SYSTEM_PROMPT_MANUAL_QA_AGENT, USER_PROMPT_MANUAL_MULTIMODAL_QA_AGENT

# from prompts.prompts import SYSTEM_PROMPT_SUBSIDY_REPORT_AGENT

# from tools.tool_query_subsidies import query_subsidies, SubsidyReportParameters


class InputEvent(Event):
    input: list[ChatMessage]

class ToolCallEvent(Event):
    tool_calls: list[ToolSelection]


class ManualQueryAgent(Workflow):
    def __init__(self, *args: Any, **kwargs: Any) -> None:

        super().__init__(*args, **kwargs)

        # initialize the LLM
        model = 'claude-3-5-sonnet-20240620'
        self.llm_mm = AnthropicMultiModal(model=model, 
                                          max_tokens=4096,
                                          api_key=os.getenv("ANTHROPIC_API_KEY"),
                                          system_prompt=SYSTEM_PROMPT_MANUAL_QA_AGENT)


        # initialize the memory
        self.memory = ChatMemoryBuffer.from_defaults(llm=self.llm_mm)
        self.sources = []

        # initialize the system message
        sys_msg = ChatMessage(role='system', content=SYSTEM_PROMPT_MANUAL_QA_AGENT)
        self.memory.put(sys_msg)


    @step()
    async def agent_director(self, ev: StartEvent) ->  StopEvent:
        # clear sources - seems like may be redundant
        self.sources = []

        # get user input
        if isinstance(ev, StartEvent):
            user_input = ev.input


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

        with open('/Users/delonsaks/Documents/virfold/data/manuals/images_resized/filename_mapping.json', 'r') as f:
            filename_mapping = json.load(f)

        image_paths = [f'/Users/delonsaks/Documents/virfold/data/manuals/images_resized/{filename_mapping[os.path.basename(path)]}' for path in image_paths]

        image_documents = SimpleDirectoryReader(input_files=image_paths).load_data()

        # get chat history
        user_msg = ChatMessage(role='user', content=user_prompt)
        self.memory.put(user_msg)
        chat_history = self.memory.get()

        # call llm with chat history and tools
        response = await self.llm_mm.acomplete(prompt=user_prompt, 
                                              image_documents=image_documents)

        # put that new response into memory
        self.memory.put(response.text)

        return StopEvent(
            result={"response": response.text, 
                    # "sources": [*self.sources]
                    } # can access this dict from final output
        )
    
if __name__ == "__main__":
    async def main():
        w = ManualQueryAgent(timeout=120, verbose=True)
        result = await w.run(input="Is there any information from the suppliers on the compressors being used?")
        print(str(result))

    # Run the async main function
    asyncio.run(main())