from src.evaluation_agent import evaluate_document

def evaluate_supplier(supplier_name, document_text, criteria, api_key, file_name=""):
    scorecard, warnings = evaluate_document(supplier_name, document_text, criteria, api_key)
    result = {
        "name": supplier_name,
        "file_name": file_name,
        "criteria": scorecard["criteria"],
        "risks": scorecard["risks"],
        "overall_summary": scorecard["overall_summary"],
    }
    return result, warnings
