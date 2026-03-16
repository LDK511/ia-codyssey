def print_hello():
    print('Hello Mars')


def read_log(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return lines
    except FileNotFoundError:
        print('Error: ' + file_path + ' 파일을 찾을 수 없습니다.')
    except PermissionError:
        print('Error: 파일에 접근할 권한이 없습니다.')
    except Exception as e:
        print('Error: 파일 처리 중 오류가 발생했습니다. ' + str(e))
    return None


def print_logs(lines):
    print('=== 전체 로그 출력 ===')
    for line in lines:
        print(line, end='')


def print_logs_reversed(lines):
    print('\n=== 시간 역순 로그 출력 ===')
    header = lines[0]
    data = lines[1:]
    reversed_data = data[::-1]
    print(header, end='')
    for line in reversed_data:
        print(line, end='')


def save_error_logs(lines, output_path):
    try:
        header = lines[0]
        error_lines = [
            line for line in lines[1:]
            if 'unstable' in line or 'explosion' in line or 'ERROR' in line or 'WARNING' in line
        ]
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(header)
            for line in error_lines:
                f.write(line)
        print('\n=== 문제 로그 저장 완료: ' + output_path + ' ===')
        for line in error_lines:
            print(line, end='')
    except Exception as e:
        print('Error: 문제 로그 저장 중 오류가 발생했습니다. ' + str(e))


def main():
    log_file = 'mission_computer_main.log'
    error_file = 'mission_computer_error.log'

    print_hello()

    lines = read_log(log_file)
    if lines is None:
        return

    print_logs(lines)
    print_logs_reversed(lines)
    save_error_logs(lines, error_file)


if __name__ == '__main__':
    main()
