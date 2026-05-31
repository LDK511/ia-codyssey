# Mission 5 — 내일 날씨는 맑음

화성 기상 CSV 데이터를 MySQL `mars_weather` 테이블에 적재한다.

## 파일 구성
- `schema.sql` — `mars_db` 데이터베이스와 `mars_weather` 테이블 생성 스크립트
- `config.example.py` — MySQL 접속 정보 템플릿 (실제 사용 시 `config.py` 로 복사)
- `mars_weather_summary.py` — CSV 읽기 + 통계 + PNG 차트 + MySQL INSERT + 폭풍 조회
- `mars_weathers_data.csv` — 입력 데이터(1000행)
- `requirements.txt` — 외부 라이브러리 목록 (`PyMySQL`, `matplotlib`)
- `.gitignore` — 실제 `config.py`(비밀번호 포함) 가 커밋되지 않도록 제외

## 사전 준비

### 1) MySQL 설치 (Windows)
1. https://dev.mysql.com/downloads/installer/ 에서 MySQL Installer 다운로드.
2. 설치 시 *MySQL Server*, *MySQL Workbench* 모두 선택.
3. root 비밀번호를 기억해둘 것.
4. 설치 후 MySQL 서비스가 실행 중인지 확인: `services.msc` → `MySQL80` Running.

### 2) Python 라이브러리 설치
```bash
pip install -r requirements.txt
```
포함 라이브러리:
- `PyMySQL` — MySQL 드라이버 (스펙상 MySQL 라이브러리 허용)
- `matplotlib` — PNG 차트 생성 (스펙 제약사항의 "결과는 png 이미지로 저장한다" 충족 + 학습 목표 "데이터 시각화")

### 3) 데이터베이스 / 테이블 생성
MySQL Workbench 에서 `schema.sql` 을 열고 실행한다. 또는 CLI:
```bash
mysql -u root -p < schema.sql
```

### 4) 접속 정보 입력
`config.example.py` 를 같은 폴더에 `config.py` 라는 이름으로 복사한 뒤,
`MYSQL_PASSWORD` 등을 실제 환경에 맞게 수정한다.

```bash
copy config.example.py config.py    # Windows
cp config.example.py config.py      # macOS / Linux
```

`config.py` 는 `.gitignore` 에 등록되어 있어 커밋되지 않는다.

## 실행
```bash
cd Course3/Mission5
python mars_weather_summary.py
```

### 예상 출력
```
1) CSV 파일을 읽는 중...
총 1000 행을 읽었습니다.
--- 미리보기 ---
mars_date                temp  storm
2050-01-01              21.40     56
...
--- 요약 통계 ---
기간      : 2050-01-01 ~ 2052-09-26
총 행수   : 1000
평균 기온 : 35.xx
폭풍 위험일(storm>=80) : NN 일
-----------------
2) 차트 PNG 생성 중...
차트 저장 완료 : .../mars_weather_summary.png
3) MySQL 에 접속 중...
...
6) 적재 결과 확인...
   COUNT=1000, FIRST=2050-01-01 00:00:00, LAST=2052-09-26 00:00:00
7) 폭풍 위험일 조회...
   storm >= 80 인 날 : NN 일
완료.
```

실행이 끝나면 같은 폴더에 `mars_weather_summary.png` 가 