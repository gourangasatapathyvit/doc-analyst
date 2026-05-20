"""PDF Agent — document retrieval specialist via RAG.

Does NOT receive full document text. Queries LanceDB vector index
to retrieve only relevant chunks.
"""

from agents.factory import AgentFactory
from tools.pdf_tools import get_page, list_documents, search_document

PDF_AGENT_PROMPT = """You are a document retrieval specialist. Use your tools to search \
and retrieve information from uploaded documents.

Instructions:
- Always use search_document first to find relevant sections
- Cite the page number and source filename when referencing content
- Do NOT try to read entire documents — use search_document to find relevant sections
- Use get_page only when you need the exact full text of a specific page
- Use list_documents to see what files are available
"""


def create_pdf_agent():
    return AgentFactory.create(
        name="pdf_agent",
        tools=[search_document, get_page, list_documents],
        prompt=PDF_AGENT_PROMPT,
    )
