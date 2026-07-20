# ============================================================
# 종합실습 1 - Pydantic 데이터 모델
# models.py
# ============================================================

from pydantic import BaseModel, Field, field_validator


class Product(BaseModel):
    """
    비동기로 수집한 상품 데이터를 검증하는 모델이다.
    """

    # 상품 번호
    id: int

    # 상품 이름
    name: str

    # 상품 카테고리
    category: str

    # 가격은 반드시 0보다 커야 한다.
    price: float = Field(gt=0)


    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """
        상품명의 앞뒤 공백을 제거하고,
        빈 문자열은 허용하지 않는다.
        """

        value = value.strip()

        if not value:
            raise ValueError("상품명은 비어 있을 수 없습니다.")

        return value


    @field_validator("category")
    @classmethod
    def lower_category(cls, value: str) -> str:
        """
        카테고리의 앞뒤 공백을 제거하고
        소문자로 정규화한다.

        예:
        ' FOOD ' → 'food'
        """

        value = value.strip().lower()

        if not value:
            raise ValueError("카테고리는 비어 있을 수 없습니다.")

        return value