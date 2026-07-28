#!/usr/bin/env python3
"""Collect and deduplicate literature metadata from scholarly APIs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


USER_AGENT = "literature-evidence-synthesis/1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", required=True, help="Search query; repeat for multiple queries.")
    parser.add_argument("--from-year", type=int, required=True)
    parser.add_argument("--to-year", type=int, required=True)
    parser.add_argument("--limit-per-source", type=int, default=50)
    parser.add_argument(
        "--sources",
        default="openalex,crossref",
        help="Comma-separated: openalex,crossref,arxiv,pubmed",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--append", action="store_true", help="Merge with an existing JSONL file.")
    parser.add_argument("--mailto", default="", help="Contact email sent to scholarly APIs.")
    return parser.parse_args()


def fetch_json(url: str, mailto: str = "", retries: int = 3) -> dict[str, Any]:
    agent = USER_AGENT + (f" (mailto:{mailto})" if mailto else "")
    request = urllib.request.Request(url, headers={"User-Agent": agent, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt + 1 == retries:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def fetch_xml(url: str, mailto: str = "", retries: int = 3) -> ET.Element:
    agent = USER_AGENT + (f" (mailto:{mailto})" if mailto else "")
    request = urllib.request.Request(url, headers={"User-Agent": agent, "Accept": "application/xml"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return ET.fromstring(response.read())
        except (urllib.error.URLError, TimeoutError, ET.ParseError):
            if attempt + 1 == retries:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def clean_text(value: Any) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", html.unescape(str(value)))
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(value: Any) -> str:
    if not value:
        return ""
    doi = str(value).strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(" .")


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    return "".join(char for char in value if char.isalnum())


def paper_key(record: dict[str, Any]) -> str:
    doi = normalize_doi(record.get("doi"))
    if doi:
        return f"doi:{doi}"
    return f"title:{normalize_title(record.get('title', ''))}:{record.get('year') or ''}"


def stable_id(record: dict[str, Any]) -> str:
    digest = hashlib.sha1(paper_key(record).encode("utf-8")).hexdigest()[:8].upper()
    return f"P{digest}"


def inverted_abstract(index: Any) -> str:
    if not isinstance(index, dict):
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in index.items():
        if not isinstance(positions, list):
            continue
        positioned.extend((int(position), str(word)) for position in positions)
    return " ".join(word for _, word in sorted(positioned))


def openalex_records(query: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    filters = []
    if args.from_year:
        filters.append(f"from_publication_date:{args.from_year}-01-01")
    if args.to_year:
        filters.append(f"to_publication_date:{args.to_year}-12-31")
    params = {"search": query, "per-page": min(args.limit_per_source, 200)}
    if filters:
        params["filter"] = ",".join(filters)
    if args.mailto:
        params["mailto"] = args.mailto
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    payload = fetch_json(url, args.mailto)
    records = []
    for item in payload.get("results", []):
        location = item.get("primary_location") or {}
        source = location.get("source") or {}
        doi = normalize_doi(item.get("doi"))
        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in item.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        records.append(
            {
                "title": clean_text(item.get("display_name")),
                "authors": authors,
                "year": item.get("publication_year"),
                "venue": clean_text(source.get("display_name")),
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else item.get("id", ""),
                "abstract": clean_text(inverted_abstract(item.get("abstract_inverted_index"))),
                "publication_type": item.get("type", ""),
                "sources": ["openalex"],
                "matched_queries": [query],
                "citation_count": item.get("cited_by_count"),
                "open_access": bool((item.get("open_access") or {}).get("is_oa")),
            }
        )
    return records


def crossref_year(item: dict[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "issued", "created"):
        parts = (item.get(key) or {}).get("date-parts") or []
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                pass
    return None


def crossref_records(query: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "query.bibliographic": query,
        "rows": min(args.limit_per_source, 1000),
        "select": "DOI,title,author,published-print,published-online,issued,created,container-title,URL,abstract,type,is-referenced-by-count",
    }
    filters = []
    if args.from_year:
        filters.append(f"from-pub-date:{args.from_year}-01-01")
    if args.to_year:
        filters.append(f"until-pub-date:{args.to_year}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    if args.mailto:
        params["mailto"] = args.mailto
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    payload = fetch_json(url, args.mailto)
    records = []
    for item in payload.get("message", {}).get("items", []):
        authors = []
        for author in item.get("author", []):
            name = " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part)
            if name:
                authors.append(name)
        doi = normalize_doi(item.get("DOI"))
        titles = item.get("title") or []
        containers = item.get("container-title") or []
        records.append(
            {
                "title": clean_text(titles[0] if titles else ""),
                "authors": authors,
                "year": crossref_year(item),
                "venue": clean_text(containers[0] if containers else ""),
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else item.get("URL", ""),
                "abstract": clean_text(item.get("abstract")),
                "publication_type": item.get("type", ""),
                "sources": ["crossref"],
                "matched_queries": [query],
                "citation_count": item.get("is-referenced-by-count"),
                "open_access": None,
            }
        )
    return records


def arxiv_records(query: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    date_filter = (
        f"submittedDate:[{args.from_year}01010000 TO {args.to_year}12312359]"
    )
    params = {
        "search_query": f'all:"{query}" AND {date_filter}',
        "start": 0,
        "max_results": min(args.limit_per_source, 100),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    root = fetch_xml(url, args.mailto)
    atom = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    records = []
    for entry in root.findall("atom:entry", atom):
        published = clean_text(entry.findtext("atom:published", default="", namespaces=atom))
        try:
            year = int(published[:4])
        except (TypeError, ValueError):
            year = None
        doi = normalize_doi(entry.findtext("arxiv:doi", default="", namespaces=atom))
        entry_url = clean_text(entry.findtext("atom:id", default="", namespaces=atom))
        authors = [
            clean_text(author.findtext("atom:name", default="", namespaces=atom))
            for author in entry.findall("atom:author", atom)
        ]
        categories = [
            category.attrib.get("term", "")
            for category in entry.findall("atom:category", atom)
            if category.attrib.get("term")
        ]
        records.append(
            {
                "title": clean_text(entry.findtext("atom:title", default="", namespaces=atom)),
                "authors": [author for author in authors if author],
                "year": year,
                "venue": clean_text(entry.findtext("arxiv:journal_ref", default="arXiv", namespaces=atom))
                or "arXiv",
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else entry_url,
                "abstract": clean_text(entry.findtext("atom:summary", default="", namespaces=atom)),
                "publication_type": "preprint",
                "subjects": categories,
                "sources": ["arxiv"],
                "matched_queries": [query],
                "citation_count": None,
                "open_access": True,
            }
        )
    return records


def element_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return clean_text("".join(element.itertext()))


def pubmed_year(article: ET.Element) -> int | None:
    for path in (
        ".//Article/Journal/JournalIssue/PubDate/Year",
        ".//PubmedData/History/PubMedPubDate/Year",
    ):
        value = element_text(article.find(path))
        if value.isdigit():
            return int(value)
    medline_date = element_text(article.find(".//Article/Journal/JournalIssue/PubDate/MedlineDate"))
    match = re.search(r"\b(19|20)\d{2}\b", medline_date)
    return int(match.group(0)) if match else None


def pubmed_records(query: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    date_query = (
        f'("{query}") AND ("{args.from_year}/01/01"[Date - Publication] : '
        f'"{args.to_year}/12/31"[Date - Publication])'
    )
    search_params = {
        "db": "pubmed",
        "term": date_query,
        "retmode": "json",
        "retmax": min(args.limit_per_source, 200),
        "sort": "relevance",
    }
    if args.mailto:
        search_params["email"] = args.mailto
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        search_params
    )
    ids = fetch_json(search_url, args.mailto).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    fetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
    if args.mailto:
        fetch_params["email"] = args.mailto
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(
        fetch_params
    )
    root = fetch_xml(fetch_url, args.mailto)
    records = []
    for article in root.findall(".//PubmedArticle"):
        medline = article.find("MedlineCitation")
        article_node = medline.find("Article") if medline is not None else None
        if medline is None or article_node is None:
            continue
        pmid = element_text(medline.find("PMID"))
        authors = []
        for author in article_node.findall(".//AuthorList/Author"):
            collective = element_text(author.find("CollectiveName"))
            name = " ".join(
                part
                for part in (
                    element_text(author.find("ForeName")),
                    element_text(author.find("LastName")),
                )
                if part
            )
            if collective or name:
                authors.append(collective or name)
        doi = ""
        for article_id in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if article_id.attrib.get("IdType") == "doi":
                doi = normalize_doi(element_text(article_id))
                break
        abstract_parts = []
        for abstract_text in article_node.findall(".//Abstract/AbstractText"):
            text = element_text(abstract_text)
            label = clean_text(abstract_text.attrib.get("Label"))
            if text:
                abstract_parts.append(f"{label}: {text}" if label else text)
        publication_types = [
            element_text(item)
            for item in article_node.findall(".//PublicationTypeList/PublicationType")
            if element_text(item)
        ]
        records.append(
            {
                "title": element_text(article_node.find("ArticleTitle")),
                "authors": authors,
                "year": pubmed_year(article),
                "venue": element_text(article_node.find(".//Journal/Title")),
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "abstract": clean_text(" ".join(abstract_parts)),
                "publication_type": publication_types[0] if publication_types else "journal-article",
                "sources": ["pubmed"],
                "matched_queries": [query],
                "citation_count": None,
                "open_access": None,
                "pubmed_id": pmid,
            }
        )
    return records


def prefer(left: Any, right: Any) -> Any:
    if left not in (None, "", [], {}):
        return left
    return right


def merge_record(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key in {"sources", "matched_queries"}:
            merged[key] = sorted(set(existing.get(key, [])) | set(value or []))
        elif key == "abstract" and len(str(value or "")) > len(str(existing.get(key) or "")):
            merged[key] = value
        else:
            merged[key] = prefer(existing.get(key), value)
    merged["doi"] = normalize_doi(merged.get("doi"))
    return merged


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    temp.replace(path)


def main() -> int:
    args = parse_args()
    if args.limit_per_source < 1:
        raise SystemExit("--limit-per-source must be positive")
    if args.from_year > args.to_year:
        raise SystemExit("--from-year cannot be greater than --to-year")
    selected = {source.strip().lower() for source in args.sources.split(",") if source.strip()}
    unknown = selected - {"openalex", "crossref", "arxiv", "pubmed"}
    if unknown:
        raise SystemExit(f"Unsupported sources: {', '.join(sorted(unknown))}")

    collected_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    gathered = read_jsonl(args.output) if args.append else []
    search_log_path = args.output.parent / "search-log.jsonl"
    search_log = read_jsonl(search_log_path) if args.append else []
    failures = []
    collectors = {
        "openalex": openalex_records,
        "crossref": crossref_records,
        "arxiv": arxiv_records,
        "pubmed": pubmed_records,
    }
    for query in args.query:
        for source in sorted(selected):
            try:
                records = collectors[source](query, args)
                gathered.extend(records)
                search_log.append(
                    {
                        "source": source,
                        "query": query,
                        "from_year": args.from_year,
                        "to_year": args.to_year,
                        "returned_count": len(records),
                        "searched_at": collected_at,
                    }
                )
            except Exception as exc:  # Continue when a complementary source remains available.
                failures.append(f"{source} / {query}: {exc}")
                search_log.append(
                    {
                        "source": source,
                        "query": query,
                        "from_year": args.from_year,
                        "to_year": args.to_year,
                        "returned_count": 0,
                        "searched_at": collected_at,
                        "error": str(exc),
                    }
                )

    by_key: dict[str, dict[str, Any]] = {}
    for record in gathered:
        if not record.get("title"):
            continue
        key = paper_key(record)
        by_key[key] = merge_record(by_key.get(key, {}), record)

    output_records = []
    for record in by_key.values():
        record["paper_id"] = record.get("paper_id") or stable_id(record)
        record["collected_at"] = record.get("collected_at") or collected_at
        record.setdefault("selected", False)
        record.setdefault("analysis_status", "pending" if record.get("abstract") else "insufficient_text")
        output_records.append(record)
    output_records.sort(key=lambda item: (-(item.get("year") or 0), item.get("title", "").casefold()))
    write_jsonl(args.output, output_records)
    write_jsonl(search_log_path, search_log)

    print(f"Wrote {len(output_records)} deduplicated records to {args.output}")
    if failures:
        print("Source failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
    return 0 if output_records else 2


if __name__ == "__main__":
    raise SystemExit(main())
