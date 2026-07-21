# ==================================================
# 종합실습 2 · EDA + 통계 + ML 파이프라인
# ==================================================

from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import polars as pl

from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ==================================================
# 0. 파일 경로와 출력 폴더 설정
# ==================================================

DATA_PATH = "data/telco_churn.csv"
OUTPUT_DIR = Path("output")

# output 폴더가 없으면 자동 생성
OUTPUT_DIR.mkdir(exist_ok=True)


# ==================================================
# 1. Polars로 데이터 불러오기
# ==================================================

df = pl.read_csv(
    DATA_PATH,
    null_values=["", " ", "NA", "null"],
)

print("=" * 60)
print("[1. 데이터 기본 확인]")
print("=" * 60)

print("\n데이터 크기:")
print(df.shape)

print("\n컬럼 이름:")
print(df.columns)

print("\n앞 5행:")
print(df.head())

print("\n데이터 요약:")
print(df.describe())


# ==================================================
# 2. 이탈 고객 비율 확인
# ==================================================

churn_count = (
    df.group_by("churn")
    .agg(
        pl.len().alias("인원")
    )
    .with_columns(
        (
            pl.col("인원")
            / pl.col("인원").sum()
            * 100
        )
        .round(2)
        .alias("비율")
    )
    .sort("churn")
)

print("\n" + "=" * 60)
print("[2. 이탈 여부별 인원과 비율]")
print("=" * 60)

print(churn_count)

print("\nchurn 값의 의미:")
print("0 = 잔류 고객")
print("1 = 이탈 고객")


# ==================================================
# 3. 이탈 고객과 잔류 고객 비교
# ==================================================

churn_summary = (
    df.group_by("churn")
    .agg(
        pl.col("monthly_charges")
        .mean()
        .round(2)
        .alias("평균월요금"),

        pl.col("tenure_months")
        .mean()
        .round(2)
        .alias("평균가입기간"),

        pl.col("total_charges")
        .mean()
        .round(2)
        .alias("평균총요금"),

        pl.col("num_services")
        .mean()
        .round(2)
        .alias("평균서비스수"),

        pl.len().alias("인원"),
    )
    .sort("churn")
)

print("\n" + "=" * 60)
print("[3. 이탈 여부별 고객 비교]")
print("=" * 60)

print(churn_summary)


# ==================================================
# 4. Pandas DataFrame으로 변환
# ==================================================

# Plotly, scipy, scikit-learn은 Pandas 형식으로 처리
pdf = df.to_pandas()

# 숫자형 컬럼을 확실히 숫자로 변환
numeric_conversion_columns = [
    "senior",
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "num_services",
    "churn",
]

for column in numeric_conversion_columns:
    pdf[column] = pd.to_numeric(
        pdf[column],
        errors="coerce",
    )

print("\nPandas 변환 후 결측치:")
print(pdf.isna().sum())


# ==================================================
# 5. Plotly 시각화
# ==================================================

# --------------------------------------------------
# 5-1. 이탈 여부별 월 요금 분포
# --------------------------------------------------

fig_charges = px.box(
    pdf,
    x="churn",
    y="monthly_charges",
    color="churn",
    title="이탈 여부별 월 요금 분포",
    labels={
        "churn": "이탈 여부",
        "monthly_charges": "월 요금",
    },
)

charges_path = OUTPUT_DIR / "churn_charges.html"

fig_charges.write_html(
    charges_path
)


# --------------------------------------------------
# 5-2. 계약 유형별 이탈 고객 수
# --------------------------------------------------

contract_count = (
    pdf.groupby(
        ["contract", "churn"],
        as_index=False,
    )
    .size()
    .rename(
        columns={
            "size": "count"
        }
    )
)

fig_contract = px.bar(
    contract_count,
    x="contract",
    y="count",
    color="churn",
    barmode="group",
    title="계약 유형별 이탈 여부",
    labels={
        "contract": "계약 유형",
        "count": "고객 수",
        "churn": "이탈 여부",
    },
)

contract_path = OUTPUT_DIR / "contract_churn.html"

fig_contract.write_html(
    contract_path
)


# --------------------------------------------------
# 5-3. 가입 기간과 월 요금 관계
# --------------------------------------------------

