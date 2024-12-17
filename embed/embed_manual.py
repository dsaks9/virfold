import json
import os
import time
from pathlib import Path
from llama_index.core import Settings, Document, VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.nvidia import NVIDIAEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding

from llama_index.core.node_parser import SentenceSplitter

from qdrant_client import QdrantClient

def load_manual_pages(json_path):
    """
    Load manual pages from JSON file and return a dictionary mapping page numbers to page content.
    
    Args:
        json_path (str): Path to the JSON file containing manual data
        
    Returns:
        dict: Dictionary with page numbers as keys and page content as values
    """
    import json
    
    # Initialize pages dictionary
    pages_dict = {}
    
    try:
        # Load JSON file
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        # Extract pages from first document
        if data and isinstance(data, list) and len(data) > 0:
            document = data[0]
            
            # Process each page
            for page in document.get('pages', []):
                page_number = page.get('page')
                if page_number is not None:
                    # Create page content dictionary with relevant fields
                    page_content = {
                        'text': page.get('text', ''),
                        'markdown': page.get('md', ''),
                        'images': page.get('images', []),
                        'charts': page.get('charts', []),
                        'items': page.get('items', []),
                        'links': page.get('links', []),
                        'width': page.get('width'),
                        'height': page.get('height'),
                        'status': page.get('status')
                    }
                    pages_dict[page_number] = page_content
                    
        return pages_dict
        
    except Exception as e:
        print(f"Error loading manual pages: {str(e)}")
        return {}

def create_documents_from_manual(json_path: str) -> list[Document]:
    """
    Create LlamaIndex Documents from manual pages JSON data.
    
    Args:
        json_path (str): Path to the JSON file containing manual data
        
    Returns:
        list[Document]: List of LlamaIndex Document objects
    """
    print(f"\nAttempting to create documents from manual pages at {json_path}")
    documents = []
    
    # Load the manual pages
    pages_dict = load_manual_pages(json_path)
    
    try:
        for page_number, page_content in pages_dict.items():
            print(f"\nProcessing page {page_number}")
            
            image_paths = [image['path'] for image in page_content.get('images', []) if image.get('type') != 'full_page_screenshot']

            # Create metadata dictionary
            metadata = {
                'page_number': page_number,
                'image_paths': image_paths,
                'links': page_content.get('links', []),
                # 'charts': page_content.get('charts', []),
                # 'items': page_content.get('items', []),
            }
            
            # Combine text and markdown content
            content = page_content.get('markdown', '')
            
            # Create Document object
            document = Document(
                text=content,
                metadata=metadata,
                excluded_llm_metadata_keys=list(metadata.keys()),  # Exclude metadata from LLM context
                excluded_embed_metadata_keys=list(metadata.keys()),  # Exclude metadata from embeddings
                metadata_separator="\n",
                metadata_template="{key}: {value}",
                text_template="Page {page_number} Content:\n{content}"
            )
            documents.append(document)
            
        print(f"\nSuccessfully created {len(documents)} documents")
        return documents
        
    except Exception as e:
        print(f"Error creating documents: {str(e)}")
        return []

def embed_documents(documents: list[Document], query_collection_name: str) -> None:
    """
    Embed the documents using Cohere embeddings with retry logic and batch processing.
    """

    # NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
    # nvidia_api_key = NVIDIA_API_KEY

    # # embed model
    # embed_model = NVIDIAEmbedding(
    #     nvidia_api_key=nvidia_api_key,
    #     api_key=nvidia_api_key,
    #     model_name="nvidia/nv-embedqa-e5-v5",
    # )

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    openai_api_key = OPENAI_API_KEY

    embed_model = OpenAIEmbedding(
        model="text-embedding-3-large",
        api_key=openai_api_key,
    )

    Settings.embed_model = embed_model

    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    qdrant_api_key = QDRANT_API_KEY

    # creates a persistant index to disk
    client = QdrantClient(url="https://6eefc541-3b11-47b5-8274-bdc84e60b5b9.us-east-1-0.aws.cloud.qdrant.io:6333",
                          api_key=qdrant_api_key,
                          timeout=3600)

    if client.collection_exists(collection_name=query_collection_name):
        print(f"Collection {query_collection_name} already exists. Deleting...")
        client.delete_collection(collection_name=query_collection_name)

    print('Starting embedding')
    start = time.time()

    # Settings for LlamaIndex
    chunk_size = 4096
    chunk_overlap = 512
    Settings.chunk_size = chunk_size
    Settings.chunk_overlap = chunk_overlap
    Settings.text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Add batch processing
    batch_size = 50  # Adjust this number based on your needs
    max_retries = 5
    base_delay = 60  # 60 seconds wait between retries

    # Process documents in batches
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        
        for attempt in range(max_retries):
            try:
                vector_store = QdrantVectorStore(
                    query_collection_name, 
                    client=client, 
                    enable_hybrid=True, 
                    batch_size=20
                )
                
                storage_context = StorageContext.from_defaults(vector_store=vector_store)

                index = VectorStoreIndex.from_documents(
                    batch,
                    storage_context=storage_context,
                    transformations=[SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)]
                )
                
                print(f"Successfully processed batch {i//batch_size + 1}")
                break  # Success, move to next batch
                
            except Exception as e:
                if "rate limit exceeded" in str(e).lower():
                    if attempt < max_retries - 1:  # Don't sleep on the last attempt
                        wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                        print(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                    else:
                        print(f"Failed to process batch after {max_retries} attempts")
                        raise
                else:
                    print(f"Unexpected error: {str(e)}")
                    raise


def main():
    print("\nStarting main function...")
    start_time = time.time()
    
    # Define the paths to your JSON files
    json_path = Path("/Users/delonsaks/Documents/virfold/data/manuals/parsed_manual.json")
    
    # Create Documents from manual
    print("\nStarting document creation...")
    documents = create_documents_from_manual(str(json_path))  # Pass the path string directly
    print(f"Created {len(documents)} Documents")
    
    if documents:
        print("\nFirst document:")
        print(f"Text: {documents[0].text[:200]}...")
        print(f"Metadata: {documents[0].metadata}")
        
        query_collection_name = "danfos_service_manual_2024_v1"
        
        # Start embedding process
        print("\nStarting embedding process...")
        try:
            embed_documents(documents, query_collection_name)
            print("Successfully completed embedding process!")
        except Exception as e:
            print(f"Error during embedding: {str(e)}")

    # Calculate and print execution time
    execution_time = time.time() - start_time
    print(f"\nTotal execution time: {execution_time:.2f} seconds")

if __name__ == "__main__":
    main()