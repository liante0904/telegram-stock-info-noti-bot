import asyncio
import subprocess
async def send_error_message(message):
    try:
        # 비동기적으로 쉘 스크립트 실행
        process = await asyncio.create_subprocess_shell(
            f'bash /home/ubuntu/sh/sendmsg.sh "{message}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # stdout과 stderr 읽기
        stdout, stderr = await process.communicate()

        if stdout:
            print(f"Output: {stdout.decode().strip()}")
        if stderr:
            print(f"Error: {stderr.decode().strip()}")

    except Exception as e:
        print(f"Error occurred while sending message: {e}")

def send_message_to_shell(result_message):
    """
    쉘 스크립트로 메시지를 전송하는 함수
    :param result_message: 쉘로 보낼 메시지 내용
    """
    try:
        subprocess.run(['/home/ubuntu/sh/sendmsg.sh', result_message], check=True)
        print(f"메시지가 쉘 스크립트로 전송되었습니다: {result_message}")
    except subprocess.CalledProcessError as e:
        print(f"쉘 스크립트 실행 중 오류 발생: {e}")


async def main():
    try:
        # 에러를 발생시킬 코드 예시
        raise ValueError("This is a test error")
    except Exception as e:
        # 에러 발생 시 메시지 전송
        await send_error_message(str(e))

if __name__ == "__main__":
    asyncio.run(main())
