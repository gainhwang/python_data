# ============================================================
# 종합실습 1 - 비동기 ETL 파이프라인
# pipeline.py
# ============================================================

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from pydantic import ValidationError

from models import Product


# ------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------

# 전체 수집 데이터 수
TOTAL_ITEMS = 60

# 동시에 실행할 최대 요청 수
MAX_CONCURRENT = 10

# 요청 한 건의 제한 시간
REQUEST_TIMEOUT = 3.0

# 최대 시도 횟수
MAX_RETRIES = 3

# 모의 네트워크 대기 시간
MOCK_DELAY = 0.25

# 결과 저장 폴더
DEFAULT_OUTPUT_DIR = "output"


# ------------------------------------------------------------
# STEP 1. 모의 API 요청
# Extract에서 사용할 네트워크 요청 역할
# ------------------------------------------------------------

async def fetch(item_id: int) -> Dict[str, Any]:
    """
    실제 API 호출 대신 네트워크 대기를 모의한다.

    60건 중 일부 데이터는 검증 연습을 위해
    의도적으로 잘못된 값으로 생성한다.
    """

    # 네트워크 응답 대기를 흉내 낸다.
    await asyncio.sleep(MOCK_DELAY)

    # 기본 정상 데이터
    product = {
        "id": item_id,
        "name": f"Product {item_id}",
        "category": [" FOOD ", "Electronics", "BOOK"][item_id % 3],
        "price": float(item_id * 1000),
    }

    # 오염 데이터 1: 음수 가격
    if item_id == 7:
        product["price"] = -5000

    # 오염 데이터 2: 가격이 0
    elif item_id == 13:
        product["price"] = 0

    # 오염 데이터 3: 필수 필드 name 누락
    elif item_id == 21:
        product.pop("name")

    # 오염 데이터 4: 빈 카테고리
    elif item_id == 29:
        product["category"] = "   "

    return product


# ------------------------------------------------------------
# STEP 2. Extract
# 비동기 방식으로 여러 데이터를 동시에 수집
# ------------------------------------------------------------

async def extract(
    ids: List[int],
    max_concurrent: int = MAX_CONCURRENT,
) -> List[Dict[str, Any]]:
    """
    여러 상품 데이터를 비동기로 수집한다.

    주요 기능:
    - asyncio.gather로 동시 실행
    - Semaphore로 동시 요청 수 제한
    - 타임아웃
    - 실패 시 재시도
    - 하나가 실패해도 전체 작업 유지
    """

    # 동시 요청 수를 제한하는 Semaphore
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(item_id: int) -> Dict[str, Any]:
        """
        상품 한 건을 수집한다.
        """

        for attempt in range(MAX_RETRIES):

            try:
                # 입장권을 받은 작업만 요청을 실행한다.
                async with semaphore:
                    return await asyncio.wait_for(
                        fetch(item_id),
                        timeout=REQUEST_TIMEOUT,
                    )

            except Exception as error:
                # 마지막 시도까지 실패한 경우 예외를 다시 발생시킨다.
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"ID {item_id} 수집 실패: {error}"
                    ) from error

                # 지수 백오프
                wait_seconds = 2 ** attempt

                print(
                    f"ID {item_id} 수집 실패 → "
                    f"{wait_seconds}초 후 재시도"
                )

                await asyncio.sleep(wait_seconds)

        # 이 위치에는 일반적으로 도달하지 않는다.
        raise RuntimeError(f"ID {item_id} 수집 실패")

    # 여러 요청을 코루틴 목록으로 만든다.
    tasks = [fetch_one(item_id) for item_id in ids]

    # 하나가 실패해도 나머지를 계속 실행한다.
    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    # 성공 결과만 저장한다.
    successful_results = []

    for item_id, result in zip(ids, results):

        if isinstance(result, Exception):
            print(f"[수집 실패] ID {item_id}: {result}")
        else:
            successful_results.append(result)

    return successful_results


# ------------------------------------------------------------
# STEP 3. Transform
# Pydantic으로 유효 데이터와 오염 데이터를 분리
# ------------------------------------------------------------

def transform(
    raw: List[Dict[str, Any]],
) -> Tuple[List[Product], List[Dict[str, Any]]]:
    """
    수집한 원본 데이터를 Pydantic으로 검증한다.

    이 함수는 네트워크나 파일을 건드리지 않는 순수 함수이다.
    따라서 독립적으로 테스트하기 쉽다.
    """

    valid: List[Product] = []
    invalid: List[Dict[str, Any]] = []

    for index, row in enumerate(raw):

        try:
            # 정상 데이터는 Product 객체로 변환한다.
            product = Product(**row)
            valid.append(product)

        except ValidationError as error:
            # 오염 데이터와 실패 이유를 함께 저장한다.
            invalid.append(
                {
                    "index": index,
                    "data": row,
                    "errors": error.errors(),
                }
            )

    return valid, invalid


