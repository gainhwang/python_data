# ============================================================
# 실습 2 : Pydantic v2 중첩 스키마 검증
# ============================================================

import json
from typing import List

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
)


# ------------------------------------------------------------
# STEP 0. JSON 파일 불러오기
# ------------------------------------------------------------

# api_response.json 파일을 읽어서 파이썬 딕셔너리로 변환한다.
with open("data/api_response.json", encoding="utf-8") as f:
    raw_data = json.load(f)


# 최상위 데이터 구조를 확인한다.
print("최상위 데이터 타입:", type(raw_data).__name__)
print("최상위 키:", list(raw_data.keys()))


# 실제 사용자 데이터는 results 키 안에 들어 있다.
data = raw_data["results"]


# 전체 건수를 출력한다.
print("전체 건수:", len(data))


# 첫 번째 사용자 데이터를 보기 좋게 출력한다.
print("\n[정상 샘플 1건]")
print(json.dumps(data[0], indent=2, ensure_ascii=False))


# 앞 10건의 필드명과 값 타입을 확인한다.
print("\n[앞 10건의 필드별 자료형]")

for i, row in enumerate(data[:10]):
    print(
        i,
        {key: type(value).__name__ for key, value in row.items()}
    )


# ------------------------------------------------------------
# STEP 1. 중첩된 profile 모델 만들기
# ------------------------------------------------------------

class Profile(BaseModel):
    """사용자의 프로필 정보를 검증하는 모델"""

    # 국가는 문자열이어야 한다.
    country: str

    # 회원 등급은 문자열이어야 한다.
    tier: str

    # 점수는 0 이상 100 이하이어야 한다.
    score: float = Field(ge=0, le=100)


    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        """
        국가 코드의 앞뒤 공백을 제거하고
        대문자로 통일한다.
        """

        value = value.strip().upper()

        if not value:
            raise ValueError("country는 비어 있을 수 없습니다.")

        return value


    @field_validator("tier")
    @classmethod
    def normalize_tier(cls, value: str) -> str:
        """
        회원 등급의 앞뒤 공백을 제거하고
        소문자로 통일한다.
        """

        value = value.strip().lower()

        if not value:
            raise ValueError("tier는 비어 있을 수 없습니다.")

        return value


# ------------------------------------------------------------
# STEP 2. 사용자 모델 만들기
# ------------------------------------------------------------

class User(BaseModel):
    """외부 API에서 받은 사용자 정보를 검증하는 모델"""

    # 사용자 번호는 정수여야 한다.
    id: int

    # 사용자 이름은 문자열이어야 한다.
    username: str

    # EmailStr을 사용해 이메일 형식까지 검증한다.
    email: EmailStr

    # 나이는 0 이상이어야 한다.
    age: int = Field(ge=0)

    # 활성 상태는 참 또는 거짓이어야 한다.
    is_active: bool

    # 가입일은 문자열 형태로 받는다.
    signup_date: str

    # profile은 Profile 모델의 규칙을 따라야 한다.
    profile: Profile

    # tags는 문자열이 들어 있는 리스트이다.
    tags: List[str]


    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """
        사용자 이름의 앞뒤 공백을 제거하고
        빈 문자열인지 검사한다.
        """

        value = value.strip()

        if not value:
            raise ValueError("username은 비어 있을 수 없습니다.")

        return value


# ------------------------------------------------------------
# STEP 3. 간단한 정상 데이터 테스트
# ------------------------------------------------------------

print("\n[간단한 모델 테스트]")

try:
    test_user = User(
        id=1,
        username="user_test",
        email="test@example.com",
        age=25,
        is_active=True,
        signup_date="2026-07-20",
        profile={
            "country": "kr",
            "tier": "pro",
            "score": 95.5,
        },
        tags=["python", "data"],
    )

    print("정상 데이터 통과:")
    print(test_user)

except ValidationError as e:
    print("정상 데이터 테스트 실패:")
    print(e)


# ------------------------------------------------------------
# STEP 4. 간단한 잘못된 데이터 테스트
# ------------------------------------------------------------

try:
    User(
        id=2,
        username="user_wrong",
        email="이메일아님",
        age=-5,
        is_active=True,
        signup_date="2026-07-20",
        profile={
            "country": "KR",
            "tier": "free",
            "score": 150,
        },
        tags=["python"],
    )

except ValidationError as e:
    print("\n잘못된 데이터가 정상적으로 걸러졌습니다.")
    print(e)


# ------------------------------------------------------------
# STEP 5. 전체 데이터를 유효 데이터와 오염 데이터로 분리
# ------------------------------------------------------------

# 검증을 통과한 사용자 데이터를 저장한다.
valid = []

# 검증에 실패한 데이터와 실패 이유를 저장한다.
invalid = []


# 전체 데이터를 한 건씩 검사한다.
for index, row in enumerate(data):

    try:
        # 딕셔너리를 User 모델에 전달해 검증한다.
        user = User(**row)

        # 검증을 통과한 데이터를 저장한다.
        valid.append(user)

    except ValidationError as e:
        # 검증에 실패해도 프로그램은 멈추지 않는다.
        # 실패한 데이터와 오류 이유를 저장한다.
        invalid.append(
            {
                "index": index,
                "id": row.get("id"),
                "data": row,
                "errors": e.errors(),
            }
        )


# ------------------------------------------------------------
# STEP 6. 전체 검증 결과 출력
# ------------------------------------------------------------

print("\n" + "=" * 50)
print("[전체 검증 결과]")
print(f"전체 {len(data)}건")
print(f"유효 {len(valid)}건")
print(f"오염 {len(invalid)}건")
print("=" * 50)


# ------------------------------------------------------------
# STEP 7. 오염 데이터의 상세 사유 출력
# ------------------------------------------------------------

print("\n[오염 데이터 상세 사유]")

if not invalid:
    print("오염 데이터가 없습니다.")

else:
    print(f"{'행':<6}{'ID':<6}{'필드':<25}{'사유'}")
    print("-" * 100)

    for item in invalid:

        for error in item["errors"]:

            # 중첩 필드 경로를 점으로 연결한다.
            # 예: profile.score
            field = ".".join(
                str(location) for location in error["loc"]
            )

            print(
                f"{item['index']:<6}"
                f"{str(item['id']):<6}"
                f"{field:<25}"
                f"{error['msg']}"
            )


# ------------------------------------------------------------
# STEP 8. 검증을 통과한 데이터 일부 확인
# ------------------------------------------------------------

print("\n[검증 통과 데이터 앞 3건]")

for user in valid[:3]:

    # Pydantic v2에서는 dict() 대신 model_dump()를 사용한다.
    print(user.model_dump())


# ------------------------------------------------------------
# STEP 9. 오염 데이터 원본 확인
# ------------------------------------------------------------

print("\n[오염 데이터 원본]")

for item in invalid:
    print(
        json.dumps(
            item["data"],
            indent=2,
            ensure_ascii=False,
        )
    )