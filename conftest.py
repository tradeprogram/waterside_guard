"""pytest 실행 시 .env를 자동으로 로드한다 (자격증명 유무에 따라 skip되는 라이브 테스트가
GEE_PROJECT_ID 등을 인식하게 하기 위함). .env가 없어도 조용히 넘어간다."""
from dotenv import load_dotenv

load_dotenv()
