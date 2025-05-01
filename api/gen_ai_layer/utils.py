"""
Utility functions for the Gen AI Layer.
Provides helper functions for common AI tasks.
"""

from typing import List, Dict, Any, Optional, Union
import logging
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os
import json
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def create_embeddings(
    provider: str = "openai",
    model_name: Optional[str] = None,
    **kwargs
):
    """
    Create an embedding model based on the provider.
    
    Args:
        provider: The embedding provider (openai, huggingface)
        model_name: The specific model to use
        **kwargs: Additional parameters for the embedding model
        
    Returns:
        An embedding model instance
    """
    if provider.lower() == "openai":
        return OpenAIEmbeddings(
            model=model_name or "text-embedding-3-small",
            **kwargs
        )
    elif provider.lower() == "huggingface":
        return HuggingFaceEmbeddings(
            model_name=model_name or "sentence-transformers/all-mpnet-base-v2",
            **kwargs
        )
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


def process_document(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    metadata: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    Process a document by splitting it into chunks.
    
    Args:
        text: The document text
        chunk_size: The size of each chunk
        chunk_overlap: The overlap between chunks
        metadata: Optional metadata to add to each chunk
        
    Returns:
        List of Document objects
    """
    # Create text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    # Split text into chunks
    chunks = text_splitter.split_text(text)
    
    # Create Document objects
    documents = []
    for i, chunk in enumerate(chunks):
        doc_metadata = {"chunk_id": i}
        if metadata:
            doc_metadata.update(metadata)
        documents.append(Document(page_content=chunk, metadata=doc_metadata))
    
    return documents


def create_vector_store(
    documents: List[Document],
    embedding_provider: str = "openai",
    embedding_model: Optional[str] = None,
    persist_directory: Optional[str] = None,
    **kwargs
):
    """
    Create a vector store from documents.
    
    Args:
        documents: List of Document objects
        embedding_provider: The embedding provider to use
        embedding_model: The specific embedding model to use
        persist_directory: Optional directory to persist the vector store
        **kwargs: Additional parameters for the embedding model
        
    Returns:
        A FAISS vector store
    """
    # Create embeddings
    embeddings = create_embeddings(
        provider=embedding_provider,
        model_name=embedding_model,
        **kwargs
    )
    
    # Create vector store
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # Persist if directory is provided
    if persist_directory:
        os.makedirs(persist_directory, exist_ok=True)
        vector_store.save_local(persist_directory)
    
    return vector_store


def dataframe_to_documents(
    df: pd.DataFrame,
    content_columns: Union[str, List[str]],
    metadata_columns: Optional[List[str]] = None,
    id_column: Optional[str] = None
) -> List[Document]:
    """
    Convert a pandas DataFrame to a list of Document objects.
    
    Args:
        df: The pandas DataFrame
        content_columns: Column(s) to use as document content
        metadata_columns: Columns to include as metadata
        id_column: Column to use as document ID
        
    Returns:
        List of Document objects
    """
    documents = []
    
    # Convert content_columns to list if it's a string
    if isinstance(content_columns, str):
        content_columns = [content_columns]
    
    # Process each row
    for _, row in df.iterrows():
        # Combine content columns
        content = " ".join(str(row[col]) for col in content_columns if pd.notna(row[col]))
        
        # Create metadata
        metadata = {}
        if id_column and id_column in row:
            metadata["id"] = row[id_column]
        
        if metadata_columns:
            for col in metadata_columns:
                if col in row and pd.notna(row[col]):
                    metadata[col] = row[col]
        
        # Create document
        documents.append(Document(page_content=content, metadata=metadata))
    
    return documents


def json_to_documents(
    json_data: Union[str, Dict, List],
    content_key: str,
    metadata_keys: Optional[List[str]] = None,
    id_key: Optional[str] = None
) -> List[Document]:
    """
    Convert JSON data to a list of Document objects.
    
    Args:
        json_data: JSON data as string, dict, or list
        content_key: Key for document content
        metadata_keys: Keys to include as metadata
        id_key: Key to use as document ID
        
    Returns:
        List of Document objects
    """
    # Parse JSON if it's a string
    if isinstance(json_data, str):
        json_data = json.loads(json_data)
    
    # Convert to list if it's a dict
    if isinstance(json_data, dict):
        json_data = [json_data]
    
    documents = []
    
    # Process each item
    for item in json_data:
        # Get content
        if content_key in item:
            content = item[content_key]
        else:
            logger.warning(f"Content key '{content_key}' not found in item: {item}")
            continue
        
        # Create metadata
        metadata = {}
        if id_key and id_key in item:
            metadata["id"] = item[id_key]
        
        if metadata_keys:
            for key in metadata_keys:
                if key in item:
                    metadata[key] = item[key]
        
        # Create document
        documents.append(Document(page_content=content, metadata=metadata))
    
    return documents


def create_knowledge_graph_from_documents(
    documents: List[Document],
    neo4j_uri: str,
    neo4j_username: str,
    neo4j_password: str,
    database: str = "neo4j",
    node_label: str = "Document",
    relationship_label: str = "RELATED_TO",
    similarity_threshold: float = 0.7,
    embedding_provider: str = "openai",
    embedding_model: Optional[str] = None,
    **kwargs
):
    """
    Create a knowledge graph from documents in Neo4j.
    
    Args:
        documents: List of Document objects
        neo4j_uri: URI for Neo4j database
        neo4j_username: Neo4j username
        neo4j_password: Neo4j password
        database: Neo4j database name
        node_label: Label for document nodes
        relationship_label: Label for relationships
        similarity_threshold: Threshold for creating relationships
        embedding_provider: The embedding provider to use
        embedding_model: The specific embedding model to use
        **kwargs: Additional parameters for the embedding model
        
    Returns:
        Number of nodes and relationships created
    """
    try:
        from langchain_neo4j import Neo4jGraph
        from langchain_neo4j.vectorstores import Neo4jVector
    except ImportError:
        logger.error("langchain_neo4j is required for knowledge graph creation")
        raise ImportError("langchain_neo4j is required for knowledge graph creation")
    
    # Create embeddings
    embeddings = create_embeddings(
        provider=embedding_provider,
        model_name=embedding_model,
        **kwargs
    )
    
    # Create Neo4j vector store
    vector_store = Neo4jVector.from_documents(
        documents,
        embeddings,
        url=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        database=database,
        node_label=node_label,
        embedding_node_property="embedding",
        text_node_property="text",
    )
    
    # Create Neo4j graph
    graph = Neo4jGraph(
        url=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        database=database,
    )
    
    # Create relationships between similar documents
    query = f"""
    MATCH (a:{node_label}), (b:{node_label})
    WHERE id(a) < id(b)
    WITH a, b, gds.similarity.cosine(a.embedding, b.embedding) AS similarity
    WHERE similarity > $threshold
    MERGE (a)-[r:{relationship_label}]->(b)
    SET r.similarity = similarity
    RETURN count(r) as relationships_created
    """
    
    result = graph.query(query, {"threshold": similarity_threshold})
    relationships_created = result[0]["relationships_created"] if result else 0
    
    # Count nodes
    node_count_query = f"MATCH (n:{node_label}) RETURN count(n) as node_count"
    node_result = graph.query(node_count_query)
    node_count = node_result[0]["node_count"] if node_result else 0
    
    return {
        "nodes_created": node_count,
        "relationships_created": relationships_created
    }