fig_tenure = px.scatter(
    pdf,
    x="tenure_months",
    y="monthly_charges",
    color="churn",
    title="가입 기간과 월 요금 관계",
    labels={
        "tenure_months": "가입 기간(개월)",
        "monthly_charges": "월 요금",
        "churn": "이탈 여부",
    },
)

tenure_path = OUTPUT_DIR / "tenure_charges.html"

fig_tenure.write_html(
    tenure_path
)

print("\n" + "=" * 60)
print("[4. Plotly HTML 저장 완료]")
print("=" * 60)

print(f"- {charges_path}")
print(f"- {contract_path}")
print(f"- {tenure_path}")


# ==================================================
# 6. 통계 검정
# ==================================================

print("\n" + "=" * 60)
print("[5. 통계 검정]")
print("=" * 60)


# --------------------------------------------------
# 6-1. t-검정
# 이탈 고객과 잔류 고객의 월 요금 평균 비교
# --------------------------------------------------

churn_yes_charges = pdf.loc[
    pdf["churn"] == 1,
    "monthly_charges",
].dropna()

churn_no_charges = pdf.loc[
    pdf["churn"] == 0,
    "monthly_charges",
].dropna()

t_statistic, t_pvalue = stats.ttest_ind(
    churn_yes_charges,
    churn_no_charges,
    equal_var=False,
)

print("\n[t-검정]")
print("이탈 고객과 잔류 고객의 월 요금 평균 비교")

print(
    "이탈 고객 평균 월 요금:",
    round(churn_yes_charges.mean(), 2),
)

print(
    "잔류 고객 평균 월 요금:",
    round(churn_no_charges.mean(), 2),
)

print(f"t 통계량 = {t_statistic:.4f}")
print(f"t-검정 p값 = {t_pvalue:.2e}")

if t_pvalue < 0.05:
    print(
        "결론: 두 고객 집단의 월 요금에는 "
        "통계적으로 유의한 차이가 있습니다."
    )
else:
    print(
        "결론: 두 고객 집단의 월 요금에는 "
        "통계적으로 유의한 차이가 없습니다."
    )


# --------------------------------------------------
# 6-2. 카이제곱 검정
# 계약 유형과 이탈 여부의 연관성 확인
# --------------------------------------------------

contingency_table = pd.crosstab(
    pdf["contract"],
    pdf["churn"],
)

chi2, chi_pvalue, dof, expected = (
    stats.chi2_contingency(
        contingency_table
    )
)

print("\n[카이제곱 검정]")
print("계약 유형과 이탈 여부의 연관성 확인")

print("\n교차표:")
print(contingency_table)

print(f"\n카이제곱 통계량 = {chi2:.4f}")
print(f"카이제곱 p값 = {chi_pvalue:.2e}")
print(f"자유도 = {dof}")

if chi_pvalue < 0.05:
    print(
        "결론: 계약 유형과 이탈 여부는 "
        "통계적으로 유의한 연관이 있습니다."
    )
else:
    print(
        "결론: 계약 유형과 이탈 여부에서 "
        "통계적으로 유의한 연관을 확인하지 못했습니다."
    )

print(
    "\n주의: 통계적으로 연관이 있다는 것은 "
    "원인과 결과를 의미하지 않습니다."
)


# ==================================================
# 7. 머신러닝 데이터 준비
# ==================================================

# customer_id는 고객을 구분하는 번호이므로
# 예측에 사용할 입력 변수에서 제외
X = pdf.drop(
    columns=[
        "customer_id",
        "churn",
    ]
)

# churn은 이미 0 또는 1
y = pdf["churn"].astype(int)

print("\n" + "=" * 60)
print("[6. 머신러닝 데이터 준비]")
print("=" * 60)

print("입력 데이터 크기:")
print(X.shape)

print("\n타깃 데이터 크기:")
print(y.shape)

print("\n타깃 비율:")
print(
    y.value_counts(
        normalize=True
    ).sort_index()
)


# ==================================================
# 8. 숫자형과 범주형 컬럼 구분
# ==================================================

numeric_columns = (
    X.select_dtypes(
        include=["number"]
    )
    .columns
    .tolist()
)

categorical_columns = (
    X.select_dtypes(
        exclude=["number"]
    )
    .columns
    .tolist()
)

