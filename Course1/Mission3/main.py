import csv
import pickle


def read_csv(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            data = [row for row in reader]
        return header, data
    except FileNotFoundError:
        print('Error: ' + file_path + ' 파일을 찾을 수 없습니다.')
    except PermissionError:
        print('Error: 파일에 접근할 권한이 없습니다.')
    except Exception as e:
        print('Error: 파일 처리 중 오류가 발생했습니다. ' + str(e))
    return None, None


def print_csv(header, data):
    print('=== 전체 목록 출력 ===')
    print(', '.join(header))
    for row in data:
        print(', '.join(row))


def sort_by_flammability(data):
    try:
        sorted_data = sorted(data, key=lambda x: float(x[4]), reverse=True)
        return sorted_data
    except Exception as e:
        print('Error: 정렬 중 오류가 발생했습니다. ' + str(e))
    return data


def print_sorted_list(header, sorted_data):
    print('\n=== 인화성 높은 순 전체 목록 ===')
    print(', '.join(header))
    for row in sorted_data:
        print(', '.join(row))


def print_danger_list(header, sorted_data):
    print('\n=== 인화성 지수 0.7 이상 목록 ===')
    print(', '.join(header))
    for row in sorted_data:
        if float(row[4]) >= 0.7:
            print(', '.join(row))


def save_danger_csv(header, sorted_data, output_path):
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in sorted_data:
                if float(row[4]) >= 0.7:
                    writer.writerow(row)
        print('\n=== 위험 물질 CSV 저장 완료: ' + output_path + ' ===')
    except Exception as e:
        print('Error: CSV 저장 중 오류가 발생했습니다. ' + str(e))


def save_binary(header, sorted_data, output_path):
    try:
        with open(output_path, 'wb') as f:
            pickle.dump([header] + sorted_data, f)
        print('=== 이진 파일 저장 완료: ' + output_path + ' ===')
    except Exception as e:
        print('Error: 이진 파일 저장 중 오류가 발생했습니다. ' + str(e))


def load_binary(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        print('\n=== 이진 파일 읽기 결과 ===')
        for row in data:
            print(', '.join(row))
    except Exception as e:
        print('Error: 이진 파일 읽기 중 오류가 발생했습니다. ' + str(e))


def main():
    csv_file = 'Mars_Base_Inventory_List.csv'
    danger_csv = 'Mars_Base_Inventory_danger.csv'
    bin_file = 'Mars_Base_Inventory_List.bin'

    header, data = read_csv(csv_file)
    if data is None:
        return

    print_csv(header, data)

    sorted_data = sort_by_flammability(data)

    print_sorted_list(header, sorted_data)

    print_danger_list(header, sorted_data)

    save_danger_csv(header, sorted_data, danger_csv)

    save_binary(header, sorted_data, bin_file)

    load_binary(bin_file)


if __name__ == '__main__':
    main()