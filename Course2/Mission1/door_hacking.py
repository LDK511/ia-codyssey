import itertools
import os
import sys
import time
import zipfile
from multiprocessing import Pool, cpu_count


CHARSET = '0123456789abcdefghijklmnopqrstuvwxyz'
PASSWORD_LENGTH = 6
PREFIX_LENGTH = 3
ZIP_FILE_NAME = os.environ.get('ZIP_FILE', 'emergency_storage_key.zip')
OUTPUT_FILE_NAME = os.environ.get('OUTPUT_FILE', 'output/password.txt')
PROGRESS_INTERVAL = 100000

# 컨테이너 분산 탐색용 환경 변수
PARTITION_INDEX = int(os.environ.get('PARTITION_INDEX', '0'))
PARTITION_COUNT = int(os.environ.get('PARTITION_COUNT', '1'))

sys.stdout.reconfigure(line_buffering=True)

_worker_zip_file = None
_worker_member_name = None


def get_elapsed_time(start_time):
    elapsed_time = time.time() - start_time
    return round(elapsed_time, 2)


def get_first_file_name(zip_file):
    file_names = zip_file.namelist()
    if not file_names:
        raise ValueError('zip 파일 안에 확인할 파일이 없습니다.')
    return file_names[0]


def save_password(password, output_path):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(password)
    except OSError as error:
        print(f'비밀번호 저장 중 오류가 발생했습니다: {error}')
        raise