# ------------------------------------------------------------
# STEP 4. Load
# 유효 데이터를 CSV와 Parquet 파일로 저장
# ------------------------------------------------------------

def load(
    valid: List[Product],
    out_dir: str = DEFAULT_OUTPUT_DIR,
) -> pd.DataFrame:
    """
    검증을 통과한 데이터를 DataFrame으로 만들고
    CSV와 Parquet 파일로 저장한다.
    """

    # 저장 폴더가 없으면 자동으로 생성한다.
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Pydantic v2에서는 model_dump()를 사용한다.
    rows = [product.model_dump() for product in valid]

    # DataFrame 생성
    df = pd.DataFrame(rows)

    # 저장 파일 경로
    csv_path = output_path / "products.csv"
    parquet_path = output_path / "products.parquet"

    # CSV 저장
    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    # Parquet 저장
    df.to_parquet(
        parquet_path,
        index=False,
    )

    return df


# ------------------------------------------------------------
# STEP 5. 오염 데이터 저장
# ------------------------------------------------------------

def save_invalid(
    invalid: List[Dict[str, Any]],
    out_dir: str = DEFAULT_OUTPUT_DIR,
) -> Optional[Path]:
    """
    오염 데이터의 원본과 오류 사유를 JSON 파일로 저장한다.
    """

    import json

    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    invalid_path = output_path / "invalid_records.json"

    with invalid_path.open("w", encoding="utf-8") as file:
        json.dump(
            invalid,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return invalid_path


# ------------------------------------------------------------
# STEP 6. Orchestrate
# run()에서 Extract → Transform → Load 순서로 조율
# ------------------------------------------------------------

async def run(
    ids: List[int],
    out_dir: str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Any]:
    """
    전체 ETL 파이프라인을 실행한다.

    run()은 직접 데이터를 처리하지 않고,
    Extract, Transform, Load 함수를 순서대로 호출한다.
    """

    # 실행시간 측정 시작
    start_time = time.perf_counter()

    # E: 비동기 수집
    raw = await extract(ids)

    # T: 데이터 검증 및 분리
    valid, invalid = transform(raw)

    # L: 정상 데이터 저장
    df = load(valid, out_dir)

    # 오염 데이터도 별도 저장
    invalid_path = save_invalid(invalid, out_dir)

    # 전체 실행시간
    elapsed_time = time.perf_counter() - start_time

    # 실행 결과 요약
    summary = {
        "total": len(raw),
        "valid": len(valid),
        "invalid": len(invalid),
        "rows_saved": len(df),
        "elapsed_seconds": round(elapsed_time, 2),
        "output_directory": out_dir,
        "invalid_file": str(invalid_path),
    }

    return summary


# ------------------------------------------------------------
# STEP 7. 오염 사유 출력
# ------------------------------------------------------------

def print_invalid_details(
    invalid: List[Dict[str, Any]],
) -> None:
    """
    오염 데이터의 필드와 실패 이유를 표 형태로 출력한다.
    """

    print("\n[오염 데이터 상세]")

    if not invalid:
        print("오염 데이터가 없습니다.")
        return

    print(f"{'행':<6}{'ID':<8}{'필드':<20}{'사유'}")
    print("-" * 90)

    for item in invalid:
        row = item["data"]

        for error in item["errors"]:
            field = ".".join(
                str(location)
                for location in error["loc"]
            )

            print(
                f"{item['index']:<6}"
                f"{str(row.get('id')):<8}"
                f"{field:<20}"
                f"{error['msg']}"
            )


# ------------------------------------------------------------
# 프로그램 실행 시작점
# ------------------------------------------------------------

async def main() -> None:
    """
    파이프라인을 실행하고 결과를 출력한다.
    """

    print("=" * 60)
    print("종합실습 1 · 비동기 ETL 파이프라인")
    print("=" * 60)

    ids = list(range(1, TOTAL_ITEMS + 1))

    # 전체 파이프라인 실행
    summary = await run(ids)

    # 오염 데이터 상세 출력을 위해 변환 결과를 다시 확인한다.
    # 실무에서는 run() 결과에 상세 데이터를 포함시키거나
    # 별도 로깅 시스템을 사용할 수 있다.
    raw = await extract(ids)
    _, invalid = transform(raw)

    print_invalid_details(invalid)

    print("\n" + "=" * 60)
    print("[ETL 실행 결과]")
    print(f"전체 수집       : {summary['total']}건")
    print(f"유효 데이터     : {summary['valid']}건")
    print(f"오염 데이터     : {summary['invalid']}건")
    print(f"저장된 행       : {summary['rows_saved']}건")
    print(f"실행시간        : {summary['elapsed_seconds']}초")
    print(f"결과 폴더       : {summary['output_directory']}")
    print("=" * 60)

    print("\n요약 딕셔너리:")
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())