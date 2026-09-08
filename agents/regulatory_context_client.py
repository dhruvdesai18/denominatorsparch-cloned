"""
Free public data sources for Agent 3 (Regulatory Context): openFDA's
device/recall and device/classification endpoints, plus PubMed's NCBI
E-utilities. No API key or LLM call required for any of it.

Uses openfda_client.py's shared HTTP/retry/budget plumbing for the openFDA
calls. PubMed's E-utilities are a separate, non-openFDA API (eutils.ncbi.
nlm.nih.gov) with their own, much looser rate limit (NCBI asks for <=3
requests/sec without a key) -- reuses the same RequestBudget class only
for its request-counting convenience, not its openFDA-specific defaults.
"""

import time

import requests

from .openfda_client import RequestBudget, api_get as _openfda_api_get

RECALL_URL = "https://api.fda.gov/device/recall.json"
CLASSIFICATION_URL = "https://api.fda.gov/device/classification.json"
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_REQUEST_DELAY_SECONDS = 0.35  # stay under NCBI's 3 req/sec without a key


def fetch_classification(product_code: str, api_key: str | None, budget: RequestBudget) -> dict | None:
    """One product code has at most one classification record."""
    payload = _openfda_api_get(
        CLASSIFICATION_URL, {"search": f"product_code:{product_code}", "limit": 1}, api_key, budget
    )
    results = payload.get("results", [])
    if not results:
        return None
    raw = results[0]
    return {
        "product_code": raw.get("product_code", ""),
        "device_name": raw.get("device_name", ""),
        "device_class": raw.get("device_class", ""),
        "regulation_number": raw.get("regulation_number", ""),
        "medical_specialty": raw.get("medical_specialty", ""),
        "life_sustain_support_flag": raw.get("life_sustain_support_flag", ""),
        "gmp_exempt_flag": raw.get("gmp_exempt_flag", ""),
    }


def flatten_recall(raw: dict) -> dict:
    return {
        "product_res_number": raw.get("product_res_number", ""),
        "recalling_firm": raw.get("recalling_firm", ""),
        "recall_status": raw.get("recall_status", ""),
        "event_date_initiated": raw.get("event_date_initiated", ""),
        "event_date_posted": raw.get("event_date_posted", ""),
        "reason_for_recall": raw.get("reason_for_recall", ""),
        "product_description": raw.get("product_description", ""),
    }


def fetch_recent_recalls(
    product_code: str, api_key: str | None, budget: RequestBudget, limit: int = 10
) -> tuple[int, list[dict]]:
    """Returns (total_recall_count, most_recent_N_recalls) -- the total
    count is the real regulatory signal (has this product family been
    recalled often?); the detail list is just enough for a reviewer to
    skim without fetching all of them."""
    payload = _openfda_api_get(
        RECALL_URL,
        {"search": f"product_code:{product_code}", "sort": "event_date_posted:desc", "limit": limit},
        api_key,
        budget,
    )
    total = payload.get("meta", {}).get("results", {}).get("total", 0)
    recalls = [flatten_recall(r) for r in payload.get("results", [])]
    return total, recalls


def _pubmed_get(url: str, params: dict, budget: RequestBudget) -> dict:
    response = requests.get(url, params=params, timeout=30)
    budget.record()
    response.raise_for_status()
    time.sleep(PUBMED_REQUEST_DELAY_SECONDS)
    return response.json()


def search_literature(query: str, budget: RequestBudget, retmax: int = 5) -> dict:
    """Search PubMed for a query, returning total hit count and the top
    `retmax` articles' title/journal/pubdate. Returns total_results=0 and
    an empty article list (not an error) if the query matches nothing."""
    search_payload = _pubmed_get(
        PUBMED_ESEARCH_URL, {"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"}, budget
    )
    esearch_result = search_payload.get("esearchresult", {})
    total = int(esearch_result.get("count", 0))
    pmids = esearch_result.get("idlist", [])

    if not pmids:
        return {"query": query, "total_results": total, "articles": []}

    summary_payload = _pubmed_get(
        PUBMED_ESUMMARY_URL, {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}, budget
    )
    summary_result = summary_payload.get("result", {})
    articles = []
    for pmid in summary_result.get("uids", []):
        article = summary_result.get(pmid, {})
        articles.append(
            {
                "pmid": pmid,
                "title": article.get("title", ""),
                "journal": article.get("fulljournalname", ""),
                "pubdate": article.get("pubdate", ""),
            }
        )

    return {"query": query, "total_results": total, "articles": articles}
