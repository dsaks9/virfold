import os
from typing import Any
import asyncio
import logging

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import ToolSelection, FunctionTool
from llama_index.core.workflow import Event
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Context

from agents.prompts.prompts import SYSTEM_PROMPT_INSULATION_AGENT, USER_PROMPT_INSULATION_AGENT, SYSTEM_PROMPT_CODE_GENERATION_CALCULATION_PLAN, SYSTEM_PROMPT_CODE_GENERATION_REVIEW_CALCULATION_PLAN

from agents.tools.tools_agent_insulation import generate_code, CodeGen

# Add Phoenix
# OpenTelemetry and instrumentation setup
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from openinference.semconv.resource import ResourceAttributes
from opentelemetry.sdk.resources import Resource
from openinference.instrumentation import using_attributes

os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = "api_key=079a4421d673df9aa72:aad28a7"
os.environ["PHOENIX_CLIENT_HEADERS"] = "api_key=079a4421d673df9aa72:aad28a7"
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "https://app.phoenix.arize.com"
os.environ['PHOENIX_PROJECT_NAME'] = "agent_insulation_streaming"

span_phoenix_processor = SimpleSpanProcessor(HTTPSpanExporter(endpoint="https://app.phoenix.arize.com/v1/traces"))

# Add them to the tracer
resource = Resource(attributes={ResourceAttributes.PROJECT_NAME: os.environ['PHOENIX_PROJECT_NAME']})
tracer_provider = trace_sdk.TracerProvider(resource=resource)
tracer_provider.add_span_processor(span_processor=span_phoenix_processor)


# Instrument the application
LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

# Custom events for streaming
class InitialProcessingEvent(Event):
    content: str

class ProvidedParametersEvent(Event):
    content: str

class RequiredParametersEvent(Event):
    content: str

class AssumptionsEvent(Event):
    content: str

class CalculationPlanStreamlitEvent(Event):
    content: str

class ProgressEvent(Event):
    content: str

class CalculationPlanEvent(Event):
    calculation_plan: str

class ValidationEvent(Event):
    validation_input: list[ChatMessage]

class ToolCallEvent(Event):
    tool_calls: list[ToolSelection]

def setup_logger():
    """Configure logging for the agent."""
    logger = logging.getLogger("insulation_agent")
    
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

