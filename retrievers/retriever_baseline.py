import os
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import Settings, Document, VectorStoreIndex, StorageContext
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.core.schema import NodeWithScore

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, MatchAny

### tracing ###

from phoenix.otel import register
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
# Add Phoenix API Key for tracing
PHOENIX_API_KEY = os.getenv('PHOENIX_API_KEY')
os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={PHOENIX_API_KEY}"

# configure the Phoenix tracer
tracer_provider = register(
  project_name="my-llm-app", # Default is 'default'
  endpoint="https://app.phoenix.arize.com/v1/traces",
)

LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

### end tracing ###

def retrieve_pages(user_input):

    # embed model
    embed_model = OpenAIEmbedding(
        model="text-embedding-3-large",
        api_key=os.getenv('OPENAI_API_KEY'),
    )
    Settings.embed_model = embed_model

    postprocessor = CohereRerank(
        top_n=5,
        model="rerank-v3.5",
        api_key=os.getenv('COHERE_API_KEY'),
    )

    client = QdrantClient(url="https://6eefc541-3b11-47b5-8274-bdc84e60b5b9.us-east-1-0.aws.cloud.qdrant.io:6333",
                          api_key=os.getenv('QDRANT_API_KEY'),
                          timeout=3600)
    
    query_collection_name = "danfos_service_manual_2024_v1"
    vector_store = QdrantVectorStore(
                query_collection_name, 
                client=client, 
                enable_hybrid=True)

    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

    retriever = index.as_retriever(similarity_top_k=25)
    nodes_embed = retriever.retrieve(user_input)
    nodes_reranked = postprocessor.postprocess_nodes(nodes=nodes_embed, query_str=user_input)

    return nodes_reranked, nodes_embed


if __name__ == "__main__":

    user_input = """ Is there any information from the suppliers on the compressors being used?"""

    if not user_input:
        user_input = input("Please enter your subsidy query: ")

    nodes_reranked, nodes_embed = retrieve_pages(user_input)
