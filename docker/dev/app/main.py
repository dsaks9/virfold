from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
import os

# OpenTelemetry setup
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
from opentelemetry.sdk.resources import Resource
from openinference.semconv.resource import ResourceAttributes
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

# Import routers
from routers import data_analyst

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Phoenix configuration
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = "api_key=3d95169888287871fcd:7bdc2f8"
os.environ["PHOENIX_CLIENT_HEADERS"] = "api_key=3d95169888287871fcd:7bdc2f8"
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "https://app.phoenix.arize.com"
os.environ['PHOENIX_PROJECT_NAME'] = "app_api"

span_phoenix_processor = SimpleSpanProcessor(HTTPSpanExporter(endpoint="https://app.phoenix.arize.com/v1/traces"))

# Add them to the tracer
resource = Resource(attributes={ResourceAttributes.PROJECT_NAME: os.environ['PHOENIX_PROJECT_NAME']})
tracer_provider = trace_sdk.TracerProvider(resource=resource)
tracer_provider.add_span_processor(span_processor=span_phoenix_processor)

# Instrument the application
LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting up API")
    yield
    logger.info("Shutting down API")
    await data_analyst.cleanup_sessions()

app = FastAPI(
    title="Data Analysis API",
    description="API endpoints for data analysis using LlamaIndex workflow agents",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    data_analyst.router,
    prefix="/data-analyst",
    tags=["Data Analyst"]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"} 