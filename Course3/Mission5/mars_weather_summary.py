"""mars_weather_summary.py

화성 기상 데이터(CSV)를 MySQL 의 mars_weather 테이블에 적재하고,
요약 통계와 추이 그래프(PNG)를 생성한다.

수행 순서:
    1. schema.sql 을 MySQL Workbench 등에서 실행해 DB 와 테이블을 만든다.
    2. config.example.py 를 config.py 로 복사 후 접속 정보를 입력한다.
    3. pip install -r requirements.txt
    4. python mars_weather_summary.py

요구사항:
    - Python 3.x
    - PyMySQL (MySQL 접속용 외부 라이브러리)
    - matplotlib (PNG 차트 생성용 시각화 라이브러리)
"""

import csv
import os
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use('Agg')

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pymysql  # noqa: E402

import config  # noqa: E402


STORM_DANGER_THRESHOLD = 80

WeatherRow = Tuple[datetime, Optional[float], Optional[int]]


class MySQLHelper:
    """MySQL 접속 및 쿼리 실행을 도와주는 헬퍼 클래스(보너스 과제).

    with 문과 함께 사용하면 정상 종료 시 commit, 예외 발생 시 rollback 한다.
    """

    def __init__(self, host, user, password, database, port=3306):
        self._host = host
        self._user = user
        self._password = password
        self._database = database
        self._port = port
        self._connection = None

    def connect(self):
        """MySQL 서버에 접속한다."""
        self._connection = pymysql.connect(
            host=self._host,
            user=self._user,
            password=self._password,
            database=self._database,
            port=self._port,
            charset='utf8mb4',
            autocommit=False,
        )

    def close(self):
        """접속을 종료한다."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def execute(self, query, params=None):
        """단일 쿼리를 실행한다."""
        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())

    def fetch_all(self, query, params=None):
        """SELECT 결과 전체를 가져온다."""
        with self._connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def commit(self):
        """현재 트랜잭션을 커밋한다."""
        if self._connection is not None:
            self._connection.commit()

    def rollback(self):
        """현재 트랜잭션을 롤백한다."""
        if self._connection is not None:
            self._connection.rollback()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


def read_weather_csv(csv_path: str) -> List[WeatherRow]:
    """CSV 파일을 읽어 (mars_date, temp, storm) 튜플 리스트로 반환한다.

    CSV 헤더는 weather_id, mars_date, temp, stom 으로 되어 있다.
    weather_id 는 DB 의 AUTO_INCREMENT 가 부여하므로 입력하지 않는다.
    'stom' 컬럼은 'storm' 오타로 간주하여 storm 으로 매핑한다.
    """
    rows: List[WeatherRow] = []
    with open(csv_path, mode='r', encoding='utf-8', newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for raw in reader:
            mars_date = datetime.strptime(raw['mars_date'], '%Y-%m-%d')
            temp_raw = (raw.get('temp') or '').strip()
            temp = float(temp_raw) if temp_raw else None
            storm_raw = (raw.get('storm') or raw.get('stom') or '').strip()
            storm = int(storm_raw) if storm_raw else None
            rows.append((mars_date, temp, storm))
    return rows


def preview_rows(rows: Sequence[WeatherRow], count: int = 5) -> None:
    """읽어들인 데이터의 일부를 화면에 출력한다."""
    print(f'총 {len(rows)} 행을 읽었습니다.')
    print('--- 미리보기 ---')
    header = '{:<20} {:>8} {:>6}'.format('mars_date', 'temp', 'storm')
    print(header)
    for row in rows[:count]:
        mars_date, temp, storm = row
        date_str = mars_date.strftime('%Y-%m-%d')
        temp_str = f'{temp:.2f}' if temp is not None else 'NULL'
        storm_str = str(storm) if storm is not None else 'NULL'
        print(f'{date_str:<20} {temp_str:>8} {storm_str:>6}')
    print('----------------')


def summarize_rows(rows: Sequence[WeatherRow]) -> None:
    """전체 데이터의 요약 통계를 콘솔에 출력한다."""
    if not rows:
        print('데이터가 비어있습니다.')
        return

    temps = [r[1] for r in rows if r[1] is not None]
    storms = [r[2] for r in rows if r[2] is not None]
    first_day = min(r[0] for r in rows)
    last_day = max(r[0] for r in rows)

    print('--- 요약 통계 ---')
    print(f'기간      : {first_day.date()} ~ {last_day.date()}')
    print(f'총 행수   : {len(rows)}')
    if temps:
        print(f'평균 기온 : {sum(temps) / len(temps):.2f}')
        print(f'최저 기온 : {min(temps):.2f}')
        print(f'최고 기온 : {max(temps):.2f}')
    if storms:
        avg_storm = sum(storms) / len(storms)
        danger_count = sum(
            1 for s in storms if s >= STORM_DANGER_THRESHOLD
        )
        print(f'평균 폭풍 : {avg_storm:.2f}')
        print(f'최고 폭풍 : {max(storms)}')
        msg = (
            f'폭풍 위험일(storm>={STORM_DANGER_THRESHOLD}) : '
            f'{danger_count} 일'
        )
        print(msg)
    print('-----------------')


def save_weather_chart(rows: Sequence[WeatherRow], output_path: str) -> None:
    """기온/폭풍 추이를 두 패널 차트로 그려 PNG 로 저장한다."""
    dates = [r[0] for r in rows]
    temps = [r[1] for r in rows]
    storms = [r[2] for r in rows]

    fig, (ax_temp, ax_storm) = plt.subplots(
        2, 1, figsize=(12, 6), sharex=True
    )

    ax_temp.plot(dates, temps, color='tab:red', linewidth=0.8)
    ax_temp.set_ylabel('Temperature')
    ax_temp.set_title('Mars Weather Summary')
    ax_temp.grid(True, alpha=0.3)

    ax_storm.bar(dates, storms, color='tab:blue', width=1.0)
    ax_storm.axhline(
        STORM_DANGER_THRESHOLD,
        color='red',
        linestyle='--',
        linewidth=0.8,
        label=f'Storm danger ({STORM_DANGER_THRESHOLD})',
    )
    ax_storm.set_ylabel('Storm intensity')
    ax_storm.set_xlabel('Date')
    ax_storm.legend(loc='upper right')
    ax_storm.grid(True, alpha=0.3)

    ax_storm.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax_storm.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(output_path, dpi=120)
    plt.close(fig)
    print(f'차트 저장 완료 : {output_path}')


def truncate_table(helper: MySQLHelper) -> None:
    """기존 데이터를 비우고 AUTO_INCREMENT 를 초기화한다."""
    helper.execute('TRUNCATE TABLE mars_weather')


def insert_weather_rows(
    helper: MySQLHelper, rows: Sequence[WeatherRow]
) -> int:
    """rows 를 mars_weather 테이블에 한 행씩 반복 INSERT 한다."""
    insert_query = (
        'INSERT INTO mars_weather (mars_date, temp, storm) '
        'VALUES (%s, %s, %s)'
    )
    inserted = 0
    for row in rows:
        helper.execute(insert_query, row)
        inserted += 1
    return inserted


def find_storm_days(
    helper: MySQLHelper, threshold: int = STORM_DANGER_THRESHOLD
) -> List[Tuple[datetime, int]]:
    """폭풍 지수가 threshold 이상인 날을 DB 에서 조회한다."""
    query = (
        'SELECT mars_date, storm FROM mars_weather '
        'WHERE storm >= %s ORDER BY mars_date'
    )
    return list(helper.fetch_all(query, (threshold,)))


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, 'mars_weathers_data.csv')
    chart_path = os.path.join(base_dir, 'mars_weather_summary.png')

    print('1) CSV 파일을 읽는 중...')
    rows = read_weather_csv(csv_path)
    preview_rows(rows)
    summarize_rows(rows)

    print('2) 차트 PNG 생성 중...')
    save_weather_chart(rows, chart_path)

    print('3) MySQL 에 접속 중...')
    with MySQLHelper(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE,
        port=config.MYSQL_PORT,
    ) as helper:
        print('4) 기존 데이터를 비우는 중...')
        truncate_table(helper)

        print('5) INSERT 반복 실행 중...')
        inserted = insert_weather_rows(helper, rows)
        print(f'   {inserted} 행을 적재했습니다.')

        print('6) 적재 결과 확인...')
        summary = helper.fetch_all(
            'SELECT COUNT(*), MIN(mars_date), MAX(mars_date) '
            'FROM mars_weather'
        )
        cnt, first_day, last_day = summary[0]
        print(f'   COUNT={cnt}, FIRST={first_day}, LAST={last_day}')

        print('7) 폭풍 위험일 조회...')
        storm_days = find_storm_days(helper)
        print(
            f'   storm >= {STORM_DANGER_THRESHOLD} 인 날 : '
            f'{len(storm_days)} 일'
        )
        for mars_date, storm in storm_days[:5]:
            print(f'   - {mars_date.date()} (storm={storm})')
        if len(storm_days) > 5:
            print(f'   ... 외 {len(storm_days) - 5} 일')

    print('완료.')


if __name__ == '__main__':
    main()
