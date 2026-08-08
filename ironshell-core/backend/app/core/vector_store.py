"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    VECTOR STORE MANAGER - THE DATA FLYWHEEL                  ║
║                                                                              ║
║  THIS IS YOUR COMPETITIVE MOAT                                               ║
║                                                                              ║
║  WHY THIS FILE IS THE MOST IMPORTANT IN THE SYSTEM:                          ║
║  1. Every user correction is stored here as an embedding                     ║
║  2. Every new analysis queries here for similar past corrections             ║
║  3. The more corrections, the smarter YOUR AI becomes                        ║
║  4. Competitors can copy code, but NOT your embeddings                       ║
║                                                                              ║
║  THE FLYWHEEL CYCLE:                                                         ║
║  User corrects AI → Embedding stored → Next query retrieves → AI improves    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .config import settings


class VectorStoreManager:
    """
    Manages the ChromaDB vector store for the Data Flywheel.

    IRON SHELL ARCHITECTURE:
    - Uses ChromaDB for local, fast vector similarity search
    - Sentence transformers for embedding generation
    - Stores user corrections with metadata for filtered retrieval

    WHY CHROMADB:
    1. Free and open source
    2. Runs locally (no API costs)
    3. Persistent storage
    4. Fast similarity search
    5. Metadata filtering for domain-specific retrieval
    """

    def __init__(self):
        self.client: Optional[chromadb.Client] = None
        self.collection = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the vector store and embedding model.

        IRON SHELL NOTE:
        We initialize once at startup to avoid repeated model loading.
        The embedding model stays in memory for fast encoding.
        """
        if self._initialized:
            return

        # Create persistence directory if needed
        persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(persist_dir, exist_ok=True)

        # Initialize ChromaDB with persistence
        # ══════════════════════════════════════════════════════════════════════
        # WHY PERSISTENT STORAGE:
        # Your corrections are your competitive advantage. They MUST survive
        # restarts. This is not a cache - it's your proprietary dataset.
        # ══════════════════════════════════════════════════════════════════════
        self.client = chromadb.Client(ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir,
            anonymized_telemetry=False  # Privacy first
        ))

        # Get or create the corrections collection
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={
                "description": "IronShell Data Flywheel - User Corrections",
                "created_at": datetime.utcnow().isoformat(),
                "hnsw:space": "cosine"  # Use cosine similarity
            }
        )

        # Initialize the embedding model
        # ══════════════════════════════════════════════════════════════════════
        # WHY SENTENCE TRANSFORMERS:
        # 1. Free and local (no API costs)
        # 2. all-MiniLM-L6-v2 is small but effective
        # 3. Can upgrade to larger models as needed
        # ══════════════════════════════════════════════════════════════════════
        print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        print(f"✅ Embedding model loaded")

        self._initialized = True
        print(f"✅ Vector store initialized with {self.collection.count()} corrections")

    async def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        if self.client:
            self.client.persist()
            print("✅ Vector store persisted to disk")

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a text string.

        IRON SHELL TIP:
        We embed the ORIGINAL INPUT, not the correction.
        This way, when similar inputs come in, we retrieve the correction.
        """
        if not self.embedding_model:
            raise RuntimeError("Embedding model not initialized")
        return self.embedding_model.encode(text).tolist()

    def _generate_id(self, text: str) -> str:
        """Generate a unique ID for a correction based on content hash."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    async def save_correction(
        self,
        original_input: str,
        ai_output: str,
        user_correction: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a user correction to the vector store.

        THIS IS THE CORE OF THE DATA FLYWHEEL.

        Parameters:
        - original_input: What the user submitted (e.g., trade data)
        - ai_output: What the AI generated (e.g., analysis)
        - user_correction: What the user changed it to (e.g., edited analysis)

        Returns:
        - The ID of the stored correction

        IRON SHELL MECHANIC:
        We embed the original_input so that future similar inputs
        will retrieve this correction and its user_correction.
        """
        if not self._initialized:
            await self.initialize()

        # Generate embedding from the original input
        # ══════════════════════════════════════════════════════════════════════
        # WHY EMBED THE INPUT, NOT THE CORRECTION:
        # We want to find this correction when SIMILAR INPUTS appear.
        # The input is the query key, the correction is the value.
        # ══════════════════════════════════════════════════════════════════════
        embedding = self._generate_embedding(original_input)

        # Generate unique ID
        correction_id = self._generate_id(f"{original_input}:{datetime.utcnow().isoformat()}")

        # Prepare metadata
        doc_metadata = {
            "ai_output": ai_output[:1000],  # Truncate for storage
            "user_correction": user_correction[:2000],
            "correction_timestamp": datetime.utcnow().isoformat(),
            "input_length": len(original_input),
            "output_changed": ai_output != user_correction,
        }

        # Add custom metadata if provided
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    doc_metadata[key] = value
                elif isinstance(value, list):
                    doc_metadata[key] = ",".join(str(v) for v in value)

        # Store in ChromaDB
        # ══════════════════════════════════════════════════════════════════════
        # THE FLYWHEEL SPINS:
        # Every time this runs, your AI gets a little smarter.
        # Your competitors can't copy this data.
        # ══════════════════════════════════════════════════════════════════════
        self.collection.add(
            ids=[correction_id],
            embeddings=[embedding],
            documents=[original_input],
            metadatas=[doc_metadata]
        )

        # Persist to disk
        self.client.persist()

        print(f"💾 Correction saved: {correction_id}")
        print(f"   Flywheel size: {self.collection.count()} corrections")

        return correction_id

    async def query_similar_corrections(
        self,
        input_text: str,
        n_results: int = None,
        min_similarity: float = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar past corrections.

        THIS IS THE RAG RETRIEVAL STEP.

        Parameters:
        - input_text: The new input to find similar corrections for
        - n_results: Number of results to return (default from settings)
        - min_similarity: Minimum similarity threshold (default from settings)
        - filter_metadata: Optional metadata filters

        Returns:
        - List of similar corrections with their metadata

        IRON SHELL MECHANIC:
        Before the AI generates a response, we check if the user has
        ever corrected a similar input. If so, we include that correction
        in the prompt so the AI doesn't make the same mistake.
        """
        if not self._initialized:
            await self.initialize()

        n_results = n_results or settings.RAG_TOP_K
        min_similarity = min_similarity or settings.RAG_SIMILARITY_THRESHOLD

        # Generate embedding for the query
        query_embedding = self._generate_embedding(input_text)

        # Build query parameters
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }

        if filter_metadata:
            query_params["where"] = filter_metadata

        # Query ChromaDB
        results = self.collection.query(**query_params)

        # Process results
        corrections = []
        if results and results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                # Calculate similarity (ChromaDB returns distances, we convert to similarity)
                distance = results['distances'][0][i] if results['distances'] else 0
                similarity = 1 - distance  # Convert distance to similarity

                if similarity >= min_similarity:
                    correction = {
                        "id": doc_id,
                        "original_input": results['documents'][0][i],
                        "similarity": round(similarity, 4),
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {}
                    }
                    corrections.append(correction)

        print(f"🔍 Found {len(corrections)} relevant corrections for RAG")
        return corrections

    async def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the vector store."""
        if not self._initialized:
            return {"status": "not_initialized", "count": 0}

        return {
            "status": "operational",
            "total_corrections": self.collection.count(),
            "collection_name": settings.CHROMA_COLLECTION_NAME
        }

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """
        Get detailed statistics about the Data Flywheel.

        IRON SHELL METRICS:
        These metrics tell you how strong your competitive moat is.
        """
        if not self._initialized:
            await self.initialize()

        total = self.collection.count()

        # Get sample of recent corrections for analysis
        stats = {
            "total_corrections": total,
            "flywheel_status": "spinning" if total > 0 else "empty",
            "moat_strength": self._calculate_moat_strength(total),
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "embedding_model": settings.EMBEDDING_MODEL,
        }

        return stats

    def _calculate_moat_strength(self, correction_count: int) -> str:
        """
        Calculate how defensible your AI is based on correction count.

        IRON SHELL WISDOM:
        - 0-10 corrections: No moat (anyone can catch up)
        - 10-100 corrections: Emerging moat (starting to learn)
        - 100-1000 corrections: Strong moat (real competitive advantage)
        - 1000+ corrections: Deep moat (very hard to replicate)
        """
        if correction_count == 0:
            return "none - start collecting corrections!"
        elif correction_count < 10:
            return "weak - keep collecting user feedback"
        elif correction_count < 100:
            return "emerging - your AI is learning your domain"
        elif correction_count < 1000:
            return "strong - competitors would need months to catch up"
        else:
            return "deep - your data is a serious competitive advantage"

    async def delete_correction(self, correction_id: str) -> bool:
        """Delete a specific correction (use sparingly!)."""
        if not self._initialized:
            await self.initialize()

        try:
            self.collection.delete(ids=[correction_id])
            self.client.persist()
            return True
        except Exception as e:
            print(f"Failed to delete correction: {e}")
            return False

    async def export_corrections(self) -> List[Dict[str, Any]]:
        """
        Export all corrections for backup.

        IRON SHELL TIP:
        Back up your corrections regularly. This data is your moat.
        """
        if not self._initialized:
            await self.initialize()

        # Get all items (ChromaDB doesn't have a direct "get all" so we query with high n)
        results = self.collection.get(
            include=["documents", "metadatas", "embeddings"]
        )

        exports = []
        if results and results['ids']:
            for i, doc_id in enumerate(results['ids']):
                exports.append({
                    "id": doc_id,
                    "document": results['documents'][i] if results['documents'] else None,
                    "metadata": results['metadatas'][i] if results['metadatas'] else None,
                })

        return exports
