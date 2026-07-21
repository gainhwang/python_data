import argparse
import time

from report import run_once


def main() -> None:
    """
    설정한 시간 간격에 따라 리포트를 반복 생성합니다.
    """

    parser = argparse.ArgumentParser(
        description="매출 리포트 자동 생성기"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help=(
            "반복 실행할 시간 간격(초). "
            "0이면 한 번만 실행합니다."
        ),
    )

    args = parser.parse_args()

    if args.interval < 0:
        raise ValueError(
            "interval은 0 이상의 숫자여야 합니다."
        )

    # interval이 0이면 한 번만 실행
    if args.interval == 0:
        run_once()
        return

    print(
        f"{args.interval}초마다 리포트를 생성합니다."
    )

    print(
        "종료하려면 터미널에서 Ctrl+C를 누르세요."
    )

    try:
        while True:
            run_once()

            print(
                f"{args.interval}초 후 다시 실행합니다."
            )

            time.sleep(
                args.interval
            )

    except KeyboardInterrupt:
        print("\n자동 실행을 종료했습니다.")


if __name__ == "__main__":
    main()