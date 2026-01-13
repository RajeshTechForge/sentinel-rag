"""
Sample Configuration for Parent-Document Retrieval parameters.

Allows fine-tuning of chunking strategies based on document type and use case.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ChunkConfig:
    """Configuration for hierarchical chunking."""

    # Parent chunk configuration (larger chunks for context)
    parent_chunk_size: int = 2000
    parent_overlap: int = 200

    # Child chunk configuration (smaller chunks for search)
    child_chunk_size: int = 400
    child_overlap: int = 50

    # Search configuration
    use_parent_retrieval: bool = True

    # RRF parameters for hybrid search
    rrf_k: int = 60
    similarity_threshold: float = 0.4

    def __post_init__(self):
        """Validate configuration."""
        if self.parent_chunk_size <= self.child_chunk_size:
            raise ValueError("Parent chunks must be larger than child chunks")

        if self.parent_overlap >= self.parent_chunk_size:
            raise ValueError("Parent overlap must be less than chunk size")

        if self.child_overlap >= self.child_chunk_size:
            raise ValueError("Child overlap must be less than chunk size")

        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")


# Predefined configurations for common document types
class PresetConfigs:
    """Preset configurations optimized for different document types."""

    # Technical documentation (e.g., API docs, technical manuals)
    TECHNICAL_DOCS = ChunkConfig(
        parent_chunk_size=2500,
        parent_overlap=250,
        child_chunk_size=500,
        child_overlap=50,
        similarity_threshold=0.35,  # More lenient for technical terms
    )

    # Legal contracts and compliance documents
    LEGAL_CONTRACTS = ChunkConfig(
        parent_chunk_size=3000,
        parent_overlap=300,
        child_chunk_size=400,
        child_overlap=40,
        similarity_threshold=0.40,
    )

    # News articles and blog posts
    NEWS_ARTICLES = ChunkConfig(
        parent_chunk_size=1500,
        parent_overlap=150,
        child_chunk_size=300,
        child_overlap=30,
        similarity_threshold=0.45,
    )

    # FAQs and Q&A documents
    FAQ_DOCUMENTS = ChunkConfig(
        parent_chunk_size=1000,
        parent_overlap=100,
        child_chunk_size=200,
        child_overlap=20,
        similarity_threshold=0.50,  # Higher threshold for precise matches
    )

    # Research papers and academic documents
    RESEARCH_PAPERS = ChunkConfig(
        parent_chunk_size=2800,
        parent_overlap=280,
        child_chunk_size=600,
        child_overlap=60,
        similarity_threshold=0.35,
    )

    # Employee handbooks and policies
    HANDBOOKS = ChunkConfig(
        parent_chunk_size=2200,
        parent_overlap=220,
        child_chunk_size=450,
        child_overlap=45,
        similarity_threshold=0.40,
    )

    # Chat logs and conversational data
    CONVERSATIONS = ChunkConfig(
        parent_chunk_size=1200,
        parent_overlap=120,
        child_chunk_size=250,
        child_overlap=25,
        similarity_threshold=0.50,
        use_parent_retrieval=False,  # May not benefit from hierarchy
    )

    # Default balanced configuration
    DEFAULT = ChunkConfig(
        parent_chunk_size=2000,
        parent_overlap=200,
        child_chunk_size=400,
        child_overlap=50,
        similarity_threshold=0.40,
    )


def get_config_for_document_type(doc_type: str) -> ChunkConfig:
    """
    Get recommended configuration for a document type.

    Args:
        doc_type: Type of document (e.g., 'technical', 'legal', 'news')

    Returns:
        ChunkConfig: Optimized configuration
    """
    config_map = {
        "technical": PresetConfigs.TECHNICAL_DOCS,
        "legal": PresetConfigs.LEGAL_CONTRACTS,
        "news": PresetConfigs.NEWS_ARTICLES,
        "faq": PresetConfigs.FAQ_DOCUMENTS,
        "research": PresetConfigs.RESEARCH_PAPERS,
        "handbook": PresetConfigs.HANDBOOKS,
        "conversation": PresetConfigs.CONVERSATIONS,
    }

    return config_map.get(doc_type.lower(), PresetConfigs.DEFAULT)


def auto_tune_config(
    avg_doc_length: int, num_sections: Optional[int] = None, is_structured: bool = True
) -> ChunkConfig:
    """
    Automatically tune configuration based on document characteristics.

    Args:
        avg_doc_length: Average document length in characters
        num_sections: Number of distinct sections/topics
        is_structured: Whether document has clear structure (headers, sections)

    Returns:
        ChunkConfig: Auto-tuned configuration
    """
    # Base sizes on document length
    if avg_doc_length < 5000:
        # Short documents
        parent_size = min(1500, avg_doc_length // 2)
        child_size = 300
    elif avg_doc_length < 20000:
        # Medium documents
        parent_size = 2000
        child_size = 400
    else:
        # Long documents
        parent_size = 2500
        child_size = 500

    # Adjust based on structure
    if num_sections and num_sections > 0:
        # If we know sections, size parents to ~1.5 sections worth
        estimated_section_length = avg_doc_length // num_sections
        parent_size = min(int(estimated_section_length * 1.5), 3000)

    # Calculate overlaps (10% of chunk size)
    parent_overlap = int(parent_size * 0.1)
    child_overlap = int(child_size * 0.125)

    # Adjust threshold based on structure
    threshold = 0.35 if is_structured else 0.45

    return ChunkConfig(
        parent_chunk_size=parent_size,
        parent_overlap=parent_overlap,
        child_chunk_size=child_size,
        child_overlap=child_overlap,
        similarity_threshold=threshold,
        use_parent_retrieval=True,
    )


def print_config_comparison():
    """Print comparison table of preset configurations."""

    configs = {
        "Technical Docs": PresetConfigs.TECHNICAL_DOCS,
        "Legal Contracts": PresetConfigs.LEGAL_CONTRACTS,
        "News Articles": PresetConfigs.NEWS_ARTICLES,
        "FAQ Documents": PresetConfigs.FAQ_DOCUMENTS,
        "Research Papers": PresetConfigs.RESEARCH_PAPERS,
        "Handbooks": PresetConfigs.HANDBOOKS,
        "Conversations": PresetConfigs.CONVERSATIONS,
        "Default": PresetConfigs.DEFAULT,
    }

    print("=" * 100)
    print("CHUNK CONFIGURATION PRESETS")
    print("=" * 100)
    print(
        f"\n{'Document Type':<20} {'Parent':<12} {'P.Overlap':<12} {'Child':<12} {'C.Overlap':<12} {'Threshold':<10}"
    )
    print("-" * 100)

    for name, config in configs.items():
        print(
            f"{name:<20} "
            f"{config.parent_chunk_size:<12} "
            f"{config.parent_overlap:<12} "
            f"{config.child_chunk_size:<12} "
            f"{config.child_overlap:<12} "
            f"{config.similarity_threshold:<10.2f}"
        )

    print("\n" + "=" * 100)
    print("\nRecommendations:")
    print("  • Larger parent chunks = More context for LLM")
    print("  • Smaller child chunks = Better search precision")
    print("  • Higher overlap = Better boundary handling, more storage")
    print("  • Lower threshold = More results, potential noise")
    print("  • Higher threshold = Fewer, more relevant results")


if __name__ == "__main__":
    # Example usage
    print_config_comparison()

    print("\n\nExample: Auto-tune for 15,000 char document with 8 sections")
    config = auto_tune_config(avg_doc_length=15000, num_sections=8, is_structured=True)
    print(f"Parent size: {config.parent_chunk_size}")
    print(f"Child size:  {config.child_chunk_size}")
    print(f"Threshold:   {config.similarity_threshold}")

    print("\n\nExample: Get config for legal documents")
    legal_config = get_config_for_document_type("legal")
    print(f"Parent size: {legal_config.parent_chunk_size}")
    print(f"Child size:  {legal_config.child_chunk_size}")
    print(f"Use parent retrieval: {legal_config.use_parent_retrieval}")
