import asyncio
import os
import signal
import threading

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from app.app import app as charts_app
from app.app import periodic_save, save_data
from app.logger import setup_logger

# 환경변수 로드
load_dotenv()

# 로깅 설정
logger = setup_logger(__name__)

# FastAPI 앱 초기화
mcp_host = os.environ.get("MCP_HOST", "0.0.0.0")
mcp_port = int(os.environ.get("MCP_PORT", 8007))
server_host = os.environ.get("FASTAPI_HOST", "127.0.0.1")
server_port = int(os.environ.get("FASTAPI_PORT", 8107))

# 종료 요청 플래그
is_shutting_down = False

# 스레드 저장
fastapi_thread = None
mcp_thread = None

# FastAPI 앱 초기화
app = FastAPI()
app.mount("/", charts_app)  # FastAPI 앱을 루트 경로에 마운트


# MCP 서버 초기화 함수
def create_mcp_server():
    """
    Create and return a FastMCP server instance.
    :return: FastMCP server instance.
    """
    mcp = FastMCP(
        "Portfolio Management",
        "0.1.0",
        host=mcp_host,  # Host address (0.0.0.0 allows connections from any IP)
        port=mcp_port,  # Port number for the server
    )

    @mcp.tool()
    async def generate_chart(code: str) -> str:
        """
        Generate a chart image from the provided code.
        :param code: Python code to generate the chart.
        :return: URL of the generated chart image.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{server_host}:{server_port}/generate_chart",
                    json={"code": code},
                    headers={"Content-Type": "application/json"},
                )
                return response.json()
        except Exception as e:
            return {"error": str(e)}

    return mcp


# FastAPI 서버 실행 함수
def run_fastapi():
    config = uvicorn.Config(
        "main:app",
        host=server_host,
        port=server_port,
    )
    server = uvicorn.Server(config)

    try:
        server.run()
    except Exception as e:
        logger.error(f"FastAPI 서버 실행 중 오류 발생: {e}")


# MCP 서버 실행 함수
def run_mcp(mcp_server):
    # 비동기 이벤트 루프 생성
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 주기적 데이터 저장 작업 추가
    save_task = loop.create_task(periodic_save())

    try:
        # MCP 서버 실행
        logger.info(f"FastMCP 서버가 {mcp_host}:{mcp_port}에서 실행 중입니다.")
        loop.run_until_complete(mcp_server.run(transport="sse"))
    except asyncio.CancelledError:
        logger.info("MCP 서버 작업이 취소되었습니다.")
    except Exception as e:
        logger.error(f"MCP 서버 실행 중 오류 발생: {e}")
    finally:
        # 남은 작업들을 정리
        save_task.cancel()

        # 이벤트 루프의 남은 작업 완료를 기다림
        pending = asyncio.all_tasks(loop)
        if pending:
            logger.info(f"남은 {len(pending)}개 작업 정리 중...")
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        # 이벤트 루프 종료
        loop.close()


# SIGINT(Ctrl+C) 및 SIGTERM 시그널 핸들러
def signal_handler(sig, frame):
    global is_shutting_down
    if is_shutting_down:
        logger.info("강제 종료 중...")
        os._exit(0)

    logger.info("종료 신호를 받았습니다. 서버를 안전하게 종료합니다...")
    is_shutting_down = True
    # 데이터 저장
    save_data()


# 메인 함수
async def main():
    global fastapi_thread, mcp_thread

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # MCP 서버 인스턴스 생성
    mcp_server = create_mcp_server()

    # FastAPI 서버 스레드 시작
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()

    logger.info(f"FastAPI 서버가 {server_host}:{server_port}에서 실행 중입니다.")

    # MCP 서버 스레드 시작
    mcp_thread = threading.Thread(target=run_mcp, args=(mcp_server,))
    mcp_thread.daemon = True
    mcp_thread.start()

    logger.info("두 서버가 모두 실행 중입니다. Ctrl+C를 눌러 종료하세요.")

    try:
        # 메인 스레드가 종료되지 않도록 대기
        while not is_shutting_down:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("메인 루프가 취소되었습니다.")
        # 종료 시 데이터 저장
        save_data()

    logger.info("모든 서버가 종료되었습니다.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt로 프로그램이 종료되었습니다.")
    finally:
        # 최종 데이터 저장
        save_data()
