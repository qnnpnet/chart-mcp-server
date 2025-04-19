import asyncio
import os
import threading
from datetime import datetime

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.logger import setup_logger
from app.models import CodeRequest, CommandRequestModel
from app.shared_data import SharedData
from app.utils import generate_chart_image

logger = setup_logger(__name__)

load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
OUTPUT_DIR = "static/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


shared_data = SharedData()

# 데이터 로드
data = shared_data.load_data()

# 데이터 저장 락
data_lock = threading.Lock()


def save_data():
    with data_lock:
        shared_data.save_data(data)


# 주기적 데이터 저장 함수
async def periodic_save():
    try:
        while True:
            await asyncio.sleep(60)  # 60초마다 저장
            with data_lock:
                save_data()
                logger.info("데이터가 주기적으로 저장되었습니다.")
    except asyncio.CancelledError:
        logger.info("주기적 데이터 저장 작업이 취소되었습니다.")
    finally:
        # 마지막으로 한 번 더 저장
        with data_lock:
            save_data()


# FastAPI 라우트 정의
@app.get("/")
async def root():
    return {"message": "FastAPI와 FastMCP 서버 통합 시스템에 오신 것을 환영합니다!"}


@app.get("/status")
async def get_status():
    with data_lock:
        data["api_requests"] += 1
        shared_data.save_data(data)
        return data


@app.post("/generate_chart")
async def generate_chart(request: CodeRequest, background_tasks: BackgroundTasks):
    with data_lock:
        data["api_requests"] += 1

        try:
            filename = generate_chart_image(request.code, OUTPUT_DIR)
            url = f"{BASE_URL}/static/images/{filename}"
            logger.info(f"차트 이미지 생성 완료: {url}")
            data["generated_charts"].append(
                {
                    "id": len(data["generated_charts"]) + 1,
                    "code": request.code,
                    "url": url,
                    "created_at": datetime.now().isoformat(),
                }
            )
            logger.debug(f"차트 데이터 저장 완료: {data['generated_charts'][-1]}")

            # 데이터 저장
            shared_data.save_data(data)
            return {"image_url": url}
        except Exception as e:
            return HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    # 서버 종료 시 데이터 저장
    shared_data.save_data(data)
