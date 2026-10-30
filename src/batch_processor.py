
from src.document_tool import extract_pdf_pages, extract_pdf_text
from src.orchestrator import evaluate_supplier
from src.scoring import calculate_batch_scores


def process_supplier_batch(suppliers, criteria, api_key):
    """
    Evaluate a batch of suppliers.

    Failed suppliers generate warnings. Other suppliers continue.
    Only successful evaluations are ranked.
    """
    results = []
    warnings = []

    for supplier in suppliers:
        supplier_name = supplier["name"]

        try:
            document_text = extract_pdf_text(supplier["bytes"])

            # Page references are optional. Keep the existing text-based
            # workflow available when page extraction is unsuccessful.
            try:
                document_pages = extract_pdf_pages(supplier["bytes"])
            except Exception:
                document_pages = None

            # Preserve compatibility with existing callers and test mocks.
            evaluation_args = {
                "supplier_name": supplier_name,
                "document_text": document_text,
                "criteria": criteria,
                "api_key": api_key,
                "file_name": supplier.get("file_name", ""),
            }

            if document_pages is not None:
                evaluation_args["document_pages"] = document_pages

            result, supplier_warnings = evaluate_supplier(**evaluation_args)

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

    ranked_results = (
        calculate_batch_scores(results, criteria)
        if results
        else []
    )

    return ranked_results, warnings
