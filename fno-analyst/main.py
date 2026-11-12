"""Indian stocks, futures & options (F&O) CSV analyst agent.

The user shares a Google Drive link to a CSV file and asks questions in plain
language. The agent fetches the file through the Google Drive connector, then
answers using a fixed set of analysis tools. There is no code execution: the
agent has no sandbox and can only call the tools below.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

import pandas as pd
from pydantic import BaseModel, Field

from mistralai import agents

CACHE_DIR = Path("/tmp/fno_analyst_datasets")

_DATAFRAMES: dict[str, pd.DataFrame] = {}
_RECENT: list[str] = []


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_").lower()
    return slug or "dataset"


def _get_frame(dataset_name: str | None) -> tuple[str, pd.DataFrame]:
    name = dataset_name or (_RECENT[-1] if _RECENT else None)
    if not name:
        raise agents.ToolError(
            "No dataset is loaded yet. Fetch the CSV from Google Drive, then call register_csv."
        )
    key = _slug(name)
    df = _DATAFRAMES.get(key)
    if df is None:
        path = CACHE_DIR / f"{key}.csv"
        if path.exists():
            df = pd.read_csv(path)
            _DATAFRAMES[key] = df
        else:
            raise agents.ToolError(
                f"Dataset '{name}' is not loaded on this worker. Fetch the CSV from Google Drive "
                "again and call register_csv."
            )
    if not _RECENT or _RECENT[-1] != key:
        _RECENT.append(key)
    return key, df


def _records(df: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    out = df.head(limit).copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    out = out.astype(object).where(out.notna(), None)
    rows = out.to_dict(orient="records")
    for row in rows:
        for col, val in row.items():
            if isinstance(val, float):
                row[col] = round(val, 4)
    return rows


def _numeric_like(series: pd.Series) -> pd.Series | None:
    if pd.api.types.is_numeric_dtype(series):
        return series
    coerced = pd.to_numeric(series.astype(str).str.replace(",", "").str.strip(), errors="coerce")
    if coerced.notna().mean() >= 0.9 and coerced.notna().any():
        return coerced
    return None


def _datetime_like(series: pd.Series) -> pd.Series | None:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    coerced = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)
    if coerced.notna().mean() >= 0.9 and coerced.notna().any():
        return coerced
    return None


def _apply_condition(df: pd.DataFrame, cond: "FilterCondition") -> pd.Series:
    if cond.column not in df.columns:
        raise agents.ToolError(
            f"Unknown column '{cond.column}'. Available columns: {list(df.columns)}"
        )
    series = df[cond.column]
    op = cond.op
    value = cond.value
    if op == "is_null":
        return series.isna()
    if op == "not_null":
        return series.notna()
    if op in ("gt", "gte", "lt", "lte", "between") and not isinstance(value, str):
        numeric = _numeric_like(series)
        if numeric is not None:
            series = numeric
    if op in ("gt", "gte", "lt", "lte", "between", "eq", "ne"):
        dates = _datetime_like(series)
        if dates is not None and isinstance(value, str):
            try:
                value = pd.to_datetime(value, dayfirst=True)
                series = dates
            except (TypeError, ValueError):
                pass
    try:
        match op:
            case "eq":
                return series == value
            case "ne":
                return series != value
            case "gt":
                return series > value
            case "gte":
                return series >= value
            case "lt":
                return series < value
            case "lte":
                return series <= value
            case "contains":
                return series.astype(str).str.contains(str(value), case=False, na=False)
            case "in":
                values = value if isinstance(value, list) else [value]
                return series.isin(values)
            case "between":
                if not isinstance(value, (list, tuple)) or len(value) != 2:
                    raise agents.ToolError("'between' needs a two-element list [low, high].")
                return series.between(value[0], value[1])
    except TypeError as exc:
        raise agents.ToolError(
            f"Cannot compare column '{cond.column}' ({series.dtype}) with value {value!r}: {exc}"
        ) from exc
    raise agents.ToolError(f"Unsupported operator '{op}'.")


class FilterCondition(BaseModel):
    column: str
    op: Literal[
        "eq", "ne", "gt", "gte", "lt", "lte", "contains", "in", "between", "is_null", "not_null"
    ]
    value: Any = Field(
        default=None,
        description=(
            "Comparison value. A number for numeric columns, a string for text, a list for "
            "'in' and 'between' (between takes [low, high]). Ignored for is_null/not_null."
        ),
    )


class Aggregation(BaseModel):
    column: str = Field(description="Column to aggregate; ignored for 'count'.")
    fn: Literal["count", "sum", "mean", "median", "min", "max", "std", "nunique"]


@agents.tool
def register_csv(
    dataset_name: Annotated[
        str, Field(description="Short name to remember this dataset by, e.g. 'nifty-fno-jun2025'.")
    ],
    csv_text: Annotated[
        str, Field(description="The complete raw CSV text fetched from Google Drive, header row included.")
    ],
) -> dict[str, Any]:
    """Load a CSV dataset so the analysis tools can query it.

    Call this after fetching the file content from Google Drive. Returns the
    row count, columns with inferred types, and a small preview.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _slug(dataset_name)
    try:
        df = pd.read_csv(pd.io.common.StringIO(csv_text))
    except Exception as exc:
        raise agents.ToolError(f"Could not parse the CSV text: {exc}") from exc
    if df.empty:
        raise agents.ToolError(
            "The CSV parsed to zero rows. Check that the file content is complete."
        )
    df.columns = [str(col).strip() for col in df.columns]
    (CACHE_DIR / f"{key}.csv").write_text(df.to_csv(index=False))
    _DATAFRAMES[key] = df
    if not _RECENT or _RECENT[-1] != key:
        _RECENT.append(key)
    columns = {col: str(df[col].dtype) for col in df.columns}
    return {
        "dataset": key,
        "rows": int(len(df)),
        "columns": columns,
        "preview": _records(df, 5),
    }


