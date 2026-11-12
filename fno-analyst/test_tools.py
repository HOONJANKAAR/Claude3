"""Tests for the fixed analysis tools in main.py. Run: uv run python test_tools.py"""

from __future__ import annotations


import shutil
from pathlib import Path

import main

SAMPLE_CSV = """SYMBOL,INSTRUMENT,EXPIRY_DT,OPTION_TYP,STRIKE_PR,CLOSE,SETTLE_PR,CONTRACTS,VALM_IN_LAKHS,OPEN_INT,CHG_IN_OPN_INT,TIMESTAMP
RELIANCE,FUTSTK,2025-06-26,,0,2890.5,2891,125000,360500,2100000,-15000,2025-06-06
RELIANCE,OPTSTK,2025-06-26,CE,2900,45.2,45.2,98000,28100,1900000,54000,2025-06-06
RELIANCE,OPTSTK,2025-06-26,PE,2800,38.9,38.9,87000,22100,1750000,-21000,2025-06-06
HDFCBANK,FUTSTK,2025-06-26,,0,1642.1,1642.5,98000,161000,1500000,30000,2025-06-06
HDFCBANK,OPTSTK,2025-06-26,CE,1650,22.4,22.4,76000,12500,1200000,12000,2025-06-06
INFY,FUTSTK,2025-06-26,,0,1455.75,1456,64000,93200,980000,-8000,2025-06-06
INFY,OPTSTK,2025-06-26,PE,1450,26.1,26.1,58000,8400,900000,15000,2025-06-06
NIFTY,FUTIDX,2025-06-26,,0,23218.4,23220,410000,9520000,12500000,210000,2025-06-06
NIFTY,OPTIDX,2025-06-26,CE,23300,112.35,112.4,520000,12100000,15800000,340000,2025-06-06
NIFTY,OPTIDX,2025-06-26,PE,23000,98.6,98.7,480000,10900000,14200000,-90000,2025-06-06
BANKNIFTY,FUTIDX,2025-06-26,,0,50112.9,50120,190000,9530000,4100000,60000,2025-06-06
BANKNIFTY,OPTIDX,2025-06-26,CE,50200,320.5,320.5,230000,7370000,2400000,88000,2025-06-06
TCS,FUTSTK,2025-06-26,,0,3412,3412.5,41000,70000,520000,9000,2025-06-06
TCS,OPTSTK,2025-06-26,CE,3450,60.15,60.2,33000,3400,310000,-4000,2025-06-06
SBIN,FUTSTK,2025-06-26,,0,842.6,843,152000,64000,1900000,45000,2025-06-06
SBIN,OPTSTK,2025-06-26,PE,830,12.85,12.9,121000,15500,1500000,62000,2025-06-06
NIFTY,OPTIDX,2025-07-31,CE,23500,180.2,180.5,150000,2700000,4000000,110000,2025-06-06
NIFTY,OPTIDX,2025-07-31,PE,22500,165.75,166,130000,2150000,3600000,70000,2025-06-06
"""


def setup() -> None:
    shutil.rmtree(main.CACHE_DIR, ignore_errors=True)
    main._DATAFRAMES.clear()
    main._RECENT.clear()


def run() -> None:
    setup()

    loaded = main.register_csv("NSE F&O June 2025", SAMPLE_CSV)
    assert loaded["rows"] == 18, loaded["rows"]
    assert loaded["columns"]["CLOSE"] == "float64"
    assert loaded["columns"]["SYMBOL"] in ("object", "str")
    assert loaded["preview"][0]["SYMBOL"] == "RELIANCE"

    desc = main.describe_columns()
    assert desc["rows"] == 18
    assert desc["columns"]["CONTRACTS"]["sum"] == 3063000
    assert desc["columns"]["OPTION_TYP"]["top_values"].get("CE", 0) == 6

    preview = main.preview_rows(num_rows=3, start=16)
    assert preview["total_rows"] == 18
    assert preview["rows"][0]["SYMBOL"] == "NIFTY"

    filtered = main.filter_rows(
        conditions=[main.FilterCondition(column="SYMBOL", op="eq", value="NIFTY")],
        order_by="CONTRACTS",
        limit=10,
    )
    assert filtered["matched_rows"] == 5, filtered["matched_rows"]
    assert filtered["rows"][0]["CONTRACTS"] == 130000

    numeric_str = main.filter_rows(
        conditions=[main.FilterCondition(column="STRIKE_PR", op="gt", value=10000)]
    )
    assert numeric_str["matched_rows"] == 5

    between = main.filter_rows(
        conditions=[main.FilterCondition(column="CLOSE", op="between", value=[90, 200])]
    )
    assert between["matched_rows"] == 4, between["matched_rows"]

    contains = main.filter_rows(
        conditions=[main.FilterCondition(column="INSTRUMENT", op="contains", value="OPT")]
    )
    assert contains["matched_rows"] == 11

    grouped = main.groupby_aggregate(
        group_by=["SYMBOL"],
        aggregations=[
            main.Aggregation(column="CONTRACTS", fn="sum"),
            main.Aggregation(column="CLOSE", fn="mean"),
            main.Aggregation(column="EXPIRY_DT", fn="nunique"),
        ],
        order_by="sum_CONTRACTS",
    )
    assert grouped["groups"] == 7
    top = grouped["rows"][0]
    assert top["SYMBOL"] == "NIFTY" and top["sum_CONTRACTS"] == 1690000, top

    grouped_filtered = main.groupby_aggregate(
        group_by=["OPTION_TYP"],
        aggregations=[main.Aggregation(column="VALM_IN_LAKHS", fn="sum")],
        filters=[main.FilterCondition(column="INSTRUMENT", op="eq", value="OPTIDX")],
    )
    assert grouped_filtered["groups"] == 2
    totals = {r["OPTION_TYP"]: r["sum_VALM_IN_LAKHS"] for r in grouped_filtered["rows"]}
    assert totals["CE"] == 22170000 and totals["PE"] == 13050000, totals

    try:
        main.describe_columns(dataset_name="missing-dataset")
    except main.agents.ToolError as exc:
        assert "not loaded" in str(exc)
    else:
        raise AssertionError("expected ToolError for unknown dataset")

    try:
        main.filter_rows(conditions=[main.FilterCondition(column="NOPE", op="eq", value=1)])
    except main.agents.ToolError as exc:
        assert "Unknown column" in str(exc)
    else:
        raise AssertionError("expected ToolError for unknown column")

    print("All tool tests passed.")


if __name__ == "__main__":
    run()
