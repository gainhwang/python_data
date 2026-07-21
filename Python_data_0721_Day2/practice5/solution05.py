#=================================
# 실습 5 · Polars · DuckDB 성능 비교
# ================================

import time

import duckdb
import pandas as pd
import polars as pl
from pandas.testing import assert_frame_equal


FILE_PATH = "data/events_large.csv"


# ==================================================
# 1. Pandas
# ==================================================
start = time.perf_counter()

pdf = pd.read_csv(FILE_PATH)

result_pd = (
    pdf.groupby("event_type", as_index=False)
    .agg(
        event_count=("event_id", "count"),
        unique_users=("user_id", "nunique"),
        total_amount=("amount", "sum"),
        avg_amount=("amount", "mean"),
    )
    .sort_values("event_type")
    .reset_index(drop=True)
)

pandas_time = time.perf_counter() - start

print("=" * 60)
print("[Pandas 결과]")
print("=" * 60)
print(result_pd)
print(f"\nPandas 실행시간: {pandas_time:.4f}초")


# ==================================================
# 2. Polars
# scan_csv를 사용한 Lazy 방식
# ==================================================
start = time.perf_counter()

result_pl = (
    pl.scan_csv(FILE_PATH)
    .group_by("event_type")
    .agg(
        pl.len().alias("event_count"),
        pl.col("user_id").n_unique().alias("unique_users"),
        pl.col("amount").sum().alias("total_amount"),
        pl.col("amount").mean().alias("avg_amount"),
    )
    .sort("event_type")
    .collect()
)

polars_time = time.perf_counter() - start

print("\n" + "=" * 60)
print("[Polars 결과]")
print("=" * 60)
print(result_pl)
print(f"\nPolars 실행시간: {polars_time:.4f}초")


# ==================================================
# 3. DuckDB
# ==================================================
start = time.perf_counter()

result_duck = duckdb.sql(
    f"""
    SELECT
        event_type,
        COUNT(*) AS event_count,
        COUNT(DISTINCT user_id) AS unique_users,
        SUM(amount) AS total_amount,
        AVG(amount) AS avg_amount
    FROM read_csv_auto('{FILE_PATH}')
    GROUP BY event_type
    ORDER BY event_type
    """
).df()

duckdb_time = time.perf_counter() - start

print("\n" + "=" * 60)
print("[DuckDB 결과]")
print("=" * 60)
print(result_duck)
print(f"\nDuckDB 실행시간: {duckdb_time:.4f}초")


# ==================================================
# 4. 결과 형식 맞추기
# ==================================================

# Polars 결과를 Pandas DataFrame으로 변환
result_pl_pd = result_pl.to_pandas()

# 컬럼 순서 통일
column_order = [
    "event_type",
    "event_count",
    "unique_users",
    "total_amount",
    "avg_amount",
]

result_pd = result_pd[column_order]
result_pl_pd = result_pl_pd[column_order]
result_duck = result_duck[column_order]

# 정렬 및 인덱스 초기화
result_pd = (
    result_pd.sort_values("event_type")
    .reset_index(drop=True)
)

result_pl_pd = (
    result_pl_pd.sort_values("event_type")
    .reset_index(drop=True)
)

result_duck = (
    result_duck.sort_values("event_type")
    .reset_index(drop=True)
)

# 비교하기 쉽도록 일부 숫자 타입 통일
integer_columns = [
    "event_count",
    "unique_users",
]

for column in integer_columns:
    result_pd[column] = result_pd[column].astype("int64")
    result_pl_pd[column] = result_pl_pd[column].astype("int64")
    result_duck[column] = result_duck[column].astype("int64")

float_columns = [
    "total_amount",
    "avg_amount",
]

for column in float_columns:
    result_pd[column] = result_pd[column].astype("float64")
    result_pl_pd[column] = result_pl_pd[column].astype("float64")
    result_duck[column] = result_duck[column].astype("float64")


# ==================================================
# 5. 결과 동일성 검증
# ==================================================
print("\n" + "=" * 60)
print("[결과 동일성 검증]")
print("=" * 60)

assert_frame_equal(
    result_pd,
    result_pl_pd,
    check_dtype=False,
    rtol=1e-5,
    atol=1e-5,
)

print("Pandas와 Polars 결과가 같습니다.")

assert_frame_equal(
    result_pd,
    result_duck,
    check_dtype=False,
    rtol=1e-5,
    atol=1e-5,
)

print("Pandas와 DuckDB 결과가 같습니다.")


# ==================================================
# 6. 실행시간 비교
# ==================================================
timing_result = pd.DataFrame(
    {
        "library": [
            "Pandas",
            "Polars",
            "DuckDB",
        ],
        "seconds": [
            pandas_time,
            polars_time,
            duckdb_time,
        ],
    }
).sort_values("seconds")

timing_result["seconds"] = timing_result["seconds"].round(4)

print("\n" + "=" * 60)
print("[실행시간 비교]")
print("=" * 60)
print(timing_result.to_string(index=False))

fastest = timing_result.iloc[0]["library"]

print(f"\n가장 빠른 라이브러리: {fastest}")