import os
from typing import Any
import asyncio
import logging
import nest_asyncio

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import ToolSelection, FunctionTool
from llama_index.core.workflow import Event
from llama_index.llms.anthropic import Anthropic
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Context

from agents.prompts.prompts import SYSTEM_PROMPT_CODE_GENERATION_DATA_ANALYST, SYSTEM_PROMPT_CODE_REVIEW_DATA_ANALYST

from agents.tools.tool_code_runner import run_python_code, CodeGen

# # Add Phoenix
# # OpenTelemetry and instrumentation setup
# from opentelemetry.sdk import trace as trace_sdk
# from opentelemetry import trace as trace_api
# from opentelemetry.sdk.trace.export import SimpleSpanProcessor
# from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
# from openinference.semconv.resource import ResourceAttributes
# from opentelemetry.sdk.resources import Resource
# from openinference.instrumentation import using_attributes

# os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = "api_key=079a4421d673df9aa72:aad28a7"
# os.environ["PHOENIX_CLIENT_HEADERS"] = "api_key=079a4421d673df9aa72:aad28a7"
# os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "https://app.phoenix.arize.com"
# os.environ['PHOENIX_PROJECT_NAME'] = "agent_data_analyst"

# span_phoenix_processor = SimpleSpanProcessor(HTTPSpanExporter(endpoint="https://app.phoenix.arize.com/v1/traces"))

# # Add them to the tracer
# resource = Resource(attributes={ResourceAttributes.PROJECT_NAME: os.environ['PHOENIX_PROJECT_NAME']})
# tracer_provider = trace_sdk.TracerProvider(resource=resource)
# tracer_provider.add_span_processor(span_processor=span_phoenix_processor)


# # Instrument the application
# LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

nest_asyncio.apply()  # Allows nested event loops

class InputEvent(Event):
    input: list[ChatMessage]

class ToolCallEvent(Event):
    tool_calls: list[ToolSelection]

class ValidationEvent(Event):
    validation_input: list[ChatMessage]

def setup_logger():
    """Configure logging for the agent."""
    logger = logging.getLogger("data_analyst_agent")
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
        
    # Create console handler with a higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    
    return logger

logger = setup_logger()


class DataAnalystAgent(Workflow):
    def __init__(self,
                 *args: Any,
                 **kwargs: Any) -> None:
        
        super().__init__(*args, **kwargs)

        self.tools = [
            FunctionTool.from_defaults(run_python_code, fn_schema=CodeGen),
        ]

        model = 'claude-3-5-sonnet-latest'
        self.llm = Anthropic(
            model=model, 
            max_tokens=4096,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            system_prompt=SYSTEM_PROMPT_CODE_GENERATION_DATA_ANALYST
        )

        self.memory = ChatMemoryBuffer.from_defaults(llm=self.llm)
        self.sources = []

        sys_msg = ChatMessage(role='system', content=SYSTEM_PROMPT_CODE_GENERATION_DATA_ANALYST)
        self.memory.put(sys_msg)

    @step()
    async def initial_code_generation(self, ev: StartEvent) -> ToolCallEvent | StopEvent:
        # clear sources - seems like may be redundant
        self.sources = []

        # get user input
        user_input = ev.input

        user_msg = ChatMessage(role='user', content=user_input)
        self.memory.put(user_msg)

        # get chat history
        chat_history = self.memory.get()

        # call llm with chat history and tools
        response = await self.llm.achat_with_tools(self.tools, chat_history=chat_history)

        # put that new response into memory
        self.memory.put(response.message)

        tool_calls = self.llm.get_tool_calls_from_response(response, error_on_no_tool_call=False)

        if not tool_calls:
            return StopEvent(
                result={"response": response} # can access this dict from final output
            )
        else:
            return ToolCallEvent(tool_calls=tool_calls)
        

    @step()
    async def handle_tool_call(self, ev: ToolCallEvent, ctx: Context) -> ValidationEvent:
        logger.info("Processing tool calls")
        tool_calls = ev.tool_calls
        tools_by_name = {tool.metadata.get_name(): tool for tool in self.tools}

        tool_msgs = []

        for tool_call in tool_calls:
            logging.info(f"Processing tool call: {tool_call.tool_name}")
            tool = tools_by_name.get(tool_call.tool_name)
            additional_kwargs = {
                "tool_call_id": tool_call.tool_id,
                "name": tool.metadata.get_name() if tool else "Unknown",
            }

            if not tool:
                logging.warning(f"Tool {tool_call.tool_name} does not exist")
                tool_msgs.append(
                    ChatMessage(
                        role="tool",
                        content = f"Tool {tool_call.tool_name} does not exist",
                        additional_kwargs=additional_kwargs
                    )
                )
                continue

            try:
                logging.info(f"Executing tool: {tool.metadata.get_name()}")
                tool_output = tool(**tool_call.tool_kwargs)
                logger.info(f"Tool output: {tool_output}")
                tool_msgs.append(ChatMessage(
                        role="tool",
                        content=tool_output.content,
                        additional_kwargs=additional_kwargs
                    ))
                
                logging.info("Adding tool messages to memory")
                for msg in tool_msgs:
                    self.memory.put(msg)

                chat_history = self.memory.get()
                logging.info("Returning ValidationEvent")
                return ValidationEvent(validation_input=chat_history)
 
            except Exception as e:
                logging.error(f"Tool execution failed: {str(e)}", exc_info=True)
                tool_msgs.append(
                    ChatMessage(
                        role="tool",
                        content=f"Tool {tool.metadata.get_name()} failed to execute: {e}",
                        additional_kwargs=additional_kwargs
                    )
                )

                logging.info("Adding error messages to memory")
                for msg in tool_msgs:
                    self.memory.put(msg)

                chat_history = self.memory.get()
                logging.info("Returning ValidationEvent after error")
                return ValidationEvent(validation_input=chat_history)

        logging.warning("No tool calls were processed")
        return ValidationEvent(validation_input=self.memory.get())


    @step()
    async def validate_code(self, ev: ValidationEvent, ctx: Context) -> ToolCallEvent | StopEvent:
        # add in code review prompt
        code_review_messages = [ChatMessage(role='system', content=SYSTEM_PROMPT_CODE_REVIEW_DATA_ANALYST)]
        code_review_messages.extend(ev.validation_input)

        # this step is where the code review happens
        try:
            response = await self.llm.achat_with_tools(self.tools, chat_history=code_review_messages)
        except Exception as e:
            logging.error(f"Code review failed: {str(e)}", exc_info=True)
            # Handle the error appropriately, e.g., return a StopEvent or raise an error
            return StopEvent(result={"response": "Please refine your query and try again."})

        # put that new response into memory
        self.memory.put(response.message)

        tool_calls = self.llm.get_tool_calls_from_response(response, error_on_no_tool_call=False)

        if not tool_calls:
            return StopEvent(
                result={"response": response} # can access this dict from final output
            )
        else:
            return ToolCallEvent(tool_calls=tool_calls)

if __name__ == "__main__":
    # Create the agent outside of an async context
    agent = DataAnalystAgent(timeout=180)
    query = "What happened to the temperature in sensor 1 recently?"
    
    async def main():
        logger.info("Starting main application")
        handler = agent.run(input=query)
        result = await handler
        print(result['response'].message.content)

    # Single event loop
    asyncio.run(main())