class InsulationAgent(Workflow):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        logger.info("Initializing InsulationAgent with configuration:")
        
        # initialize the LLM
        model = 'o1-preview-2024-09-12'
        self.llm = OpenAI(
            model=model, 
            max_completion_tokens=4096,
            api_key=os.getenv("OPENAI_API_KEY"),
            system_prompt=SYSTEM_PROMPT_INSULATION_AGENT
        )
        logger.info(f"Initialized OpenAI LLM with model: {model}")

        model = 'claude-3-5-sonnet-latest'
        self.llm_code_generation = Anthropic(
            model=model, 
            max_tokens=4096,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            system_prompt=SYSTEM_PROMPT_CODE_GENERATION_CALCULATION_PLAN
        )

        model = 'claude-3-5-sonnet-latest'
        self.llm_code_generation_review = Anthropic(
            model=model, 
            max_tokens=4096,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            system_prompt=SYSTEM_PROMPT_CODE_GENERATION_REVIEW_CALCULATION_PLAN
        )

        # initialize the tools
        self.tools = [
            FunctionTool.from_defaults(generate_code, fn_schema=CodeGen),
        ]

        # initialize the memory
        self.memory = ChatMemoryBuffer.from_defaults(llm=self.llm)

        # # initialize the system message
        # message_system_prompt = ChatMessage(role='system', content=SYSTEM_PROMPT_INSULATION_AGENT)
        # self.memory.put(message_system_prompt)

        # # initialize the system message for code generation
        # self.system_prompt_code_generation = SYSTEM_PROMPT_CODE_GENERATION
        

    @step()
    async def agent_director(self, ev: StartEvent, ctx: Context) -> CalculationPlanEvent:
        logger.info("Starting agent director workflow")
        
        design_parameters = ev.input if isinstance(ev, StartEvent) else None
        logger.debug(f"Received design parameters: {design_parameters}")
        
        # Signal initial processing
        ctx.write_event_to_stream(InitialProcessingEvent(content="Starting query processing..."))

        user_prompt = USER_PROMPT_INSULATION_AGENT.format(
            design_parameters=design_parameters,
        )

        # get chat history and prepare for LLM call
        user_msg = ChatMessage(role='user', content=user_prompt)
        self.memory.put(user_msg)

        logger.debug(f"Processing user input: {design_parameters}")

        # Stream LLM response
        full_response = ""  # Keep track of complete response
        section_response = ""  # For section processing
        current_section = None
        
        logger.info("Starting Calculation Plan generation")
        try:
            async for response_chunk in await self.llm.astream_complete(prompt=user_prompt):
                delta = response_chunk.delta
                full_response += delta  # Add to complete response
                # section_response += delta  # Add to section processing

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
                            "calculation_plan": CalculationPlanStreamlitEvent,
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
                logger.debug(f"Processing section: {current_section}" if current_section else "Processing response chunk")

            # Store final response in memory
            assistant_msg = ChatMessage(role='assistant', content=full_response)
            self.memory.put(assistant_msg)

            logger.info("Completed LLM stream processing successfully")

            return CalculationPlanEvent(
                calculation_plan=full_response
                )

        except Exception as e:
            logger.error(f"Error during LLM streaming: {str(e)}", exc_info=True)
            raise

        # return StopEvent(
        #     result={
        #         "response": full_response,  # Return the complete response
        #     }
        # ) 
    
    @step()
    async def generate_code(self, ev: CalculationPlanEvent, ctx: Context) -> ToolCallEvent:
        logger.info("Starting code generation step")

        # msg_system = ChatMessage(role='system', content=self.system_prompt_code_generation)
        # self.memory_code_generation.put(msg_system)


        calculation_plan = ev.calculation_plan
        user_prompt = "Now provide the code for the calculation plan."
        msg_calculation_plan = ChatMessage(role='user', content=user_prompt)
        self.memory.put(msg_calculation_plan)
        chat_history = self.memory.get()

        result = await self.llm_code_generation.achat_with_tools(self.tools, chat_history=chat_history)
        logger.info(f"Code generation result: {result}")
        self.memory.put(result.message)

        tool_calls = self.llm_code_generation.get_tool_calls_from_response(result, error_on_no_tool_call=False)
        logger.info(f"Tool calls: {tool_calls}")

        if not tool_calls:
            return StopEvent(
                result={"response": result} # can access this dict from final output
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
        code_review_messages = [ChatMessage(role='system', content=SYSTEM_PROMPT_CODE_GENERATION_REVIEW_CALCULATION_PLAN)]
        code_review_messages.extend(ev.validation_input)

        # this step is where the code review happens
        try:
            response = await self.llm_code_generation.achat_with_tools(self.tools, chat_history=code_review_messages)
        except Exception as e:
            logging.error(f"Code review failed: {str(e)}", exc_info=True)
            # Handle the error appropriately, e.g., return a StopEvent or raise an error
            return StopEvent(result={"response": "Please refine your query and try again."})

        # put that new response into memory
        self.memory.put(response.message)

        tool_calls = self.llm_code_generation.get_tool_calls_from_response(response, error_on_no_tool_call=False)

        if not tool_calls:
            return StopEvent(
                result={"response": response} # can access this dict from final output
            )
        else:
            return ToolCallEvent(tool_calls=tool_calls)





if __name__ == "__main__":
    async def run_agent_with_stream(agent, query: str):
        logger.info("Starting agent stream")
        """Run the agent and yield streaming events."""
        handler = agent.run(input=query)
        async for event in handler.stream_events():
            yield event
        
        # Get the final result and yield it as a StopEvent
        result = await handler
        yield result

    async def main():
        logger.info("Starting main application")
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
            # elif isinstance(event, ProgressEvent):
            #     chunk = event.content
            #     full_response += chunk
                # Uncomment to see streaming progress
                # print("\n\n\n", f"Full Response: {full_response}", "\n\n\n")

    # Run the async main function
    asyncio.run(main())