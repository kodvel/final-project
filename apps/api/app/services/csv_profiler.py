"""CSV profiling and visualization metadata generation using Python stdlib."""

import csv
import io
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ColumnProfile:
    name: str
    inferred_type: str  # "numeric", "categorical", "date", "text"
    null_count: int = 0
    unique_count: int = 0
    sample_values: list[str] | None = None
    numeric_stats: dict[str, float] | None = None
    date_stats: dict[str, Any] | None = None

    def __post_init__(self):
        if self.sample_values is None:
            self.sample_values = []


@dataclass
class CSVProfile:
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    file_path: str | None = None
    delimiter: str = ","
    has_header: bool = True

    def to_dict(self) -> dict:
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [
                {
                    **asdict(col),
                    "numeric_stats": col.numeric_stats,
                    "date_stats": col.date_stats,
                }
                for col in self.columns
            ],
            "file_path": self.file_path,
            "delimiter": self.delimiter,
            "has_header": self.has_header,
        }


# Re-export for convenience — active artifact types only
ArtifactTypes = {"source_summary", "source_content", "source_insight"}


def infer_column_type(values: list[str]) -> str:
    """Infer column type from a sample of string values."""
    non_null = [v for v in values if v.strip() != ""]
    if not non_null:
        return "text"

    numeric_count = 0
    date_count = 0

    # Try to detect numeric
    for v in non_null[:100]:
        try:
            float(v.replace(",", "").replace("%", "").replace("$", "").strip())
            numeric_count += 1
        except ValueError:
            pass

    if numeric_count / len(non_null[:100]) > 0.8:
        return "numeric"

    # Try to detect date patterns
    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}$",  # 2026-04-01
        r"^\d{2}/\d{2}/\d{4}$",  # 04/01/2026
        r"^\d{2}-\d{2}-\d{4}$",  # 04-01-2026
        r"^\w+ \d{1,2}, \d{4}$",  # April 1, 2026
        r"^\d{4}$",  # year only 2026
        r"^\d{4}-Q[1-4]$",  # 2026-Q1
        r"^\w+ \d{4}$",  # April 2026
        r"^\d{4}-\d{2}$",  # 2026-01 (year-month)
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO datetime
    ]
    for v in non_null[:100]:
        for pat in date_patterns:
            if re.match(pat, v.strip()):
                date_count += 1
                break

    if date_count / len(non_null[:100]) > 0.8:
        return "date"

    # Categorical detection: low unique ratio OR short non-numeric strings with few unique values
    unique_ratio = len(set(non_null)) / len(non_null) if non_null else 1.0
    avg_len = sum(len(v) for v in non_null) / len(non_null) if non_null else 0
    if unique_ratio < 0.8 or (avg_len < 30 and not any(c.isdigit() for c in "".join(non_null[:10] or [""]))):
        return "categorical"

    return "text"


def compute_numeric_stats(values: list[str]) -> dict[str, float]:
    """Compute min/max/avg from string numeric values."""
    numeric_vals: list[float] = []
    for v in values:
        try:
            numeric_vals.append(float(v.replace(",", "").replace("%", "").replace("$", "").strip()))
        except ValueError:
            pass

    if not numeric_vals:
        return {}
    return {
        "min": min(numeric_vals),
        "max": max(numeric_vals),
        "avg": sum(numeric_vals) / len(numeric_vals),
        "count": len(numeric_vals),
    }


def compute_date_stats(values: list[str]) -> dict[str, Any]:
    """Compute min/max dates from string date values."""
    dates: list[datetime] = []
    for v in values:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y"):
            try:
                dates.append(datetime.strptime(v.strip(), fmt))
                break
            except ValueError:
                continue

    if not dates:
        return {}
    return {
        "min": min(dates).isoformat(),
        "max": max(dates).isoformat(),
        "count": len(dates),
    }


