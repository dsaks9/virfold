import os
from typing import Any
import asyncio
import logging

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import ToolSelection, FunctionTool
from llama_index.core.workflow import Event
from llama_index.llms.anthropic import Anthropic
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Context

from llama_index.core.agent.workflow import (
    AgentWorkflow,
    FunctionAgent,
)

from agents.prompts.prompts import SYSTEM_PROMPT_CODE_GENERATION_DATA_ANALYST, SYSTEM_PROMPT_CODE_REVIEW_DATA_ANALYST, SYSTEM_PROMPT_REPORT_WRITER

from agents.tools.tool_code_runner import run_python_code, CodeGen

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


# Add logger configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

data_analyst_agent = FunctionAgent(
    name="DataAnalyst",
    description="""This agent is a specialized Python/SQL code generator that creates 
    production-ready code for analyzing thermal sensor data from a TimescaleDB database, 
    with a focus on thermal engineering principles and data analysis best practices.""",
    system_prompt=SYSTEM_PROMPT_CODE_GENERATION_DATA_ANALYST,
    tools=[
        FunctionTool.from_defaults(fn=run_python_code, fn_schema=CodeGen),
    ],
    llm=Anthropic(model="claude-3-5-sonnet-latest"),
    can_handoff_to=['CodeReviewer'],
)

code_review_agent = FunctionAgent(
    name="CodeReviewer",
    description="""This agent is a specialized Python/SQL code reviewer that reviews 
    generated code for analyzing thermal sensor data from a TimescaleDB database, 
    with a focus on thermal engineering principles and data analysis best practices.""",
    system_prompt=SYSTEM_PROMPT_CODE_REVIEW_DATA_ANALYST,
    tools=[
        FunctionTool.from_defaults(fn=run_python_code, fn_schema=CodeGen),
    ],
    llm=Anthropic(model="claude-3-5-sonnet-latest"),
    can_handoff_to=['CodeReviewer', 'ReportWriter'],
)

report_writer_agent = FunctionAgent(
    name="ReportWriter",
    description="""This agent is a specialized report writer that writes a report based on the 
    conversation and it's results.""",
    system_prompt=SYSTEM_PROMPT_REPORT_WRITER,
    llm=Anthropic(model="claude-3-5-sonnet-latest"),
)

workflow_data_analyst = AgentWorkflow(
    agents=[data_analyst_agent, code_review_agent, report_writer_agent],
    root_agent=data_analyst_agent.name,
    timeout=180,
)

if __name__ == "__main__":
    async def main():
        logger.info("Starting data analyst workflow")
        try:
            handler = workflow_data_analyst.run(
                user_msg=(
                    "What happened to the temperature in sensor 1 recently?"
                )
            )
            logger.info("Workflow handler created successfully")
            
            result = await handler
            logger.info("Workflow completed successfully")
            print(result)
            
        except Exception as e:
            logger.error(f"Error during workflow execution: {str(e)}", exc_info=True)
            raise

    asyncio.run(main())