@agents.tool
def describe_columns(
    dataset_name: Annotated[
        str | None, Field(description="Dataset name; omit for the most recent one.")
    ] = None,
) -> dict[str, Any]:
    """Describe every column of a loaded dataset: type, missing values, unique count, and numeric or categorical summary."""
    key, df = _get_frame(dataset_name)
    report: dict[str, Any] = {"dataset": key, "rows": int(len(df)), "columns": {}}
    for col in df.columns:
        series = df[col]
        entry: dict[str, Any] = {
            "dtype": str(series.dtype),
            "non_null": int(series.notna().sum()),
            "nulls": int(series.isna().sum()),
            "unique": int(series.nunique()),
        }
        numeric = _numeric_like(series)
        if numeric is not None:
            entry.update(
                min=round(float(numeric.min()), 4),
                max=round(float(numeric.max()), 4),
                mean=round(float(numeric.mean()), 4),
                median=round(float(numeric.median()), 4),
                sum=round(float(numeric.sum()), 4),
            )
        else:
            entry["top_values"] = {
                str(k): int(v) for k, v in series.value_counts().head(8).items()
            }
        report["columns"][col] = entry
    return report


@agents.tool
def preview_rows(
    num_rows: Annotated[int, Field(ge=1, le=100)] = 10,
    start: Annotated[int, Field(ge=0, description="Zero-based row offset.")] = 0,
    dataset_name: Annotated[
        str | None, Field(description="Dataset name; omit for the most recent one.")
    ] = None,
) -> dict[str, Any]:
    """Preview raw rows of a loaded dataset, from an offset."""
    key, df = _get_frame(dataset_name)
    window = df.iloc[start : start + num_rows]
    return {
        "dataset": key,
        "total_rows": int(len(df)),
        "start": start,
        "returned": int(len(window)),
        "rows": _records(window, num_rows),
    }


@agents.tool
def filter_rows(
    conditions: Annotated[list[FilterCondition], Field(description="All conditions must hold (AND).")],
    columns: Annotated[list[str] | None, Field(description="Return only these columns.")] = None,
    order_by: Annotated[str | None, Field(description="Column to sort by.")] = None,
    ascending: bool = True,
    limit: Annotated[int, Field(ge=1, le=500)] = 50,
    dataset_name: Annotated[
        str | None, Field(description="Dataset name; omit for the most recent one.")
    ] = None,
) -> dict[str, Any]:
    """Filter rows with structured conditions and return the matches.

    Use this for row-level questions such as 'all RELIANCE trades above 2500'
    or 'rows where open interest jumped'. For rankings and summaries prefer
    groupby_aggregate.
    """
    key, df = _get_frame(dataset_name)
    mask = pd.Series(True, index=df.index)
    for cond in conditions:
        mask &= _apply_condition(df, cond)
    matched = df[mask]
    if order_by is not None:
        if order_by not in matched.columns:
            raise agents.ToolError(
                f"Unknown order_by column '{order_by}'. Available: {list(matched.columns)}"
            )
        matched = matched.sort_values(order_by, ascending=ascending, na_position="last")
    if columns is not None:
        missing = [col for col in columns if col not in matched.columns]
        if missing:
            raise agents.ToolError(f"Unknown columns {missing}. Available: {list(matched.columns)}")
        matched = matched[columns]
    return {
        "dataset": key,
        "matched_rows": int(len(matched)),
        "returned": int(min(len(matched), limit)),
        "rows": _records(matched, limit),
    }


