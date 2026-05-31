# Mission 5 — 내일 날씨는 맑음

화성 기상 CSV 데이터를 MySQL `mars_weather` 테이블에 적재한다.

## 파일 구성
- `schema.sql` — `mars_db` 데이터베이스와 `mars_weather` 테이블 생성 스크립트
- `config.example.py` — MySQL 접속 정보 템플릿 (실제 사용 시 `config.py` 로 복사)
- `mars_weather_summary.py` — CSV 읽기 + MySQL 연결 + INSERT 본 코드
- `mars_weathers_data.csv` — 입력 데이터(1000행)
- `.gitignore` — 실제 `config.py`(비밀번호 포함) 가 커밋되지 않도록 제외

## 사전 준비

### 1) MySQL 설치 (Windows)
1. https://dev.mysql.com/downloads/installer/ 에서 MySQL Installer 다운로드.
2. 설치 시 *MySQL Server*, *MySQL Workbench* 모두 선택.
3. root 비밀번호를 기억해둘 것.
4. 설치 후 MySQL 서비스가 실행 중인지 확인: `services.msc` → `MySQL80` Running.

### 2) Python 라이브러리 설치
```bash
pip install pymysql
```
> 과제 제약상 일반 라이브러리는 사용하지 않지만, MySQL 드라이버는 예외로 허용됨.

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
2050-01-02              24.67     53
...
2) MySQL 에 접속 중...
3) 기존 데이터를 비우는 중...
4) INSERT 반복 실행 중...
   1000 행을 적재했습니다.
5) 적재 결과 확인...
   COUNT=1000, FIRST=2050-01-01 00:00:00, LAST=2052-09-26 00:00:00
완료.
```

## 데이터 / 스펙 노트
- CSV 헤더가 `stom` 으로 되어 있지만 스펙상 `storm` 이므로 코드에서 자동 매핑한다.
- 스펙에는 `temp INT` 로 명시돼 있으나 실제 데이터는 소수점을 포함하므로 `FLOAT` 로 변경했다.
- `weather_id` 는 `AUTO_INCREMENT` 가 부여하므로 INSERT 시 직접 입력하지 않는다.

## 보너스
`MySQLHelper` 클래스를 정의하여 with 문, 트랜잭션, 쿼리 실행을 일괄 처리한다.
