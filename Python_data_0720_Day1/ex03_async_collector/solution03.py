# ============================================================
# 실습 3 : asyncio 기반 비동기 수집기
# ============================================================

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List


# ------------------------------------------------------------
# STEP 0. 기본 설정
# ------------------------------------------------------------

# False이면 인터넷을 사용하지 않고 모의 요청을 실행한다.
# 실습에서는 기본값을 False로 사용한다.
USE_REAL_HTTP = False

# 수집할 데이터의 전체 개수
TOTAL_ITEMS = 60

# 동시에 실행할 수 있는 요청의 최대 개수
MAX_CONCURRENT = 10

# 요청 한 건의 제한 시간(초)
REQUEST_TIMEOUT = 3.0

# 한 요청이 실패했을 때 재시도할 최대 횟수
MAX_RETRIES = 3

# 모의 네트워크 요청의 대기 시간
# 10개씩 6번 처리되므로 전체 약 1.5~2초가 걸린다.
MOCK_DELAY = 0.25

# 실제 HTTP 요청을 사용할 때 필요한 주소
REAL_HTTP_URL = "https://jsonplaceholder.typicode.com/todos"

# 최종 실패 데이터를 저장할 파일 경로
DEAD_LETTER_PATH = Path("data/dead_letter.json")


# ------------------------------------------------------------
# STEP 1. 모의 네트워크 요청 함수
# ------------------------------------------------------------

async def mock_request(item_id: int) -> Dict[str, Any]:
    """
    실제 API 요청 대신 네트워크 대기 시간을 흉내 내는 함수이다.

    asyncio.sleep()은 기다리는 동안 다른 작업이 실행될 수 있게 한다.
    async 함수 안에서는 time.sleep()을 사용하면 안 된다.
    """

    # 네트워크 응답을 기다리는 상황을 모의한다.
    await asyncio.sleep(MOCK_DELAY)

    # 정상적인 API 응답과 비슷한 딕셔너리를 반환한다.
    return {
        "id": item_id,
        "title": f"item_{item_id:03d}",
        "source": "mock",
        "ok": True,
    }


# ------------------------------------------------------------
# STEP 2. 실제 HTTP 요청 함수
# ------------------------------------------------------------

async def real_http_request(
    client: Any,
    item_id: int,
) -> Dict[str, Any]:
    """
    USE_REAL_HTTP가 True일 때 실제 HTTP 요청을 보내는 함수이다.

    httpx.AsyncClient를 사용하므로 비동기 방식으로 요청한다.
    """

    response = await client.get(
        f"{REAL_HTTP_URL}/{item_id}",
    )

    # 400 또는 500번대 응답이면 예외를 발생시킨다.
    response.raise_for_status()

    data = response.json()

    return {
        "id": item_id,
        "title": data.get("title"),
        "source": "real_http",
        "ok": True,
    }


# ------------------------------------------------------------
# STEP 3. 요청 한 건을 실행하는 함수
# ------------------------------------------------------------

async def do_request(
    item_id: int,
    client: Any = None,
) -> Dict[str, Any]:
    """
    설정에 따라 모의 요청 또는 실제 HTTP 요청을 실행한다.
    """

    if USE_REAL_HTTP:
        return await real_http_request(client, item_id)

    return await mock_request(item_id)


# ------------------------------------------------------------
# STEP 4. Semaphore와 재시도를 적용한 수집 함수
# ------------------------------------------------------------

async def fetch_with_retry(
    item_id: int,
    semaphore: asyncio.Semaphore,
    client: Any = None,
    max_retries: int = MAX_RETRIES,
) -> Dict[str, Any]:
    """
    데이터 한 건을 수집한다.

    주요 기능:
    1. Semaphore로 동시 요청 수 제한
    2. wait_for로 요청 시간 제한
    3. 실패 시 최대 3회 재시도
    4. 재시도 사이에 지수 백오프 적용
    """

    # attempt는 0, 1, 2 순서로 증가한다.
    for attempt in range(max_retries):

        try:
            # Semaphore 입장권을 받은 요청만 실행된다.
            async with semaphore:

                # Python 3.9에서도 사용할 수 있도록
                # asyncio.wait_for()로 타임아웃을 적용한다.
                result = await asyncio.wait_for(
                    do_request(item_id, client),
                    timeout=REQUEST_TIMEOUT,
                )

                # 몇 번째 시도에서 성공했는지 기록한다.
                result["attempt"] = attempt + 1

                return result

        except asyncio.TimeoutError:
            # 제한 시간을 넘긴 경우의 오류 메시지
            error_message = (
                f"요청 시간이 {REQUEST_TIMEOUT}초를 초과했습니다."
            )

        except Exception as error:
            # 네트워크 오류 등 일반적인 요청 실패 사유
            error_message = str(error)

        # 현재 시도가 마지막 시도라면 더 이상 재시도하지 않는다.
        if attempt == max_retries - 1:
            return {
                "id": item_id,
                "ok": False,
                "error": error_message,
                "attempt": attempt + 1,
            }

        # 실패할 때마다 대기 시간을 늘린다.
        # attempt가 0이면 1초, 1이면 2초 대기한다.
        wait_seconds = 2 ** attempt

        print(
            f"[재시도] ID {item_id}: "
            f"{error_message} → {wait_seconds}초 후 재시도"
        )

        # 비동기 함수에서는 반드시 asyncio.sleep()을 사용한다.
        await asyncio.sleep(wait_seconds)

    # 일반적으로 실행되지 않지만 안전을 위한 반환값이다.
    return {
        "id": item_id,
        "ok": False,
        "error": "알 수 없는 오류",
        "attempt": max_retries,
    }


