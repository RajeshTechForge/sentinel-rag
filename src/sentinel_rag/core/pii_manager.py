from os import cpu_count
from concurrent.futures import ProcessPoolExecutor
from langchain_core.documents import Document
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Global placeholders for each worker process
analyzer = None
anonymizer = None

configuration = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_md"}],
}

provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine = provider.create_engine()

def initialize_worker():
    global analyzer, anonymizer
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
    anonymizer = AnonymizerEngine()

def process_chunk(text: str) -> str:
    # Use the models already loaded in this process
    results = analyzer.analyze(text=text, language='en')
    operators = {"DEFAULT": OperatorConfig("replace")}
    anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)
    return anonymized_result.text

def process_document(doc: Document) -> Document:
    doc.page_content = process_chunk(doc.page_content)
    return doc

class PiiManager:
    def __init__(self):
        # Determine number of workers (usually number of CPU cores)
        self.num_workers = cpu_count() or 1
        self.executor = ProcessPoolExecutor(
            max_workers=self.num_workers, 
            initializer=initialize_worker
        )

    def reduce_pii(self, chunks: list[str]):
        results = list(self.executor.map(process_chunk, chunks))
        return results

    def reduce_pii_documents(self, documents: list[Document]) -> list[Document]:
        results = list(self.executor.map(process_document, documents))
        return results
    
    def __del__(self):
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
