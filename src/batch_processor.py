
from src.document_tool import extract_pdf_text
from src.orchestrator import evaluate_supplier
from src.scoring import calculate_batch_scores


def process_supplier_batch(suppliers, criteria, api_key):
    """
    Evaluate a batch of suppliers.

    A supplier failure is recorded as a warning. Other suppliers
    continue to be evaluated. Only successful evaluations are ranked.
    """
    results = []
    warnings = []

    for supplier in suppliers:
        supplier_name = supplier["name"]

        try:
            document_text = extract_pdf_text(supplier["bytes"])

            result, supplier_warnings = evaluate_supplier(
                supplier_name=supplier_name,
                document_text=document_text,
                criteria=criteria,
                api_key=api_key,
                file_name=supplier.get("file_name", ""),
            )

            result.update({
                "name": supplier_name,
                "submission_date": supplier["submission_date"],
                "experience_rating": supplier["experience_rating"],
                "file_name": supplier.get("file_name", ""),
            })

            results.append(result)

            warnings.extend(
                f"{supplier_name}: {warning}"
                for warning in supplier_warnings
            )

        except Exception as error:
            warnings.append(
                f"{supplier_name}: evaluation failed: {error}"
            )

    if results:
        ranked_results = calculate_batch_scores(results, criteria)
    else:
        ranked_results = []

    return ranked_results, warnings
