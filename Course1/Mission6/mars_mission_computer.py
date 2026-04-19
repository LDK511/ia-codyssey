import random  # 랜덤값 생성에 사용
import datetime  # 로그 저장 시 날짜시간 기록에 사용


class DummySensor:  # 요구사항: DummySensor 클래스 생성
    def __init__(self):
        self.env_values = {  # 요구사항: env_values 사전 객체 멤버 추가
            'mars_base_internal_temperature': 0,
            'mars_base_external_temperature': 0,
            'mars_base_internal_humidity': 0,
            'mars_base_external_illuminance': 0,
            'mars_base_internal_co2': 0,
            'mars_base_internal_oxygen': 0
        }

    def set_env(self):  # 요구사항: set_env() 메소드 - 랜덤값 생성해서 env_values에 채워넣기
        self.env_values['mars_base_internal_temperature'] = round(random.uniform(18, 30), 2)
        self.env_values['mars_base_external_temperature'] = round(random.uniform(0, 21), 2)
        self.env_values['mars_base_internal_humidity'] = round(random.uniform(50, 60), 2)
        self.env_values['mars_base_external_illuminance'] = round(random.uniform(500, 715), 2)
        self.env_values['mars_base_internal_co2'] = round(random.uniform(0.02, 0.1), 4)
        self.env_values['mars_base_internal_oxygen'] = round(random.uniform(4, 7), 2)

    def get_env(self):  # 요구사항: get_env() 메소드 - env_values 반환
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 보너스: 현재 날짜시간 기록
        log_line = (  # 보너스: 날짜시간 + 6개 항목 한 줄로 구성
            now + ',' +
            str(self.env_values['mars_base_internal_temperature']) + ',' +
            str(self.env_values['mars_base_external_temperature']) + ',' +
            str(self.env_values['mars_base_internal_humidity']) + ',' +
            str(self.env_values['mars_base_external_illuminance']) + ',' +
            str(self.env_values['mars_base_internal_co2']) + ',' +
            str(self.env_values['mars_base_internal_oxygen'])
        )

        try:
            with open('sensor_log.csv', 'a', encoding='utf-8') as f:  # 보너스: sensor_log.csv에 로그 저장
                f.write(log_line + '\n')
        except Exception as e:
            print('Error: 로그 저장 중 오류가 발생했습니다. ' + str(e))

        return self.env_values  # 요구사항: env_values 반환


if __name__ == '__main__':
    ds = DummySensor()  # 요구사항: ds 이름으로 인스턴스 생성
    ds.set_env()        # 요구사항: set_env() 호출
    print(ds.get_env())  # 요구사항: get_env() 호출해서 값 확인
