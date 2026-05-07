"""CSV profiling and visualization metadata generation using Python stdlib."""

import csv
import io
import json
import re
from dataclasses import dataclass, asdict
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


# Re-export for convenience
ArtifactTypes = {"csv_profile", "chart_spec", "insight_card"}


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
    has_low_cardinality = unique_ratio <= 0.95
    has_short_text_values = avg_len < 30 and not any(c.isdigit() for c in "".join(non_null[:10] or [""]))
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


def build_chart_spec(profile: CSVProfile) -> list[dict]:
    """Build chart_spec artifacts from a CSVProfile when useful inputs exist.

    Returns a list of chart spec dicts with keys: type, title, x_col, y_col(s), series_col, display_title.
    """
    specs: list[dict] = []

    # Find date + numeric -> trend chart
    date_cols = [c for c in profile.columns if c.inferred_type == "date"]
    numeric_cols = [c for c in profile.columns if c.inferred_type == "numeric"]

    for date_col in date_cols:
        for num_col in numeric_cols:
            if len(specs) >= 3:
                break
            specs.append({
                "chart_type": "line",
                "title": f"{num_col.name} over {date_col.name}",
                "x_col": date_col.name,
                "y_cols": [num_col.name],
                "series_col": None,
                "display_title": f"Trend: {num_col.name} vs {date_col.name}",
                "description": f"Line chart showing {num_col.name} trend over {date_col.name}",
            })

    # Find categorical + numeric -> segment/bar chart
    cat_cols = [c for c in profile.columns if c.inferred_type == "categorical"]
    for cat_col in cat_cols:
        for num_col in numeric_cols:
            if len(specs) >= 6:
                break
            specs.append({
                "chart_type": "bar",
                "title": f"{num_col.name} by {cat_col.name}",
                "x_col": cat_col.name,
                "y_cols": [num_col.name],
                "series_col": None,
                "display_title": f"Breakdown: {num_col.name} by {cat_col.name}",
                "description": f"Bar chart showing {num_col.name} breakdown by {cat_col.name}",
            })

    # Find 2+ numeric cols -> scatter/relationship
    if len(numeric_cols) >= 2:
        for i in range(len(numeric_cols) - 1):
            for j in range(i + 1, len(numeric_cols)):
                if len(specs) >= 4:
                    break
                specs.append({
                    "chart_type": "scatter",
                    "title": f"{numeric_cols[i].name} vs {numeric_cols[j].name}",
                    "x_col": numeric_cols[i].name,
                    "y_cols": [numeric_cols[j].name],
                    "series_col": None,
                    "display_title": f"Relationship: {numeric_cols[i].name} vs {numeric_cols[j].name}",
                    "description": f"Scatter plot showing relationship between {numeric_cols[i].name} and {numeric_cols[j].name}",
                })

    return specs


def build_insight_card(profile: CSVProfile) -> list[dict]:
    """Build insight_card artifacts from identifiable insights in the CSV profile."""
    insights: list[dict] = []

    # Row/column summary
    insights.append({
        "insight_type": "summary",
        "title": "Dataset Overview",
        "description": f"This dataset contains {profile.row_count} rows and {profile.column_count} columns.",
        "columns": [c.name for c in profile.columns],
        "confidence": "high",
    })

    # Numeric insights: min/max/avg for each numeric column
    for col in profile.columns:
        if col.inferred_type == "numeric" and col.numeric_stats:
            stats = col.numeric_stats
            insights.append({
                "insight_type": "stat_summary",
                "title": f"Metric: {col.name}",
                "description": (
                    f"{col.name} ranges from {stats['min']:.2f} to {stats['max']:.2f}, "
                    f"with an average of {stats['avg']:.2f} across {stats['count']} records."
                ),
                "column": col.name,
                "min": stats["min"],
                "max": stats["max"],
                "avg": stats["avg"],
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
                        insights.append({
                            "insight_type": "anomaly",
                            "title": f"Potential outlier in {col.name}",
                            "description": f"Value {val:.2f} is more than 2 standard deviations from the mean ({avg:.2f}) in {col.name}.",
                            "column": col.name,
                            "value": val,
                            "expected_range": f"{avg - 2*std:.2f} – {avg + 2*std:.2f}",
                            "confidence": "medium",
                        })
                        break

    # Date range insight
    date_cols = [c for c in profile.columns if c.inferred_type == "date"]
    for col in date_cols:
        if col.date_stats and "min" in col.date_stats and "max" in col.date_stats:
            insights.append({
                "insight_type": "date_range",
                "title": f"Period: {col.name}",
                "description": f"Data spans from {col.date_stats['min']} to {col.date_stats['max']}.",
                "column": col.name,
                "period_start": col.date_stats["min"],
                "period_end": col.date_stats["max"],
                "confidence": "high",
            })

    return insights