# ------------------------------------------------------------
# STEP 5. 전체 60건을 동시에 수집하는 함수
# ------------------------------------------------------------

async def collect_all() -> List[Dict[str, Any]]:
    """
    전체 데이터 60건을 비동기로 수집한다.

    gather를 이용해 여러 코루틴을 동시에 실행하며,
    Semaphore가 실제 동시 실행 수를 10개로 제한한다.
    """

    # 동시에 최대 10개만 실행할 수 있도록 입장권을 만든다.
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # 수집할 ID는 1부터 60까지이다.
    item_ids = range(1, TOTAL_ITEMS + 1)

    # 실제 HTTP 사용 여부에 따라 실행 방식을 구분한다.
    if USE_REAL_HTTP:
        try:
            # httpx는 실제 HTTP 요청을 사용할 때만 불러온다.
            import httpx

        except ImportError as error:
            raise ImportError(
                "실제 HTTP 요청을 사용하려면 "
                "`pip install httpx`를 실행하세요."
            ) from error

        async with httpx.AsyncClient() as client:
            tasks = [
                fetch_with_retry(
                    item_id=item_id,
                    semaphore=semaphore,
                    client=client,
                )
                for item_id in item_ids
            ]

            # return_exceptions=True를 사용하면
            # 하나가 실패해도 다른 작업은 계속 실행된다.
            raw_results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

    else:
        # 모의 실행에서는 HTTP 클라이언트가 필요 없다.
        tasks = [
            fetch_with_retry(
                item_id=item_id,
                semaphore=semaphore,
            )
            for item_id in item_ids
        ]

        raw_results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

    # gather 자체에서 반환된 예외도 일반 결과 형태로 변환한다.
    results: List[Dict[str, Any]] = []

    for item_id, result in zip(item_ids, raw_results):

        if isinstance(result, Exception):
            results.append(
                {
                    "id": item_id,
                    "ok": False,
                    "error": str(result),
                    "attempt": 0,
                }
            )

        else:
            results.append(result)

    return results


# ------------------------------------------------------------
# STEP 6. 최종 실패 데이터를 파일로 저장하는 함수
# ------------------------------------------------------------

def save_dead_letters(
    failed_results: List[Dict[str, Any]],
) -> None:
    """
    재시도 후에도 실패한 데이터를 dead_letter.json에 저장한다.

    실패 데이터가 없으면 기존 파일이 있더라도 빈 리스트를 저장한다.
    """

    # data 폴더가 없으면 자동으로 생성한다.
    DEAD_LETTER_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with DEAD_LETTER_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            failed_results,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ------------------------------------------------------------
# STEP 7. 실행 결과를 출력하는 메인 함수
# ------------------------------------------------------------

async def main() -> None:
    """
    전체 비동기 수집을 실행하고 결과를 출력한다.
    """

    print("=" * 55)
    print("asyncio 기반 비동기 수집기")
    print("=" * 55)

    print(f"실행 방식       : {'실제 HTTP' if USE_REAL_HTTP else '모의 실행'}")
    print(f"전체 요청 수    : {TOTAL_ITEMS}건")
    print(f"최대 동시 요청  : {MAX_CONCURRENT}건")
    print(f"최대 재시도     : {MAX_RETRIES}회")
    print(f"요청 제한 시간  : {REQUEST_TIMEOUT}초")
    print("-" * 55)

    # 실행 시작 시간을 기록한다.
    start_time = time.perf_counter()

    # 전체 비동기 수집을 실행한다.
    results = await collect_all()

    # 실행 종료 후 걸린 시간을 계산한다.
    elapsed_time = time.perf_counter() - start_time

    # 성공 데이터와 실패 데이터를 분리한다.
    success_results = [
        result
        for result in results
        if result.get("ok") is True
    ]

    failed_results = [
        result
        for result in results
        if result.get("ok") is not True
    ]

    # 최종 실패 데이터는 별도 JSON 파일에 저장한다.
    save_dead_letters(failed_results)

    # 최종 결과를 출력한다.
    print("\n" + "=" * 55)
    print("[수집 결과]")
    print(f"전체   : {len(results)}건")
    print(f"성공   : {len(success_results)}건")
    print(f"실패   : {len(failed_results)}건")
    print(f"소요시간: {elapsed_time:.2f}초")
    print("=" * 55)

    # 성공 데이터 중 앞의 5건만 확인한다.
    print("\n[성공 데이터 앞 5건]")

    for result in success_results[:5]:
        print(result)

    # 실패 데이터가 있으면 상세 사유를 출력한다.
    if failed_results:
        print("\n[최종 실패 데이터]")

        for result in failed_results:
            print(
                f"ID {result.get('id')} → "
                f"{result.get('error')}"
            )

        print(
            f"\n실패 데이터 저장 위치: "
            f"{DEAD_LETTER_PATH}"
        )

    else:
        print("\n최종 실패 데이터가 없습니다.")
        print(
            f"dead-letter 파일에는 빈 목록이 저장되었습니다: "
            f"{DEAD_LETTER_PATH}"
        )


# ------------------------------------------------------------
# STEP 8. 프로그램 시작점
# ------------------------------------------------------------

if __name__ == "__main__":
    # 비동기 프로그램은 asyncio.run()으로 시작한다.
    asyncio.run(main())