@agents.tool
def groupby_aggregate(
    group_by: Annotated[list[str], Field(description="One or more columns to group by.")],
    aggregations: Annotated[
        list[Aggregation], Field(description="Aggregations to compute per group.")
    ],
    filters: Annotated[
        list[FilterCondition] | None,
        Field(description="Optional conditions applied before grouping (AND)."),
    ] = None,
    order_by: Annotated[str | None, Field(description="Output column to sort by, e.g. 'sum_VOLUME'.")] = None,
    ascending: bool = False,
    limit: Annotated[int, Field(ge=1, le=500)] = 100,
    dataset_name: Annotated[
        str | None, Field(description="Dataset name; omit for the most recent one.")
    ] = None,
) -> dict[str, Any]:
    """Group rows and compute aggregates such as count, sum, mean, min, max.

    Use this for 'total volume per symbol', 'average premium per expiry',
    'top 10 symbols by contracts traded', and similar summary questions.
    """
    key, frame = _get_frame(dataset_name)
    if filters:
        mask = pd.Series(True, index=frame.index)
        for cond in filters:
            mask &= _apply_condition(frame, cond)
        frame = frame[mask]
    missing_groups = [col for col in group_by if col not in frame.columns]
    if missing_groups:
        raise agents.ToolError(
            f"Unknown group_by columns {missing_groups}. Available: {list(frame.columns)}"
        )
    grouped = frame.groupby(group_by, dropna=False, observed=True)
    parts: list[pd.Series] = []
    for agg in aggregations:
        if agg.fn == "count":
            parts.append(grouped.size().rename("count"))
            continue
        if agg.column not in frame.columns:
            raise agents.ToolError(
                f"Unknown aggregation column '{agg.column}'. Available: {list(frame.columns)}"
            )
        column = frame[agg.column]
        if agg.fn in ("sum", "mean", "median", "std"):
            numeric = _numeric_like(column)
            if numeric is None:
                raise agents.ToolError(
                    f"Column '{agg.column}' is not numeric; '{agg.fn}' needs numbers."
                )
            column = numeric
        parts.append(getattr(grouped[agg.column], agg.fn)().rename(f"{agg.fn}_{agg.column}"))
    if not parts:
        raise agents.ToolError("Provide at least one aggregation.")
    result = pd.concat(parts, axis=1).reset_index()
    for col in result.columns:
        if pd.api.types.is_float_dtype(result[col]):
            result[col] = result[col].round(4)
    if order_by is not None:
        if order_by not in result.columns:
            raise agents.ToolError(
                f"Unknown order_by column '{order_by}'. Output columns: {list(result.columns)}"
            )
        result = result.sort_values(order_by, ascending=ascending, na_position="last")
    return {
        "dataset": key,
        "groups": int(len(result)),
        "grouped_by": group_by,
        "returned": int(min(len(result), limit)),
        "rows": _records(result, limit),
    }


INSTRUCTIONS = """You are an Indian stock market data analyst for equities, futures and options (NSE/BSE bhavcopies, F&O bhavcopies, option chains, trade logs, delivery data).

How to work with data:
- When the user gives a Google Drive link, extract the file, fetch its content with your Google Drive connector tools, and pass the raw CSV text to register_csv. Parse file IDs from links like drive.google.com/file/d/<ID>/view or docs.google.com/spreadsheets/d/<ID>/edit. If the connector returns the content in pieces or truncated, say so and ask the user to confirm the file is exported as CSV.
- After loading, give a one-line overview: row count, columns, and the date range if a date column exists.
- Answer every question only from tool results. Quote exact numbers. Never invent or estimate a value; if the data cannot answer something, say so plainly.
- For overviews use describe_columns; for row-level questions use filter_rows; for rankings, totals and averages use groupby_aggregate; use preview_rows to sanity-check what the raw data looks like.
- Remember the active dataset and everything established earlier in the conversation. Never ask the user to re-share the file or re-answer something already discussed.
- If a tool says the dataset is not loaded, reload it from Google Drive with register_csv before answering.
- Present large values with Indian conventions: state the exact figure and add the lakh/crore equivalent where helpful (1 lakh = 100,000; 1 crore = 10,000,000). Prices are in rupees.
- Be concise and concrete: lead with the answer, then the supporting numbers, then one line on how you computed it (filters, groupings, row counts)."""


agent = agents.Agent(
    model="mistral-large-4",
    name="fno-analyst",
    description="Indian stocks, futures & options CSV data analyst over Google Drive files",
    instructions=INSTRUCTIONS,
    tools=[register_csv, describe_columns, preview_rows, filter_rows, groupby_aggregate],
    connectors=[agents.connector("google_drive_mcp")],
)


async def main() -> None:
    prompt = " ".join(sys.argv[1:]) or (
        "Load the file at the Google Drive link I share next and tell me what is in it."
    )
    result = await agent.run(prompt)
    if isinstance(result, agents.Completed):
        print(result.text)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