def profile_csv_from_path(file_path: str | Path) -> CSVProfile:
    """Profile a CSV file from its local path, returning a CSVProfile."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    raw = path.read_text(encoding="utf-8")
    return profile_csv_from_text(raw, str(path))


def profile_csv_from_text(content: str, file_path: str | None = None) -> CSVProfile:
    """Profile CSV content string, returning a CSVProfile."""
    # Sniff delimiter
    sample = content[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        raise ValueError("CSV file is empty")

    has_header = csv.Sniffer().has_header(sample)
    if has_header and len(rows) > 1:
        header = [h.strip() for h in rows[0]]
        data_rows = rows[1:]
    else:
        header = [f"col_{i}" for i in range(len(rows[0]))]
        data_rows = rows

    # Profile each column
    columns: list[ColumnProfile] = []
    num_cols = len(header)

    for col_idx in range(num_cols):
        col_values = [row[col_idx] if col_idx < len(row) else "" for row in data_rows]
        non_null = [v for v in col_values if v.strip() != ""]
        inferred_type = infer_column_type(non_null if non_null else col_values)

        profile = ColumnProfile(
            name=header[col_idx],
            inferred_type=inferred_type,
            null_count=len(col_values) - len(non_null),
            unique_count=len(set(non_null)) if non_null else 0,
            sample_values=non_null[:5] if non_null else [],
        )

        if inferred_type == "numeric":
            profile.numeric_stats = compute_numeric_stats(non_null)
        elif inferred_type == "date":
            profile.date_stats = compute_date_stats(non_null)

        columns.append(profile)

    return CSVProfile(
        row_count=len(data_rows),
        column_count=num_cols,
        columns=columns,
        file_path=file_path,
        delimiter=delimiter,
        has_header=has_header,
    )


# ---------------------------------------------------------------------------
# Common artifact envelope helpers
# ---------------------------------------------------------------------------


def _empty_envelope() -> dict:
    """Return the common top-level artifact envelope with empty defaults."""
    return {
        "summary": "",
        "statistics": {
            "row_count": None,
            "column_count": None,
            "page_count": None,
            "chunk_count": None,
        },
        "columns": [],
        "sections": [],
        "findings": [],
        "risks": [],
        "opportunities": [],
        "assumptions": [],
        "quotes": [],
        "chunks": [],
        "warnings": [],
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Active artifact builders (source_summary, source_content, source_insight)
# ---------------------------------------------------------------------------


def build_source_summary(profile: CSVProfile) -> dict:
    """Build a source_summary artifact from a CSVProfile.

    High-level dataset overview using the common envelope.
    """
    type_breakdown: dict[str, list[str]] = {}
    for col in profile.columns:
        type_breakdown.setdefault(col.inferred_type, []).append(col.name)

    summary_parts = [
        f"Dataset with {profile.row_count} rows and {profile.column_count} columns",
    ]
    if type_breakdown.get("numeric"):
        summary_parts.append(f"Numeric columns: {', '.join(type_breakdown['numeric'])}")
    if type_breakdown.get("date"):
        summary_parts.append(f"Date columns: {', '.join(type_breakdown['date'])}")
    if type_breakdown.get("categorical"):
        summary_parts.append(f"Categorical columns: {', '.join(type_breakdown['categorical'])}")

    envelope = _empty_envelope()
    envelope["summary"] = ". ".join(summary_parts) + "."
    envelope["statistics"]["row_count"] = profile.row_count
    envelope["statistics"]["column_count"] = profile.column_count
    envelope["columns"] = [
        {"name": c.name, "inferred_type": c.inferred_type}
        for c in profile.columns
    ]
    envelope["metadata"] = {
        "type_breakdown": type_breakdown,
        "delimiter": profile.delimiter,
        "has_header": profile.has_header,
    }
    return envelope


def build_source_content(profile: CSVProfile) -> dict:
    """Build a source_content artifact from a CSVProfile.

    Produces compact factual snippet chunks from the profile data suitable for
    citation-grounded retrieval. Each chunk has a stable chunk_id, a text
    summary, column profiling detail, and row references.
    """
    chunks: list[dict] = []
    chunk_index = 0

    # One chunk per column with profiling facts
    for col in profile.columns:
        text_parts: list[str] = [f"Column '{col.name}' ({col.inferred_type}): "]

        if col.inferred_type == "numeric" and col.numeric_stats:
            stats = col.numeric_stats
            text_parts.append(
                f"ranges {stats['min']:.2f}–{stats['max']:.2f}, "
                f"avg {stats['avg']:.2f} ({stats['count']} values, "
                f"{col.null_count} nulls, {col.unique_count} unique)"
            )
        elif col.inferred_type == "date" and col.date_stats:
            text_parts.append(
                f"spans {col.date_stats['min']} to {col.date_stats['max']} "
                f"({col.date_stats['count']} values, "
                f"{col.null_count} nulls, {col.unique_count} unique)"
            )
        else:
            text_parts.append(
                f"{col.unique_count} unique, {col.null_count} nulls"
            )
            if col.sample_values:
                samples = ", ".join(str(v) for v in col.sample_values[:3])
                text_parts.append(f", samples: [{samples}]")

        col_data: dict[str, Any] = {
            "name": col.name,
            "inferred_type": col.inferred_type,
            "null_count": col.null_count,
            "unique_count": col.unique_count,
            "sample_values": col.sample_values or [],
        }
        if col.numeric_stats:
            col_data["numeric_stats"] = col.numeric_stats
        if col.date_stats:
            col_data["date_stats"] = col.date_stats

        chunks.append({
            "chunk_id": f"csv-profile-{chunk_index}",
            "text": "".join(text_parts),
            "content_type": "metric" if col.inferred_type == "numeric" else "metadata",
            "document_section": "data_profile",
            "chunk_index": chunk_index,
            "columns": [col.name],
            "column_profile": col_data,
        })
        chunk_index += 1

    # If there are numeric columns, add a summary chunk with aggregate stats
    numeric_cols = [c for c in profile.columns if c.inferred_type == "numeric" and c.numeric_stats]
    if numeric_cols:
        lines = [f"Dataset: {profile.row_count} rows × {profile.column_count} columns."]
        for c in numeric_cols:
            s = c.numeric_stats or {}
            if not s:
                continue
            lines.append(f"{c.name}: min={s['min']:.2f}, max={s['max']:.2f}, avg={s['avg']:.2f}")
        chunks.append({
            "chunk_id": f"csv-profile-{chunk_index}",
            "text": " ".join(lines),
            "content_type": "metric",
            "document_section": "data_summary",
            "chunk_index": chunk_index,
            "columns": [c.name for c in numeric_cols],
            "row_count": profile.row_count,
        })
        chunk_index += 1

    envelope = _empty_envelope()
    envelope["summary"] = f"Column-level profiling for {profile.row_count} rows, {profile.column_count} columns."
    envelope["statistics"]["row_count"] = profile.row_count
    envelope["statistics"]["column_count"] = profile.column_count
    envelope["statistics"]["chunk_count"] = len(chunks)
    envelope["columns"] = [
        {"name": c.name, "inferred_type": c.inferred_type}
        for c in profile.columns
    ]
    envelope["chunks"] = chunks
    envelope["metadata"] = {
        "delimiter": profile.delimiter,
        "has_header": profile.has_header,
    }
    return envelope


def build_source_insight(profile: CSVProfile) -> dict:
    """Build a source_insight artifact from identifiable insights in the CSV profile."""
    findings: list[dict] = []
    risks: list[dict] = []
    opportunities: list[dict] = []
    assumptions: list[dict] = []
    warnings: list[str] = []

    # Dataset overview finding
    findings.append({
        "text": f"Dataset contains {profile.row_count} rows and {profile.column_count} columns.",
        "confidence": "high",
    })

    # Numeric column insights
    for col in profile.columns:
        if col.inferred_type == "numeric" and col.numeric_stats:
            stats = col.numeric_stats
            findings.append({
                "text": (
                    f"{col.name} ranges from {stats['min']:.2f} to {stats['max']:.2f}, "
                    f"with an average of {stats['avg']:.2f} across {stats['count']} records."
                ),
                "column": col.name,
                "confidence": "high",
            })

            # Simple anomaly detection: flag values > 2 std devs from mean
            numeric_vals: list[float] = []
            col_samples = col.sample_values or []
            for v in col_samples:
                try:
                    numeric_vals.append(float(v.replace(",", "").replace("%", "").replace("$", "").strip()))
                except ValueError:
                    pass
            if numeric_vals and len(numeric_vals) >= 3:
                avg = sum(numeric_vals) / len(numeric_vals)
                variance = sum((x - avg) ** 2 for x in numeric_vals) / len(numeric_vals)
                std = variance ** 0.5
                for val in numeric_vals:
                    if abs(val - avg) > 2 * std:
                        risks.append({
                            "text": f"Potential outlier in {col.name}: value {val:.2f} is more than 2 standard deviations from the mean ({avg:.2f}).",
                            "column": col.name,
                            "confidence": "medium",
                        })
                        break

    # Date range insights
    for col in profile.columns:
        if col.inferred_type == "date" and col.date_stats:
            findings.append({
                "text": f"Data spans from {col.date_stats['min']} to {col.date_stats['max']}.",
                "column": col.name,
                "confidence": "high",
            })

    # Warn on high null counts
    for col in profile.columns:
        if profile.row_count > 0 and col.null_count / profile.row_count > 0.3:
            warnings.append(f"Column '{col.name}' has {col.null_count} null values ({col.null_count / profile.row_count * 100:.0f}%).")

    envelope = _empty_envelope()
    envelope["summary"] = f"Insights from CSV with {profile.row_count} rows, {profile.column_count} columns."
    envelope["statistics"]["row_count"] = profile.row_count
    envelope["statistics"]["column_count"] = profile.column_count
    envelope["findings"] = findings
    envelope["risks"] = risks
    envelope["opportunities"] = opportunities
    envelope["assumptions"] = assumptions
    envelope["warnings"] = warnings
    return envelope
