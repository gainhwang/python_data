from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from config import CONFIG


# ==================================================
# 1. 데이터 정제 함수
# ==================================================

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    판매 데이터를 정제하고 amount 컬럼을 생성합니다.
    """

    cleaned = df.copy()

    # 숫자형 변환
    cleaned["quantity"] = pd.to_numeric(
        cleaned["quantity"],
        errors="coerce",
    )

    cleaned["unit_price"] = pd.to_numeric(
        cleaned["unit_price"],
        errors="coerce",
    )

    cleaned["discount"] = pd.to_numeric(
        cleaned["discount"],
        errors="coerce",
    )

    # 결측치 처리
    cleaned["quantity"] = cleaned["quantity"].fillna(
        cleaned["quantity"].median()
    )

    cleaned["unit_price"] = (
        cleaned.groupby("category")["unit_price"]
        .transform(
            lambda series: series.fillna(
                series.median()
            )
        )
    )

    cleaned["discount"] = cleaned["discount"].fillna(0)

    cleaned["category"] = cleaned["category"].fillna(
        "Unknown"
    )

    cleaned["region"] = cleaned["region"].fillna(
        "Unknown"
    )

    # 할인 적용 매출액 계산
    cleaned["amount"] = (
        cleaned["quantity"]
        * cleaned["unit_price"]
        * (1 - cleaned["discount"])
    )

    return cleaned


# ==================================================
# 2. 집계 함수
# ==================================================

def aggregate(
    df: pd.DataFrame,
    top_n: int = 10,
) -> dict:
    """
    데이터프레임을 받아 리포트에 사용할 값을 반환합니다.

    파일을 직접 저장하지 않는 순수 집계 함수입니다.
    """

    kpi = {
        "총매출": float(df["amount"].sum()),
        "주문수": int(len(df)),
        "평균주문액": float(df["amount"].mean()),
        "총판매수량": float(df["quantity"].sum()),
    }

    by_category = (
        df.groupby(
            "category",
            as_index=False,
            observed=True,
        )
        .agg(
            amount=("amount", "sum")
        )
        .sort_values(
            "amount",
            ascending=False,
        )
        .head(top_n)
        .to_dict("records")
    )

    by_region = (
        df.groupby(
            "region",
            as_index=False,
            observed=True,
        )
        .agg(
            amount=("amount", "sum")
        )
        .sort_values(
            "amount",
            ascending=False,
        )
        .to_dict("records")
    )

    return {
        "kpi": kpi,
        "by_category": by_category,
        "by_region": by_region,
    }


# ==================================================
# 3. HTML 렌더링 함수
# ==================================================

def render_report(
    data: dict,
    config=CONFIG,
) -> Path:
    """
    집계 결과를 Jinja2 템플릿에 넣어
    HTML 리포트를 생성합니다.
    """

    environment = Environment(
        loader=FileSystemLoader(
            config.template_dir
        ),
        autoescape=True,
    )

    template = environment.get_template(
        config.template_name
    )

    now = datetime.now()

    html = template.render(
        title=config.title,
        generated_at=now.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        **data,
    )

    # output 폴더가 없으면 자동 생성
    config.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 이전 파일을 덮어쓰지 않도록
    # 파일명에 생성 시각을 포함
    timestamp = now.strftime(
        "%Y%m%d_%H%M%S"
    )

    output_path = (
        config.output_dir
        / f"report_{timestamp}.html"
    )

    output_path.write_text(
        html,
        encoding="utf-8",
    )

    return output_path


# ==================================================
# 4. 1회 실행 함수
# ==================================================

def run_once() -> Path:
    """
    데이터 읽기 → 정제 → 집계 → 리포트 생성을
    한 번 실행합니다.
    """

    print("=" * 60)
    print("[자동 리포트 생성 시작]")
    print("=" * 60)

    print(f"데이터 파일: {CONFIG.data_path}")

    if not CONFIG.data_path.exists():
        raise FileNotFoundError(
            f"데이터 파일을 찾을 수 없습니다: "
            f"{CONFIG.data_path}"
        )

    raw_df = pd.read_csv(
        CONFIG.data_path
    )

    print(f"원본 데이터 크기: {raw_df.shape}")

    cleaned_df = clean_data(
        raw_df
    )

    report_data = aggregate(
        cleaned_df,
        CONFIG.top_n,
    )

    report_path = render_report(
        report_data,
        CONFIG,
    )

    print(f"총매출: {report_data['kpi']['총매출']:,.1f}")
    print(f"주문수: {report_data['kpi']['주문수']:,}")
    print(f"리포트 생성 완료: {report_path}")

    return report_path


# ==================================================
# 5. report.py를 직접 실행했을 때
# ==================================================

if __name__ == "__main__":
    run_once()