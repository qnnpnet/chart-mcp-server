import json
import os

from app.logger import setup_logger

logger = setup_logger(__name__)


class SharedData:
    def __init__(self):
        # 데이터 저장 경로 설정
        self.data_dir = "data"
        self.data_file = os.path.join(self.data_dir, "chart_data.json")

        # 디렉토리 생성
        os.makedirs(self.data_dir, exist_ok=True)

    # 데이터 로드 함수
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    logger.info(f"데이터 파일을 로드합니다: {self.data_file}")
                    return json.load(f)
            except json.JSONDecodeError:
                # 파일이 손상된 경우 기본값 반환
                logger.error(f"데이터 파일이 손상되었습니다. 기본값을 사용합니다.")

        # 기본 데이터 구조
        return {"status": "running", "api_requests": 0, "generated_charts": []}

    # 데이터 저장 함수
    def save_data(self, shared_data):
        try:
            with open(self.data_file, "w") as f:
                logger.info(f"데이터 파일을 저장합니다: {self.data_file}")
                json.dump(shared_data, f, indent=2)
        except Exception as e:
            logger.error(f"데이터 저장 중 오류가 발생했습니다: {e}")
