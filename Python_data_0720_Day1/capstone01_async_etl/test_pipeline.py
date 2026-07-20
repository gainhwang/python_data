# ============================================================
# 종합실습 1 - pytest 테스트
# test_pipeline.py
# ============================================================

import pandas as pd

from models import Product
from pipeline import load, transform


# ------------------------------------------------------------
# 테스트 1. 카테고리 소문자화
# ------------------------------------------------------------

def test_category_lowercase():
    """
    카테고리의 공백이 제거되고 소문자로 바뀌는지 검사한다.
    """

    rows = [
        {
            "id": 1,
            "name": "Apple",
            "category": " FOOD ",
            "price": 1000,
        }
    ]

    valid, invalid = transform(rows)

    assert len(valid) == 1
    assert len(invalid) == 0
    assert valid[0].category == "food"


# ------------------------------------------------------------
# 테스트 2. 상품명 공백 제거
# ------------------------------------------------------------

def test_name_strip():
    """
    상품명의 앞뒤 공백이 제거되는지 검사한다.
    """

    product = Product(
        id=1,
        name="  Apple  ",
        category="food",
        price=1000,
    )

    assert product.name == "Apple"


# ------------------------------------------------------------
# 테스트 3. 음수 가격 거부
# ------------------------------------------------------------

def test_negative_price_rejected():
    """
    음수 가격이 오염 데이터로 분류되는지 검사한다.
    """

    rows = [
        {
            "id": 1,
            "name": "Apple",
            "category": "food",
            "price": -500,
        }
    ]

    valid, invalid = transform(rows)

    assert len(valid) == 0
    assert len(invalid) == 1


# ------------------------------------------------------------
# 테스트 4. 유효·무효 건수 합계
# ------------------------------------------------------------

def test_valid_invalid_count_matches_total():
    """
    유효 건수와 무효 건수의 합이
    전체 입력 건수와 같은지 검사한다.
    """

    rows = [
        {
            "id": 1,
            "name": "Apple",
            "category": "food",
            "price": 1000,
        },
        {
            "id": 2,
            "name": "Notebook",
            "category": "BOOK",
            "price": 2000,
        },
        {
            "id": 3,
            "name": "Wrong",
            "category": "food",
            "price": -100,
        },
    ]

    valid, invalid = transform(rows)

    assert len(valid) + len(invalid) == len(rows)
    assert len(valid) == 2
    assert len(invalid) == 1


# ------------------------------------------------------------
# 테스트 5. 필수 필드 누락 거부
# ------------------------------------------------------------

def test_missing_name_rejected():
    """
    필수 필드인 name이 없을 때
    오염 데이터로 분류되는지 검사한다.
    """

    rows = [
        {
            "id": 1,
            "category": "food",
            "price": 1000,
        }
    ]

    valid, invalid = transform(rows)

    assert len(valid) == 0
    assert len(invalid) == 1

    error_fields = [
        error["loc"][0]
        for error in invalid[0]["errors"]
    ]

    assert "name" in error_fields


# ------------------------------------------------------------
# 테스트 6. Parquet 라운드트립
# ------------------------------------------------------------

def test_parquet_round_trip(tmp_path):
    """
    Parquet 파일을 저장했다가 다시 읽었을 때
    원본 DataFrame과 같은지 검사한다.

    tmp_path는 pytest가 제공하는 임시 폴더이다.
    """

    valid = [
        Product(
            id=1,
            name="Apple",
            category="food",
            price=10.5,
        ),
        Product(
            id=2,
            name="Notebook",
            category="book",
            price=20.0,
        ),
    ]

    # 임시 폴더에 CSV와 Parquet을 저장한다.
    original_df = load(
        valid,
        out_dir=str(tmp_path),
    )

    parquet_path = tmp_path / "products.parquet"

    # 저장한 Parquet을 다시 읽는다.
    loaded_df = pd.read_parquet(parquet_path)

    # 저장 전후 DataFrame이 완전히 같은지 검사한다.
    pd.testing.assert_frame_equal(
        original_df,
        loaded_df,
    )