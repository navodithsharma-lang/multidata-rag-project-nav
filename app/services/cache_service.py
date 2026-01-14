"""
Cache Service
Manages caching of document chunks and embeddings to avoid redundant processing.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("rag_app.cache_service")


class CacheService:
    """
    Manages caching of document chunks and embeddings.
    Uses content-based SHA-256 hashing for true deduplication.
    """

    def __init__(self, cache_dir: Path):
        """
        Initialize cache service.

        Args:
            cache_dir: Directory to store cached data (e.g., data/cached_chunks/)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache service initialized at: {self.cache_dir}")

    def compute_document_id(self, file_path: Path) -> str:
        """
        Generate unique document ID from file contents using SHA-256.
        Same file = same ID (true content-based deduplication).

        Args:
            file_path: Path to the document file

        Returns:
            64-character hexadecimal SHA-256 hash

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        sha256 = hashlib.sha256()

        # Read file in chunks to handle large files efficiently
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        doc_id = sha256.hexdigest()
        logger.debug(f"Computed document ID: {doc_id} for {file_path.name}")
        return doc_id

    def _get_cache_path(self, doc_id: str) -> Path:
        """Get the cache directory path for a document ID."""
        return self.cache_dir / doc_id

    def cache_exists(self, doc_id: str) -> bool:
        """
        Check if valid cache exists for document ID.
        Requires all three files: chunks.json, embeddings.npy, metadata.json

        Args:
            doc_id: Document ID (SHA-256 hash)

        Returns:
            True if complete cache exists, False otherwise
        """
        cache_path = self._get_cache_path(doc_id)

        if not cache_path.exists():
            return False

        # Check all required files exist
        required_files = ['chunks.json', 'embeddings.npy', 'metadata.json']
        for filename in required_files:
            if not (cache_path / filename).exists():
                logger.warning(f"Cache incomplete for {doc_id}: missing {filename}")
                return False

        return True

    def save_chunks_and_embeddings(
        self,
        doc_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        metadata: Dict[str, Any]
    ) -> None:
        """
        Save chunks, embeddings, and metadata to cache.

        Args:
            doc_id: Document ID (SHA-256 hash)
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors (N x 1536)
            metadata: Document metadata (filename, timestamp, etc.)

        Raises:
            ValueError: If chunks and embeddings length mismatch
            Exception: If save operation fails
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunk/embedding mismatch: {len(chunks)} chunks, {len(embeddings)} embeddings"
            )

        cache_path = self._get_cache_path(doc_id)
        cache_path.mkdir(parents=True, exist_ok=True)

        try:
            # Save chunks as JSON
            chunks_file = cache_path / 'chunks.json'
            with open(chunks_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=2, ensure_ascii=False)

            # Save embeddings as NumPy binary array (float32 for efficiency)
            embeddings_file = cache_path / 'embeddings.npy'
            embeddings_array = np.array(embeddings, dtype=np.float32)
            np.save(embeddings_file, embeddings_array)

            # Save metadata as JSON
            metadata_file = cache_path / 'metadata.json'
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Log cache size
            total_size = sum(
                f.stat().st_size for f in cache_path.iterdir() if f.is_file()
            )
            logger.info(
                f"Cached {len(chunks)} chunks for {doc_id} "
                f"({total_size / 1024:.1f} KB total)"
            )

        except Exception as e:
            # Clean up partial cache on failure
            if cache_path.exists():
                import shutil
                shutil.rmtree(cache_path, ignore_errors=True)
            raise Exception(f"Failed to save cache: {str(e)}")

    def load_chunks_and_embeddings(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Load cached chunks and embeddings.

        Args:
            doc_id: Document ID (SHA-256 hash)

        Returns:
            Dictionary with 'chunks', 'embeddings', and 'metadata' keys,
            or None if cache doesn't exist or is corrupted

        Note:
            Returns None on any error (graceful degradation)
        """
        if not self.cache_exists(doc_id):
            return None

        cache_path = self._get_cache_path(doc_id)

        try:
            # Load chunks
            chunks_file = cache_path / 'chunks.json'
            with open(chunks_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)

            # Load embeddings
            embeddings_file = cache_path / 'embeddings.npy'
            embeddings_array = np.load(embeddings_file)
            embeddings = embeddings_array.tolist()  # Convert to list for consistency

            # Load metadata
            metadata_file = cache_path / 'metadata.json'
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Validate consistency
            if len(chunks) != len(embeddings):
                logger.error(
                    f"Cache corruption: {len(chunks)} chunks but {len(embeddings)} embeddings"
                )
                return None

            logger.info(f"Loaded {len(chunks)} chunks from cache for {doc_id}")

            return {
                'chunks': chunks,
                'embeddings': embeddings,
                'metadata': metadata
            }

        except Exception as e:
            logger.warning(f"Failed to load cache for {doc_id}: {str(e)}")
            return None

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with:
                - total_documents: Number of cached documents
                - total_size_bytes: Total cache size in bytes
                - total_size_mb: Total cache size in MB
                - document_ids: List of cached document IDs
        """
        if not self.cache_dir.exists():
            return {
                'total_documents': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0.0,
                'document_ids': []
            }

        # Find all cache directories
        cache_dirs = [d for d in self.cache_dir.iterdir() if d.is_dir()]
        document_ids = [d.name for d in cache_dirs]

        # Calculate total size
        total_size = 0
        for cache_dir in cache_dirs:
            for file in cache_dir.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size

        return {
            'total_documents': len(document_ids),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'document_ids': document_ids
        }

    def clear_cache(self, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear cache for specific document or entire cache.

        Args:
            doc_id: Document ID to clear, or None to clear all cache

        Returns:
            Dictionary with:
                - cleared: Boolean success status
                - message: Description of what was cleared
                - documents_cleared: Number of documents cleared
        """
        import shutil

        try:
            if doc_id:
                # Clear specific document
                cache_path = self._get_cache_path(doc_id)
                if cache_path.exists():
                    shutil.rmtree(cache_path)
                    logger.info(f"Cleared cache for document: {doc_id}")
                    return {
                        'cleared': True,
                        'message': f'Cleared cache for document {doc_id}',
                        'documents_cleared': 1
                    }
                else:
                    return {
                        'cleared': False,
                        'message': f'No cache found for document {doc_id}',
                        'documents_cleared': 0
                    }
            else:
                # Clear entire cache
                stats = self.get_cache_stats()
                doc_count = stats['total_documents']

                if self.cache_dir.exists():
                    shutil.rmtree(self.cache_dir)
                    self.cache_dir.mkdir(parents=True, exist_ok=True)

                logger.info(f"Cleared entire cache ({doc_count} documents)")
                return {
                    'cleared': True,
                    'message': f'Cleared entire cache',
                    'documents_cleared': doc_count
                }

        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
            return {
                'cleared': False,
                'message': f'Failed to clear cache: {str(e)}',
                'documents_cleared': 0
            }
