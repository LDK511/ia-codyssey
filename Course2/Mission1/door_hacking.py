import itertools
import os
import sys
import time
import zipfile
from multiprocessing import Pool, cpu_count


CHARSET = '0123456789abcdefghijklmnopqrstuvwxyz'
PASSWORD_LENGTH = 6
ZIP_FILE_NAME = 'emergency_storage_key.zip'
OUTPUT_FILE_NAME = 'password.txt'
PROGRESS_INTERVAL = 100000

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
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(password)
    except OSError as error:
        print(f'비밀번호 저장 중 오류가 발생했습니다: {error}')
        raise


def try_password(zip_file, member_name, password):
    password_bytes = password.encode('utf-8')
    try:
        zip_file.read(member_name, pwd=password_bytes)
        return True
    except (RuntimeError, zipfile.BadZipFile):
        return False


def unlock_zip(zip_path=ZIP_FILE_NAME, output_path=OUTPUT_FILE_NAME):
    start_time = time.time()
    start_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    repeat_count = 0

    print(f'암호 해제 시작 시간: {start_text}')
    print(f'대상 파일: {zip_path}')
    print('탐색 문자: 숫자 0-9, 소문자 a-z')
    print('탐색 길이: 6자리', flush=True)

    if not os.path.exists(zip_path):
        print('zip 파일을 찾을 수 없습니다.')
        return None

    try:
        with zipfile.ZipFile(zip_path) as zip_file:
            member_name = get_first_file_name(zip_file)

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


def check_prefix(prefix):
    suffix_length = PASSWORD_LENGTH - len(prefix)
    repeat_count = 0

    for suffix in itertools.product(CHARSET, repeat=suffix_length):
        password = prefix + ''.join(suffix)
        repeat_count += 1

        if try_password(_worker_zip_file, _worker_member_name, password):
            return password, repeat_count

    return None, repeat_count


def unlock_zip_fast(zip_path=ZIP_FILE_NAME, output_path=OUTPUT_FILE_NAME):
    start_time = time.time()
    start_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    repeat_count = 0
    last_logged = 0
    prefix_length = 3
    worker_count = max(cpu_count() - 1, 1)

    print(f'빠른 암호 해제 시작 시간: {start_text}')
    print(f'대상 파일: {zip_path}')
    print(f'사용 프로세스 수: {worker_count}')
    print('탐색 문자: 숫자 0-9, 소문자 a-z')
    print('탐색 길이: 6자리', flush=True)

    if not os.path.exists(zip_path):
        print('zip 파일을 찾을 수 없습니다.')
        return None

    try:
        with zipfile.ZipFile(zip_path) as zip_file:
            member_name = get_first_file_name(zip_file)

        prefixes = (
            ''.join(prefix)
            for prefix in itertools.product(CHARSET, repeat=prefix_length)
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


if __name__ == '__main__':
    unlock_zip()
    # 보너스 병렬 탐색을 실행하려면 위 줄 대신 아래 줄을 사용한다.
    # unlock_zip_fast()
