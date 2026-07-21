#===================================
# 실습4· Pandas 2.x 데이터 정제
#===================================

import pandas as pd

# Pandas 2.x Copy-on-Write 설정
pd.options.mode.copy_on_write = True


# -----------------------------
# 1. 데이터 불러오기
# -----------------------------
df = pd.read_csv("data/sales_raw.csv")

print("=" * 50)
print("[정제 전 데이터 확인]")
print("=" * 50)

print("\n데이터 크기:")
print(df.shape)

print("\n컬럼 정보:")
df.info()

print("\n컬럼별 결측치:")
print(df.isna().sum())

print("\n앞 5행:")
print(df.head())


# -----------------------------
# 2. 타입 정규화
# -----------------------------
df["order_date"] = pd.to_datetime(
    df["order_date"],
    errors="coerce",
)

df["quantity"] = pd.to_numeric(
    df["quantity"],
    errors="coerce",
)

df["unit_price"] = pd.to_numeric(
    df["unit_price"],
    errors="coerce",
)

df["discount"] = pd.to_numeric(
    df["discount"],
    errors="coerce",
)

df["region"] = df["region"].astype("category")
df["category"] = df["category"].astype("category")

print("\n" + "=" * 50)
print("[타입 변환 후]")
print("=" * 50)

print(df.dtypes)

print("\n타입 변환 후 결측치:")
print(df.isna().sum())


# -----------------------------
# 3. 결측치 처리
# -----------------------------

# 카테고리별 가격 중앙값으로 결측치 채우기
df["unit_price"] = (
    df.groupby("category", observed=True)["unit_price"]
    .transform(lambda s: s.fillna(s.median()))
)

# 수량은 전체 중앙값으로 채우기
df["quantity"] = df["quantity"].fillna(
    df["quantity"].median()
)

# 할인율 결측치는 할인 없음인 0으로 채우기
df["discount"] = df["discount"].fillna(0)

# 지역과 카테고리 결측치는 Unknown으로 채우기
df["region"] = (
    df["region"]
    .cat.add_categories(["Unknown"])
    .fillna("Unknown")
)

df["category"] = (
    df["category"]
    .cat.add_categories(["Unknown"])
    .fillna("Unknown")
)

# 잘못된 날짜가 있다면 해당 행 제거
df = df.dropna(subset=["order_date"])

print("\n" + "=" * 50)
print("[결측치 처리 후]")
print("=" * 50)

print(df.isna().sum())


# -----------------------------
# 4. 이상치 처리 함수
# -----------------------------
def winsorize(series, k=1.5):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1

    lower = q1 - k * iqr
    upper = q3 + k * iqr

    return series.clip(
        lower=lower,
        upper=upper,
    )


print("\n" + "=" * 50)
print("[이상치 처리]")
print("=" * 50)

print(
    "가격 처리 전 최댓값:",
    df["unit_price"].max(),
)

print(
    "수량 처리 전 최댓값:",
    df["quantity"].max(),
)

df["unit_price"] = winsorize(df["unit_price"])
df["quantity"] = winsorize(df["quantity"])

print(
    "가격 처리 후 최댓값:",
    df["unit_price"].max(),
)

print(
    "수량 처리 후 최댓값:",
    df["quantity"].max(),
)


# -----------------------------
# 5. 할인 적용 매출액 계산
# -----------------------------
df["amount"] = (
    df["quantity"]
    * df["unit_price"]
    * (1 - df["discount"])
)

print("\n" + "=" * 50)
print("[매출액 계산 결과]")
print("=" * 50)

print(
    df[
        [
            "order_id",
            "quantity",
            "unit_price",
            "discount",
            "amount",
        ]
    ].head()
)


# -----------------------------
# 6. 카테고리별 집계
# -----------------------------
summary = (
    df.groupby("category", observed=True)
    .agg(
        주문수=("order_id", "count"),
        판매수량=("quantity", "sum"),
        평균가격=("unit_price", "mean"),
        중앙가격=("unit_price", "median"),
        평균할인율=("discount", "mean"),
        총매출=("amount", "sum"),
    )
    .round(1)
    .sort_values(
        "총매출",
        ascending=False,
    )
)

print("\n" + "=" * 50)
print("[카테고리별 요약]")
print("=" * 50)

print(summary)


# -----------------------------
# 7. 지역별 집계
# -----------------------------
region_summary = (
    df.groupby("region", observed=True)
    .agg(
        주문수=("order_id", "count"),
        판매수량=("quantity", "sum"),
        총매출=("amount", "sum"),
    )
    .round(1)
    .sort_values(
        "총매출",
        ascending=False,
    )
)

print("\n" + "=" * 50)
print("[지역별 요약]")
print("=" * 50)

print(region_summary)


# -----------------------------
# 8. 카테고리 × 지역 매출 교차표
# -----------------------------
pivot = df.pivot_table(
    index="category",
    columns="region",
    values="amount",
    aggfunc="sum",
    fill_value=0,
    observed=True,
).round(1)

print("\n" + "=" * 50)
print("[카테고리별·지역별 매출]")
print("=" * 50)

print(pivot)


# -----------------------------
# 9. 정제 후 최종 확인
# -----------------------------
print("\n" + "=" * 50)
print("[정제 후 최종 확인]")
print("=" * 50)

print("최종 데이터 크기:", df.shape)

print("\n최종 결측치:")
print(df.isna().sum())

print("\n최종 타입:")
print(df.dtypes)

print("\n정제된 데이터 앞 5행:")
print(df.head())