"""mars_weather_summary.py

화성 기상 데이터(CSV)를 MySQL 의 mars_weather 테이블에 적재한다.

수행 순서:
    1. schema.sql 을 MySQL Workbench 등에서 실행해 DB 와 테이블을 만든다.
    2. config.py 에 접속 정보를 입력한다.
    3. python mars_weather_summary.py 로 실행한다.

요구사항:
    - Python 3.x
    - PyMySQL (pip install pymysql)
"""

import csv
import os
from datetime import datetime

import pymysql

import config


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


def read_weather_csv(csv_path):
    """CSV 파일을 읽어 (mars_date, temp, storm) 튜플 리스트로 반환한다.

    CSV 헤더는 weather_id, mars_date, temp, stom 으로 되어 있다.
    weather_id 는 DB 의 AUTO_INCREMENT 가 부여하므로 입력하지 않는다.
    'stom' 컬럼은 'storm' 오타로 간주하여 storm 으로 매핑한다.
    """
    rows = []
    with open(csv_path, mode='r', encoding='utf-8', newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for raw in reader:
            mars_date = datetime.strptime(raw['mars_date'], '%Y-%m-%d')
            temp_raw = raw.get('temp', '').strip()
            temp = float(temp_raw) if temp_raw else None
            storm_raw = (raw.get('storm') or raw.get('stom') or '').strip()
            storm = int(storm_raw) if storm_raw else None
            rows.append((mars_date, temp, storm))
    return rows


def preview_rows(rows, count=5):
    """읽어들인 데이터의 일부를 화면에 출력한다."""
    print(f'총 {len(rows)} 행을 읽었습니다.')
    print('--- 미리보기 ---')
    print(f'{"mars_date":<20} {"temp":>8} {"storm":>6}')
    for row in rows[:count]:
        mars_date, temp, storm = row
        date_str = mars_date.strftime('%Y-%m-%d')
        temp_str = f'{temp:.2f}' if temp is not None else 'NULL'
        storm_str = str(storm) if storm is not None else 'NULL'
        print(f'{date_str:<20} {temp_str:>8} {storm_str:>6}')
    print('----------------')


def truncate_table(helper):
    """기존 데이터를 비우고 AUTO_INCREMENT 를 초기화한다."""
    helper.execute('TRUNCATE TABLE mars_weather')


def insert_weather_rows(helper, rows):
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


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, 'mars_weathers_data.csv')

    print('1) CSV 파일을 읽는 중...')
    rows = read_weather_csv(csv_path)
    preview_rows(rows)

    print('2) MySQL 에 접속 중...')
    with MySQLHelper(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE,
        port=config.MYSQL_PORT,
    ) as helper:
        print('3) 기존 데이터를 비우는 중...')
        truncate_table(helper)

        print('4) INSERT 반복 실행 중...')
        inserted = insert_weather_rows(helper, rows)
        print(f'   {inserted} 행을 적재했습니다.')

        print('5) 적재 결과 확인...')
        result = helper.fetch_all(
            'SELECT COUNT(*) AS cnt, MIN(mars_date) AS first_day, '
            'MAX(mars_date) AS last_day FROM mars_weather'
        )
        row = result[0]
        print(
            f'   COUNT={row[0]}, '
            f'FIRST={row[1]}, '
            f'LAST={row[2]}'
        )

    print('완료.')


if __name__ == '__main__':
    main()
