
from src.evaluation_agent import evaluate_document
from src.rag_retriever import retrieve_relevant_chunks


def evaluate_supplier(
    supplier_name,
    document_text,
    criteria,
    api_key,
    file_name="",
    document_pages=None,
):
    """Coordinate evidence retrieval and supplier evaluation."""

    retrieved_evidence = retrieve_relevant_chunks(
        document_text=document_text,
        document_pages=document_pages,
        file_name=file_name,
        criteria=criteria,
        api_key=api_key,
    )

    scorecard, warnings = evaluate_document(
        supplier_name=supplier_name,
        document_text=document_text,
        criteria=criteria,
        api_key=api_key,
        retrieved_evidence=retrieved_evidence,
    )

    result = {
        "name": supplier_name,
        "file_name": file_name,
        "criteria": scorecard["criteria"],
        "risks": scorecard["risks"],
        "overall_summary": scorecard["overall_summary"],
    }

    return result, warnings