def load_cached_password(output_path):
    '''이전 실행에서 저장된 비밀번호를 읽는다.

    파일이 없거나, 형식(길이 6, 숫자/소문자 알파벳)이 맞지 않으면 None 반환.
    이 함수는 비밀번호의 정당성까지 보증하지 않으며, 실제 검증은
    호출자가 try_password로 수행해야 한다.
    '''
    try:
        with open(output_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
    except FileNotFoundError:
        return None
    except OSError as error:
        print(f'캐시 파일 읽기 오류: {error}')
        return None

    if len(content) != PASSWORD_LENGTH:
        return None
    if not all(c in CHARSET for c in content):
        return None
    return content


def is_password_found(output_path):
    '''다른 컨테이너가 이미 정답을 찾았는지 공유 볼륨에서 확인한다.'''
    try:
        with open(output_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            return len(content) == PASSWORD_LENGTH
    except (FileNotFoundError, OSError):
        return False


def try_password(zip_file, member_name, password):
    import zlib
    password_bytes = password.encode('utf-8')
    try:
        zip_file.read(member_name, pwd=password_bytes)
        return True
    except (RuntimeError, zipfile.BadZipFile, zlib.error):
        return False


def unlock_zip(zip_path=ZIP_FILE_NAME, output_path=OUTPUT_FILE_NAME):
    '''zip 파일의 6자리 비밀번호를 찾아 password.txt에 저장한다.

    이전 실행 결과(output_path)가 존재하면 zip에 적용해 먼저 검증한다.
    검증을 통과하면 전수 탐색을 생략한다(캐시 적중).
    그렇지 않으면 0-9, a-z 6자리 전체 공간을 사전식 순서로 탐색한다.
    '''
    start_time = time.time()
    start_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    repeat_count = 0

    print(f'암호 해제 시작 시간: {start_text}')
    print(f'대상 파일: {zip_path}')

    if not os.path.exists(zip_path):
        print('zip 파일을 찾을 수 없습니다.')
        return None

    try:
        with zipfile.ZipFile(zip_path) as zip_file:
            member_name = get_first_file_name(zip_file)

            # 1. 캐시(이전 실행 결과) 검증
            cached = load_cached_password(output_path)
            if cached is not None:
                repeat_count += 1
                if try_password(zip_file, member_name, cached):
                    elapsed_time = get_elapsed_time(start_time)
                    print('저장된 비밀번호 검증 성공 (전수 탐색 생략)')
                    print(f'비밀번호: {cached}')
                    print(f'반복 회수: {repeat_count}')
                    print(f'진행 시간: {elapsed_time}초')
                    print(f'저장 파일: {output_path}')
                    return cached
                print('저장된 비밀번호가 유효하지 않습니다. 전수 탐색을 시작합니다.')

            # 2. 전수 탐색 (cache miss 또는 cache invalid)
            print('탐색 문자: 숫자 0-9, 소문자 a-z')
            print('탐색 길이: 6자리', flush=True)

            for candidate in itertools.product(CHARSET, repeat=PASSWORD_LENGTH):
                password = ''.join(candidate)
                repeat_count += 1

                if try_password(zip_file, member_name, password):
                    elapsed_time = get_elapsed_time(start_time)
                    save_password(password, output_path)

                    print('암호 해제 성공')
                    print(f'비밀번호: {password}')
                    print(f'반복 회수: {repeat_count}')
                    print(f'진행 시간: {elapsed_time}초')
                    print(f'저장 파일: {output_path}')
                    return password

                if repeat_count % PROGRESS_INTERVAL == 0:
                    elapsed_time = get_elapsed_time(start_time)
                    print(
                        f'진행 중 | 반복 회수: {repeat_count} | '
                        f'현재 시도: {password} | 진행 시간: {elapsed_time}초'
                    )

    except FileNotFoundError:
        print('zip 파일을 찾을 수 없습니다.')
    except PermissionError:
        print('파일 접근 권한이 없습니다.')
    except zipfile.BadZipFile:
        print('올바른 zip 파일이 아닙니다.')
    except ValueError as error:
        print(error)

    elapsed_time = get_elapsed_time(start_time)
    print('암호를 찾지 못했습니다.')
    print(f'총 반복 회수: {repeat_count}')
    print(f'총 진행 시간: {elapsed_time}초')
    return None


def init_worker(zip_path, member_name):
    global _worker_zip_file
    global _worker_member_name

    _worker_zip_file = zipfile.ZipFile(zip_path)
    _worker_member_name = member_name


def check_prefix(args):
    prefix, output_path = args
    suffix_length = PASSWORD_LENGTH - len(prefix)
    repeat_count = 0

    for suffix in itertools.product(CHARSET, repeat=suffix_length):
        password = prefix + ''.join(suffix)
        repeat_count += 1

        if is_password_found(output_path):             # 다른 워커/컨테이너가 이미 찾음
            return None, repeat_count

        if try_password(_worker_zip_file, _worker_member_name, password):
            return password, repeat_count

    return None, repeat_count


def unlock_zip_fast(zip_path=ZIP_FILE_NAME, output_path=OUTPUT_FILE_NAME):
    '''보너스: 멀티프로세싱으로 키 공간을 prefix 단위로 나눠 병렬 탐색.

    캐시가 있으면 unlock_zip과 동일하게 먼저 검증한다.
    '''
    start_time = time.time()
    start_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    repeat_count = 0
    last_logged = 0
    worker_count = max(cpu_count() - 1, 1)

    print(f'빠른 암호 해제 시작 시간: {start_text}')
    print(f'대상 파일: {zip_path}')
    print(f'사용 프로세스 수: {worker_count}')

    if not os.path.exists(zip_path):
        print('zip 파일을 찾을 수 없습니다.')
        return None

    try:
        with zipfile.ZipFile(zip_path) as zip_file:
            member_name = get_first_file_name(zip_file)

            cached = load_cached_password(output_path)
            if cached is not None:
                repeat_count += 1
                if try_password(zip_file, member_name, cached):
                    elapsed_time = get_elapsed_time(start_time)
                    print('저장된 비밀번호 검증 성공 (전수 탐색 생략)')
                    print(f'비밀번호: {cached}')
                    print(f'반복 회수: {repeat_count}')
                    print(f'진행 시간: {elapsed_time}초')
                    print(f'저장 파일: {output_path}')
                    return cached
                print('저장된 비밀번호가 유효하지 않습니다. 병렬 탐색을 시작합니다.')

        print('탐색 문자: 숫자 0-9, 소문자 a-z')
        print('탐색 길이: 6자리', flush=True)

        prefixes = (
            (''.join(prefix), output_path)
            for prefix in itertools.product(CHARSET, repeat=PREFIX_LENGTH)
        )

        with Pool(
            processes=worker_count,
            initializer=init_worker,
            initargs=(zip_path, member_name)
        ) as pool:
            for password, count in pool.imap_unordered(check_prefix, prefixes):
                repeat_count += count

                if repeat_count - last_logged >= PROGRESS_INTERVAL:
                    elapsed_time = get_elapsed_time(start_time)
                    print(
                        f'진행 중 | 반복 회수: {repeat_count} | '
                        f'진행 시간: {elapsed_time}초'
                    )
                    last_logged = repeat_count

                if password is not None:
                    elapsed_time = get_elapsed_time(start_time)
                    save_password(password, output_path)
                    pool.terminate()

                    print('암호 해제 성공')
                    print(f'비밀번호: {password}')
                    print(f'반복 회수: {repeat_count}')
                    print(f'진행 시간: {elapsed_time}초')
                    print(f'저장 파일: {output_path}')
                    return password

    except FileNotFoundError:
        print('zip 파일을 찾을 수 없습니다.')
    except PermissionError:
        print('파일 접근 권한이 없습니다.')
    except zipfile.BadZipFile:
        print('올바른 zip 파일이 아닙니다.')
    except ValueError as error:
        print(error)

    elapsed_time = get_elapsed_time(start_time)
    print('암호를 찾지 못했습니다.')
    print(f'총 반복 회수: {repeat_count}')
    print(f'총 진행 시간: {elapsed_time}초')
    return None


def get_my_prefixes():
    '''전체 prefix 목록에서 이 컨테이너가 담당할 범위만 잘라서 반환.'''
    all_prefixes = [
        ''.join(p)
        for p in itertools.product(CHARSET, repeat=PREFIX_LENGTH)
    ]
    total = len(all_prefixes)                          # 36^3 = 46,656개
    chunk = total // PARTITION_COUNT
    start = PARTITION_INDEX * chunk
    end = start + chunk if PARTITION_INDEX < PARTITION_COUNT - 1 else total
    return all_prefixes[start:end]


def unlock_zip_distributed(zip_path=ZIP_FILE_NAME, output_path=OUTPUT_FILE_NAME):
    '''보너스: 컨테이너 여러 개로 키 공간을 나눠 분산 탐색.

    환경 변수 PARTITION_INDEX, PARTITION_COUNT 로 이 컨테이너의 담당 범위를 지정.
    공유 볼륨의 output_path 를 주기적으로 확인해 다른 컨테이너가 정답을 찾으면 중단.
    단일 컨테이너(PARTITION_COUNT=1)로 실행하면 unlock_zip_fast 와 동일하게 동작.
    '''
    start_time = time.time()
    start_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    repeat_count = 0
    last_logged = 0
    worker_count = max(cpu_count() - 1, 1)

    print(f'[컨테이너 {PARTITION_INDEX}/{PARTITION_COUNT - 1}] '
          f'분산 암호 해제 시작: {start_text}')
    print(f'대상 파일: {zip_path}')
    print(f'사용 프로세스 수: {worker_count}')

    if not os.path.exists(zip_path):
        print('zip 파일을 찾을 수 없습니다.')
        return None

    if is_password_found(output_path):
        print('다른 컨테이너가 이미 정답을 찾았습니다. 종료합니다.')
        return None

    try:
        with zipfile.ZipFile(zip_path) as zip_file:
            member_name = get_first_file_name(zip_file)

        my_prefixes = get_my_prefixes()
        print(f'담당 prefix: {my_prefixes[0]} ~ {my_prefixes[-1]} '
              f'({len(my_prefixes)}개)')

        prefixes = (
            (prefix, output_path)
            for prefix in my_prefixes
        )

        with Pool(
            processes=worker_count,
            initializer=init_worker,
            initargs=(zip_path, member_name)
        ) as pool:
            for password, count in pool.imap_unordered(check_prefix, prefixes):
                repeat_count += count

                if repeat_count - last_logged >= PROGRESS_INTERVAL:
                    elapsed_time = get_elapsed_time(start_time)
                    print(
                        f'[컨테이너 {PARTITION_INDEX}] 진행 중 | '
                        f'반복 회수: {repeat_count} | '
                        f'진행 시간: {elapsed_time}초'
                    )
                    last_logged = repeat_count

                if password is not None:
                    elapsed_time = get_elapsed_time(start_time)
                    save_password(password, output_path)
                    pool.terminate()

                    print(f'[컨테이너 {PARTITION_INDEX}] 암호 해제 성공!')
                    print(f'비밀번호: {password}')
                    print(f'반복 회수: {repeat_count}')
                    print(f'진행 시간: {elapsed_time}초')
                    print(f'저장 파일: {output_path}')
                    return password

                if is_password_found(output_path):
                    pool.terminate()
                    print(f'[컨테이너 {PARTITION_INDEX}] '
                          f'다른 컨테이너가 정답을 찾아 중단합니다.')
                    return None

    except FileNotFoundError:
        print('zip 파일을 찾을 수 없습니다.')
    except PermissionError:
        print('파일 접근 권한이 없습니다.')
    except zipfile.BadZipFile:
        print('올바른 zip 파일이 아닙니다.')
    except ValueError as error:
        print(error)

    elapsed_time = get_elapsed_time(start_time)
    print(f'[컨테이너 {PARTITION_INDEX}] 담당 구간 탐색 완료')
    print(f'총 반복 회수: {repeat_count}')
    print(f'총 진행 시간: {elapsed_time}초')
    return None


if __name__ == '__main__':
    if PARTITION_COUNT > 1:
        # 환경 변수로 PARTITION_COUNT가 설정된 경우 → 컨테이너 분산 탐색
        unlock_zip_distributed()
    else:
        # 기본 단일 탐색
        unlock_zip()
        # 단일 머신 병렬 탐색 (멀티프로세싱)
        # unlock_zip_fast()