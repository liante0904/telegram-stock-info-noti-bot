import os
import time
import google.generativeai as genai
from datetime import datetime
from loguru import logger

class GeminiManager:
    def __init__(self, api_key=None, model_name="models/gemini-2.5-flash-lite"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
        
        genai.configure(api_key=self.api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name=self.model_name)

    def upload_to_gemini(self, path, mime_type=None):
        """Gemini에 파일을 업로드합니다."""
        file = genai.upload_file(path, mime_type=mime_type)
        logger.info(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file

    def wait_for_files_active(self, files):
        """업로드된 파일들이 처리될 때까지 대기합니다."""
        logger.info("Waiting for file processing...")
        for name in (f.name for f in files):
            file = genai.get_file(name)
            while file.state.name == "PROCESSING":
                # logger.debug("Processing...")
                time.sleep(2)
                file = genai.get_file(name)
            if file.state.name != "ACTIVE":
                raise Exception(f"File {file.name} failed to process")
        logger.success("All files are active.")

    async def summarize_pdf(self, pdf_path, prompt=None):
        """PDF 파일을 요약합니다."""
        if not prompt:
            prompt = """당신은 금융 전문가입니다. 제공된 증권사 레포트(PDF)를 분석하여 다음 형식으로 요약해 주세요:
1. 핵심 요약 (3줄 이내)
2. 주요 포인트 (불렛 포인트)
3. 투자의견 및 목표주가 (있는 경우)
한국어로 답변해 주세요."""

        try:
            # 파일 업로드
            uploaded_file = self.upload_to_gemini(pdf_path, mime_type="application/pdf")
            
            # 처리 대기
            self.wait_for_files_active([uploaded_file])

            # 요약 생성
            logger.debug(f"Generating summary using {self.model_name}...")
            response = self.model.generate_content([uploaded_file, prompt])
            
            # 업로드된 파일 삭제 (공간 절약)
            genai.delete_file(uploaded_file.name)
            logger.debug(f"Deleted temporary file: {uploaded_file.name}")
            
            return {
                "summary": response.text,
                "model": self.model_name,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error during Gemini summarization: {e}")
            return {
                "summary": None,
                "model": self.model_name,
                "status": "error",
                "error": str(e)
            }