print("\n숫자형 컬럼:")
print(numeric_columns)

print("\n범주형 컬럼:")
print(categorical_columns)


# ==================================================
# 9. 숫자형 전처리
# ==================================================

numeric_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            ),
        ),
        (
            "scaler",
            StandardScaler(),
        ),
    ]
)


# ==================================================
# 10. 범주형 전처리
# ==================================================

categorical_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            ),
        ),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore"
            ),
        ),
    ]
)


# ==================================================
# 11. ColumnTransformer
# ==================================================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            numeric_pipeline,
            numeric_columns,
        ),
        (
            "categorical",
            categorical_pipeline,
            categorical_columns,
        ),
    ]
)


# ==================================================
# 12. 훈련 데이터와 테스트 데이터 분리
# ==================================================

X_train, X_test, y_train, y_test = (
    train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
)

print("\n" + "=" * 60)
print("[7. 훈련·테스트 데이터 분리]")
print("=" * 60)

print("훈련 데이터:")
print(X_train.shape)

print("테스트 데이터:")
print(X_test.shape)

print("\n훈련 데이터의 이탈 비율:")
print(y_train.mean())

print("테스트 데이터의 이탈 비율:")
print(y_test.mean())


# ==================================================
# 13. RandomForest 모델 생성
# ==================================================

model_pipeline = Pipeline(
    steps=[
        (
            "preprocessor",
            preprocessor,
        ),
        (
            "model",
            RandomForestClassifier(
                n_estimators=200,
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ]
)


# ==================================================
# 14. 모델 학습
# ==================================================

print("\n" + "=" * 60)
print("[8. 모델 학습]")
print("=" * 60)

model_pipeline.fit(
    X_train,
    y_train,
)

print("모델 학습이 완료되었습니다.")


# ==================================================
# 15. 모델 예측
# ==================================================

# 일반 예측 결과: 0 또는 1
y_prediction = model_pipeline.predict(
    X_test
)

# ROC-AUC 계산용 이탈 확률
y_probability = (
    model_pipeline.predict_proba(
        X_test
    )[:, 1]
)


# ==================================================
# 16. ROC-AUC 평가
# ==================================================

roc_auc = roc_auc_score(
    y_test,
    y_probability,
)

print("\n" + "=" * 60)
print("[9. 모델 평가]")
print("=" * 60)

print(f"ROC-AUC = {roc_auc:.3f}")

print("\n분류 평가표:")
print(
    classification_report(
        y_test,
        y_prediction,
        target_names=[
            "잔류",
            "이탈",
        ],
        zero_division=0,
    )
)


# ==================================================
# 17. 모델 저장
# ==================================================

model_path = (
    OUTPUT_DIR
    / "churn_model.joblib"
)

joblib.dump(
    model_pipeline,
    model_path,
)

print("\n" + "=" * 60)
print("[10. 모델 저장 완료]")
print("=" * 60)

print(f"모델 파일: {model_path}")


# ==================================================
# 18. 분석 결과를 텍스트 파일로 저장
# ==================================================

result_text = f"""
종합과제 2 분석 결과

1. t-검정
t 통계량: {t_statistic:.4f}
p값: {t_pvalue:.2e}

2. 카이제곱 검정
카이제곱 통계량: {chi2:.4f}
p값: {chi_pvalue:.2e}
자유도: {dof}

3. 머신러닝 평가
ROC-AUC: {roc_auc:.3f}

해석 주의:
통계적으로 유의한 연관이 있다는 것은
직접적인 인과관계를 의미하지 않습니다.
"""

result_path = (
    OUTPUT_DIR
    / "analysis_result.txt"
)

result_path.write_text(
    result_text,
    encoding="utf-8",
)


# ==================================================
# 19. 최종 결과 확인
# ==================================================

print("\n" + "=" * 60)
print("[종합과제 2 완료]")
print("=" * 60)

print(f"t-검정 p값: {t_pvalue:.2e}")
print(f"카이제곱 p값: {chi_pvalue:.2e}")
print(f"ROC-AUC: {roc_auc:.3f}")

print("\n생성된 파일:")
print(f"- {charges_path}")
print(f"- {contract_path}")
print(f"- {tenure_path}")
print(f"- {model_path}")
print(f"- {result_path}")