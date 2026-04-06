import random  # 랜덤값 생성에 사용
import datetime  # 날짜시간 기록에 사용
import time  # 5초 반복에 사용
import json  # env_values JSON 형태 출력에 사용
import threading  # 보너스: 키 입력 감지를 위한 스레드


class DummySensor:  # 요구사항: DummySensor 클래스 생성
    def __init__(self):
        self.env_values = {  # 요구사항: env_values 사전 객체 멤버 추가
            'mars_base_internal_temperature': 0,  # 요구사항: 화성 기지 내부 온도
            'mars_base_external_temperature': 0,  # 요구사항: 화성 기지 외부 온도
            'mars_base_internal_humidity': 0,     # 요구사항: 화성 기지 내부 습도
            'mars_base_external_illuminance': 0,  # 요구사항: 화성 기지 외부 광량
            'mars_base_internal_co2': 0,          # 요구사항: 화성 기지 내부 이산화탄소 농도
            'mars_base_internal_oxygen': 0        # 요구사항: 화성 기지 내부 산소 농도
        }

    def set_env(self):  # 요구사항: set_env() 메소드 - 랜덤값 생성해서 env_values에 채워넣기
        self.env_values['mars_base_internal_temperature'] = round(random.uniform(18, 30), 2)   # 요구사항: 내부 온도 18~30도
        self.env_values['mars_base_external_temperature'] = round(random.uniform(0, 21), 2)    # 요구사항: 외부 온도 0~21도
        self.env_values['mars_base_internal_humidity'] = round(random.uniform(50, 60), 2)      # 요구사항: 내부 습도 50~60%
        self.env_values['mars_base_external_illuminance'] = round(random.uniform(500, 715), 2) # 요구사항: 외부 광량 500~715 W/m2
        self.env_values['mars_base_internal_co2'] = round(random.uniform(0.02, 0.1), 4)        # 요구사항: 내부 CO2 0.02~0.1%
        self.env_values['mars_base_internal_oxygen'] = round(random.uniform(4, 7), 2)          # 요구사항: 내부 산소 4~7%

    def get_env(self):  # 요구사항: get_env() 메소드 - env_values 반환
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 현재 날짜시간 기록
        log_line = (  # 날짜시간 + 6개 항목 한 줄로 구성
            now + ',' +
            str(self.env_values['mars_base_internal_temperature']) + ',' +
            str(self.env_values['mars_base_external_temperature']) + ',' +
            str(self.env_values['mars_base_internal_humidity']) + ',' +
            str(self.env_values['mars_base_external_illuminance']) + ',' +
            str(self.env_values['mars_base_internal_co2']) + ',' +
            str(self.env_values['mars_base_internal_oxygen'])
        )

        try:
            with open('sensor_log.csv', 'a', encoding='utf-8') as f:  # sensor_log.csv에 로그 저장
                f.write(log_line + '\n')
        except Exception as e:
            print('Error: 로그 저장 중 오류가 발생했습니다. ' + str(e))

        return self.env_values  # 요구사항: env_values 반환


class MissionComputer:  # 요구사항: MissionComputer 클래스 생성
    def __init__(self):
        self.env_values = {  # 요구사항: env_values 사전 객체 속성 추가
            'mars_base_internal_temperature': 0,  # 요구사항: 화성 기지 내부 온도
            'mars_base_external_temperature': 0,  # 요구사항: 화성 기지 외부 온도
            'mars_base_internal_humidity': 0,     # 요구사항: 화성 기지 내부 습도
            'mars_base_external_illuminance': 0,  # 요구사항: 화성 기지 외부 광량
            'mars_base_internal_co2': 0,          # 요구사항: 화성 기지 내부 이산화탄소 농도
            'mars_base_internal_oxygen': 0        # 요구사항: 화성 기지 내부 산소 농도
        }
        self.running = True  # 보너스: 반복 제어 플래그
        self.history = []    # 보너스: 5분 평균 계산을 위한 데이터 누적 리스트

    def get_sensor_data(self):  # 요구사항: get_sensor_data() 메소드 추가
        start_time = time.time()  # 보너스: 5분 평균 계산 시작 시간

        while self.running:  # 요구사항: 5초마다 반복
            ds.set_env()  # DummySensor에서 랜덤값 생성
            sensor_data = ds.get_env()  # DummySensor에서 센서값 가져오기

            self.env_values['mars_base_internal_temperature'] = sensor_data['mars_base_internal_temperature']
            self.env_values['mars_base_external_temperature'] = sensor_data['mars_base_external_temperature']
            self.env_values['mars_base_internal_humidity'] = sensor_data['mars_base_internal_humidity']
            self.env_values['mars_base_external_illuminance'] = sensor_data['mars_base_external_illuminance']
            self.env_values['mars_base_internal_co2'] = sensor_data['mars_base_internal_co2']
            self.env_values['mars_base_internal_oxygen'] = sensor_data['mars_base_internal_oxygen']

            # 요구사항: env_values를 JSON 형태로 출력
            print(json.dumps(self.env_values, indent=4))

            # 보너스: 5분 평균 계산을 위한 데이터 누적
            self.history.append(dict(self.env_values))

            # 보너스: 5분(300초)마다 평균값 출력
            elapsed = time.time() - start_time
            if elapsed >= 300:
                self.print_average()
                self.history = []
                start_time = time.time()

            time.sleep(5)  # 요구사항: 5초에 한 번씩 반복

        print('System stoped....')  # 보너스: 반복 멈추면 출력

    def print_average(self):  # 보너스: 5분 평균값 출력 메소드
        if not self.history:
            return
        keys = self.env_values.keys()
        averages = {}
        for key in keys:
            averages[key] = round(sum(d[key] for d in self.history) / len(self.history), 4)
        print('=== 5분 평균값 ===')
        print(json.dumps(averages, indent=4))

    def stop(self):  # 보너스: 반복 중지 메소드
        self.running = False


def wait_for_stop(computer):  # 보너스: 키 입력 감지 함수
    input()  # 엔터 키 입력 대기
    computer.stop()


if __name__ == '__main__':
    ds = DummySensor()  # 요구사항: DummySensor를 ds로 인스턴스화
    RunComputer = MissionComputer()  # 요구사항: MissionComputer를 RunComputer로 인스턴스화

    # 보너스: 키 입력 감지 스레드 시작
    stop_thread = threading.Thread(target=wait_for_stop, args=(RunComputer,))
    stop_thread.daemon = True
    stop_thread.start()

    RunComputer.get_sensor_data()  # 요구사항: get_sensor_data() 호출