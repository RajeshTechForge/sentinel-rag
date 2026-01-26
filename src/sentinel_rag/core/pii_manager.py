"""
Manages PII detection and anonymization using Presidio in a multi-process setup.
"""

import logging
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from os import cpu_count
from typing import List

# Suppress Presidio and spaCy logs BEFORE imports
for name in (
    "presidio_analyzer",
    "presidio_anonymizer",
    "presidio-analyzer",
    "presidio-anonymizer",
    "spacy",
    "spacy.language",
):
    logger = logging.getLogger(name)
    logger.setLevel(logging.CRITICAL)
    logger.propagate = False


from langchain_core.documents import Document  # noqa: E402
from presidio_analyzer import AnalyzerEngine  # noqa: E402
from presidio_analyzer.nlp_engine import NlpEngineProvider  # noqa: E402
from presidio_anonymizer import AnonymizerEngine  # noqa: E402
from presidio_anonymizer.entities import OperatorConfig  # noqa: E402

# Worker-local engines (initialized per process)
_analyzer = None
_anonymizer = None

_NLP_CONFIG = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_md"}],
}


@lru_cache(maxsize=1)
def _get_nlp_engine():
    """Lazily initialize NLP engine once per process."""
    provider = NlpEngineProvider(nlp_configuration=_NLP_CONFIG)
    return provider.create_engine()


def _init_worker():
    """Initialize Presidio engines in worker process."""
    global _analyzer, _anonymizer
    # Suppress logs in worker process
    for name in ("presidio_analyzer", "presidio_anonymizer", "spacy"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    _analyzer = AnalyzerEngine(nlp_engine=_get_nlp_engine())
    _anonymizer = AnonymizerEngine()


def _process_text(text: str) -> str:
    """Process single text chunk for PII."""
    results = _analyzer.analyze(text=text, language="en")
    return _anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators={"DEFAULT": OperatorConfig("replace")},
    ).text


def _process_doc(doc: Document) -> Document:
    """Process document for PII, returning new document."""
    return Document(page_content=_process_text(doc.page_content), metadata=doc.metadata)


class PiiManager:
    """Thread-safe PII detection and anonymization manager."""

    def __init__(self, max_workers: int = None):
        self._max_workers = max_workers or min(cpu_count() or 1, 4)
        self._executor = None

    @property
    def executor(self) -> ProcessPoolExecutor:
        """Lazy executor initialization."""
        if self._executor is None:
            self._executor = ProcessPoolExecutor(
                max_workers=self._max_workers, initializer=_init_worker
            )
        return self._executor

    def reduce_pii(self, chunks: List[str]) -> List[str]:
        """Anonymize PII in text chunks."""
        if not chunks:
            return []
        return list(self.executor.map(_process_text, chunks))

    def reduce_pii_documents(self, documents: List[Document]) -> List[Document]:
        """Anonymize PII in documents."""
        if not documents:
            return []
        return list(self.executor.map(_process_doc, documents))

    def close(self):
        """Shutdown executor gracefully."""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
