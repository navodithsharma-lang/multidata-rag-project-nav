"""
Multi-Source RAG + Text-to-SQL API
FastAPI application with document RAG and natural language to SQL capabilities.
"""

from fastapi import FastAPI, status, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
from pathlib import Path
import sys
import shutil

from app.config import settings
from app.services.document_service import parse_document, chunk_text
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.services.rag_service import RAGService
from app.services.sql_service import TextToSQLService

app = FastAPI(
    title="Multi-Source RAG + Text-to-SQL API",
    description="A system that combines document RAG with natural language to SQL conversion",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Global service instances (initialized on startup if API keys are available)
embedding_service: EmbeddingService | None = None
vector_service: VectorService | None = None
rag_service: RAGService | None = None
sql_service: TextToSQLService | None = None

# Upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.

    Returns:
        dict: Status information including timestamp and service state
    """
    return {
        "status": "healthy",
        "service": "Multi-Source RAG + Text-to-SQL API",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
    }


@app.get("/info", status_code=status.HTTP_200_OK, tags=["Information"])
async def get_info():
    """
    Get system information and configuration details.

    Returns:
        dict: System information including Python version, environment, and features
    """
    return {
        "application": {
            "name": "Multi-Source RAG + Text-to-SQL",
            "version": "0.1.0",
            "environment": "development",  # Will be loaded from settings once .env exists
        },
        "features": {
            "document_rag": "Available - Phase 1 Complete",
            "text_to_sql": "Available - Phase 2 Complete",
            "query_routing": "Pending implementation - Phase 3",
            "evaluation": "Pending implementation - Phase 4",
        },
        "system": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "info": "/info",
            "upload_document": "POST /upload",
            "query_documents": "POST /query/documents",
            "list_documents": "GET /documents",
            "generate_sql": "POST /query/sql/generate",
            "execute_sql": "POST /query/sql/execute",
            "pending_sql_queries": "GET /query/sql/pending",
        },
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with welcome message and quick links.

    Returns:
        dict: Welcome message and navigation links
    """
    return {
        "message": "Welcome to Multi-Source RAG + Text-to-SQL API",
        "version": "0.1.0",
        "status": "Phase 0 Complete - Development Ready",
        "documentation": "/docs",
        "health_check": "/health",
        "system_info": "/info",
    }


@app.post("/upload", status_code=status.HTTP_201_CREATED, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document (PDF, DOCX, CSV, JSON).
    Pipeline: save → parse → chunk → embed → store in Pinecone

    Args:
        file: The document file to upload

    Returns:
        dict: Upload status with filename and chunks created
    """
    global embedding_service, vector_service

    # Check if services are initialized
    if not embedding_service or not vector_service:
        raise HTTPException(
            status_code=503,
            detail="Services not initialized. Please configure API keys in .env file."
        )

    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse document
        print(f"Parsing document: {file.filename}")
        text = parse_document(str(file_path))

        # Chunk text
        print(f"Chunking text...")
        chunks = chunk_text(text, chunk_size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)

        # Generate embeddings
        print(f"Generating embeddings for {len(chunks)} chunks...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = await embedding_service.generate_embeddings(texts)

        # Store in Pinecone
        print(f"Storing vectors in Pinecone...")
        vector_service.add_documents(
            chunks=chunks,
            embeddings=embeddings,
            filename=file.filename,
            namespace="default"
        )

        return {
            "status": "success",
            "filename": file.filename,
            "file_size_bytes": file_path.stat().st_size,
            "chunks_created": len(chunks),
            "total_tokens": sum(chunk['token_count'] for chunk in chunks),
            "message": f"Document processed and {len(chunks)} chunks stored in Pinecone"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/query/documents", status_code=status.HTTP_200_OK, tags=["Query"])
async def query_documents(question: str, top_k: int = 3):
    """
    Query documents using RAG (Retrieval-Augmented Generation).
    Retrieves relevant chunks and generates an answer using GPT-4.

    Args:
        question: The question to answer
        top_k: Number of document chunks to retrieve (default: 3)

    Returns:
        dict: Generated answer with sources and metadata
    """
    global rag_service

    # Check if service is initialized
    if not rag_service:
        raise HTTPException(
            status_code=503,
            detail="RAG service not initialized. Please configure API keys in .env file."
        )

    try:
        result = await rag_service.generate_answer(
            question=question,
            top_k=top_k,
            namespace="default",
            include_sources=True
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/documents", status_code=status.HTTP_200_OK, tags=["Documents"])
async def list_documents():
    """
    List all uploaded documents.

    Returns:
        dict: List of uploaded documents with metadata
    """
    try:
        documents = []
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                documents.append({
                    "filename": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                    "uploaded_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })

        return {
            "total_documents": len(documents),
            "documents": documents
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@app.post("/query/sql/generate", status_code=status.HTTP_200_OK, tags=["SQL"])
async def generate_sql(question: str):
    """
    Generate SQL from a natural language question using Vanna.ai.
    Returns the SQL for user review and approval before execution.

    Args:
        question: Natural language question about the database

    Returns:
        dict: Generated SQL with query_id for approval
    """
    global sql_service

    if not sql_service:
        raise HTTPException(
            status_code=503,
            detail="SQL service not initialized. Please configure DATABASE_URL in .env file."
        )

    try:
        result = sql_service.generate_sql_for_approval(question)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL generation failed: {str(e)}")


@app.post("/query/sql/execute", status_code=status.HTTP_200_OK, tags=["SQL"])
async def execute_sql(query_id: str, approved: bool = True):
    """
    Execute a previously generated SQL query after user approval.

    Args:
        query_id: ID from the generate_sql endpoint
        approved: Whether to execute (True) or reject (False) the query

    Returns:
        dict: Query results or rejection message
    """
    global sql_service

    if not sql_service:
        raise HTTPException(
            status_code=503,
            detail="SQL service not initialized. Please configure DATABASE_URL in .env file."
        )

    try:
        result = sql_service.execute_approved_query(query_id, approved)

        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('error', 'Unknown error'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL execution failed: {str(e)}")


@app.get("/query/sql/pending", status_code=status.HTTP_200_OK, tags=["SQL"])
async def list_pending_sql_queries():
    """
    List all SQL queries pending approval.

    Returns:
        dict: List of pending queries with their IDs and SQL
    """
    global sql_service

    if not sql_service:
        raise HTTPException(
            status_code=503,
            detail="SQL service not initialized."
        )

    try:
        pending = sql_service.get_pending_queries()
        return {
            "total_pending": len(pending),
            "pending_queries": pending
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pending queries: {str(e)}")


# Event handlers for startup/shutdown
@app.on_event("startup")
async def startup_event():
    """Execute tasks on application startup."""
    global embedding_service, vector_service, rag_service, sql_service

    print("=" * 60)
    print("Starting Multi-Source RAG + Text-to-SQL API...")
    print("=" * 60)
    print("Phase 0: Foundation Setup - COMPLETE")
    print("Phase 1: Document RAG MVP - COMPLETE")
    print("Phase 2: Text-to-SQL Foundation - COMPLETE")
    print("=" * 60)

    # Initialize Document RAG services if API keys are available
    try:
        if settings.OPENAI_API_KEY and settings.PINECONE_API_KEY:
            print("\nInitializing Document RAG services...")
            embedding_service = EmbeddingService()
            vector_service = VectorService()
            vector_service.connect_to_index()
            rag_service = RAGService()
            print("✓ Document RAG services initialized!")
        else:
            print("\nWARNING: OpenAI/Pinecone API keys not configured.")
            print("Document RAG features will be unavailable.")
    except Exception as e:
        print(f"\nWARNING: Failed to initialize RAG services: {e}")
        print("Document RAG features will be unavailable.")

    # Initialize Text-to-SQL service if database is available
    try:
        if settings.DATABASE_URL and settings.OPENAI_API_KEY:
            print("\nInitializing Text-to-SQL service...")
            sql_service = TextToSQLService()
            print("Training Vanna on database schema and examples...")
            sql_service.complete_training()
            print("✓ Text-to-SQL service initialized and trained!")
        else:
            print("\nWARNING: DATABASE_URL not configured.")
            print("Text-to-SQL features will be unavailable.")
    except Exception as e:
        print(f"\nWARNING: Failed to initialize SQL service: {e}")
        print("Text-to-SQL features will be unavailable.")

    print("\n" + "=" * 60)
    print("API is ready! Visit http://localhost:8000/docs")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Execute cleanup tasks on application shutdown."""
    print("Shutting down Multi-Source RAG + Text-to-SQL API...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
