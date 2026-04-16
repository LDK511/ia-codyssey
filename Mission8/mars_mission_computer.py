import random
import datetime
import time
import json
import threading
import platform  # 운영체제, CPU 정보 가져오는 표준 라이브러리
import psutil    # CPU/메모리 실시간 사용량 가져오는 라이브러리


class DummySensor:
    def __init__(self):
        self.env_values = { # 요구사항 : env_values 사전 객체 멤버 추가, 초기값은 각 항목 범위의 중간값으로 설정
            'mars_base_internal_temperature': 24,
            'mars_base_external_temperature': 10,
            'mars_base_internal_humidity': 55,
            'mars_base_external_illuminance': 607,
            'mars_base_internal_co2': 0.06,
            'mars_base_internal_oxygen': 5.5
        }

    def set_env(self):
        self.env_values['mars_base_internal_temperature'] = round(random.uniform(18, 30), 2)
        self.env_values['mars_base_external_temperature'] = round(random.uniform(0, 21), 2)
        self.env_values['mars_base_internal_humidity'] = round(random.uniform(50, 60), 2)
        self.env_values['mars_base_external_illuminance'] = round(random.uniform(500, 715), 2)
        self.env_values['mars_base_internal_co2'] = round(random.uniform(0.02, 0.1), 4)
        self.env_values['mars_base_internal_oxygen'] = round(random.uniform(4, 7), 2)

    def get_env(self):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = (
            now + ',' +
            str(self.env_values['mars_base_internal_temperature']) + ',' +
            str(self.env_values['mars_base_external_temperature']) + ',' +
            str(self.env_values['mars_base_internal_humidity']) + ',' +
            str(self.env_values['mars_base_external_illuminance']) + ',' +
            str(self.env_values['mars_base_internal_co2']) + ',' +
            str(self.env_values['mars_base_internal_oxygen'])
        )

        try:
            with open('sensor_log.csv', 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except Exception as e:
            print('Error: 로그 저장 중 오류가 발생했습니다. ' + str(e))

        return self.env_values


class MissionComputer:
    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': 0,
            'mars_base_external_temperature': 0,
            'mars_base_internal_humidity': 0,
            'mars_base_external_illuminance': 0,
            'mars_base_internal_co2': 0,
            'mars_base_internal_oxygen': 0
        }
        self.running = True
        self.history = []

    def get_sensor_data(self):
        start_time = time.time()

        while self.running:
            ds.set_env()
            sensor_data = ds.get_env()

            self.env_values['mars_base_internal_temperature'] = sensor_data['mars_base_internal_temperature']
            self.env_values['mars_base_external_temperature'] = sensor_data['mars_base_external_temperature']
            self.env_values['mars_base_internal_humidity'] = sensor_data['mars_base_internal_humidity']
            self.env_values['mars_base_external_illuminance'] = sensor_data['mars_base_external_illuminance']
            self.env_values['mars_base_internal_co2'] = sensor_data['mars_base_internal_co2']
            self.env_values['mars_base_internal_oxygen'] = sensor_data['mars_base_internal_oxygen']

            print(json.dumps(self.env_values, indent=4))

            self.history.append(dict(self.env_values))

            elapsed = time.time() - start_time
            if elapsed >= 300:
                self.print_average()
                self.history = []
                start_time = time.time()

            time.sleep(5)

        print('System stoped....')

    def print_average(self):
        if not self.history:
            return
        keys = self.env_values.keys()
        averages = {}
        for key in keys:
            averages[key] = round(sum(d[key] for d in self.history) / len(self.history), 4)
        print('=== 5분 평균값 ===')
        print(json.dumps(averages, indent=4))

    def stop(self):
        self.running = False

    def get_mission_computer_info(self):
        # 요구사항: 시스템 정보를 가져오는 부분은 예외처리 필수
        try:
            # 보너스: setting.txt에서 출력할 항목 읽기
            selected_keys = self.load_settings()

            info = {
                'os': platform.system(),                  # 운영체제 이름
                'os_version': platform.version(),         # 운영체제 버전
                'cpu_type': platform.processor(),         # CPU 타입
                'cpu_cores': psutil.cpu_count(logical=False),  # CPU 물리 코어 수
                'memory_size': str(round(psutil.virtual_memory().total / (1024 ** 3), 2)) + ' GB'  # 메모리 크기 GB 단위
            }

            # 보너스: setting.txt에 항목이 있으면 해당 항목만 필터링해서 출력
            if selected_keys:
                info = {k: v for k, v in info.items() if k in selected_keys}

            print(json.dumps(info, indent=4))

        except Exception as e:
            print('Error: 시스템 정보를 가져오는 중 오류가 발생했습니다. ' + str(e))

    def get_mission_computer_load(self):
        # 요구사항: CPU/메모리 실시간 사용량 가져오기
        try:
            # 보너스: setting.txt에서 출력할 항목 읽기
            selected_keys = self.load_settings()

            load = {
                'cpu_usage': str(psutil.cpu_percent(interval=1)) + ' %',      # CPU 실시간 사용량
                'memory_usage': str(psutil.virtual_memory().percent) + ' %'   # 메모리 실시간 사용량
            }

            # 보너스: setting.txt에 항목이 있으면 해당 항목만 필터링해서 출력
            if selected_keys:
                load = {k: v for k, v in load.items() if k in selected_keys}

            print(json.dumps(load, indent=4))

        except Exception as e:
            print('Error: 시스템 부하 정보를 가져오는 중 오류가 발생했습니다. ' + str(e))

    def load_settings(self):
        # 보너스: setting.txt 파일에서 출력할 항목 목록 읽기
        # setting.txt가 없으면 None 반환해서 전체 항목 출력
        try:
            with open('setting.txt', 'r', encoding='utf-8') as f:
                keys = [line.strip() for line in f if line.strip()]
            return keys
        except FileNotFoundError:
            return None
        except Exception as e:
            print('Error: setting.txt 읽기 오류: ' + str(e))
            return None


def wait_for_stop(computer):
    input()
    computer.stop()


if __name__ == '__main__':
    ds = DummySensor()
    runComputer = MissionComputer()  # 요구사항: 문제7 RunComputer에서 runComputer로 변경

    runComputer.get_mission_computer_info()   # 시스템 정보 출력
    runComputer.get_mission_computer_load()   # 실시간 부하 출력

    stop_thread = threading.Thread(target=wait_for_stop, args=(runComputer,))
    stop_thread.daemon = True
    stop_thread.start()

    runComputer.get_sensor_data()
