from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    # 입력 데이터 위치
    data_path: Path = Path("data/sales_raw.csv")

    # HTML 리포트 저장 폴더
    output_dir: Path = Path("output")

    # HTML 템플릿 폴더
    template_dir: Path = Path("templates")

    # 템플릿 파일 이름
    template_name: str = "report.html"

    # 리포트 제목
    title: str = "일일 매출 리포트"

    # 상위 몇 개 카테고리를 표시할지 설정
    top_n: int = 10


CONFIG = Config()