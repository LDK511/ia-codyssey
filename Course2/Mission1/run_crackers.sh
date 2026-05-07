#!/bin/bash
# 사용법: ./run_crackers.sh [컨테이너 수]
# 권장:   ./run_crackers.sh 200  (최악 기준 약 1분)
# 최소:   ./run_crackers.sh 50   (평균 기준 약 1~2분)

PARTITION_COUNT=${1:-200}
IMAGE_NAME='zip-cracker'
OUTPUT_DIR=$(pwd)/output
OUTPUT_FILE="${OUTPUT_DIR}/password.txt"

echo "========================================"
echo " ZIP 분산 암호 해제"
echo " 컨테이너 수 : ${PARTITION_COUNT}개"
echo " 출력 경로   : ${OUTPUT_FILE}"
echo "========================================"

# 출력 폴더 생성
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_FILE"

# 이미지 빌드
echo ""
echo "[1/3] Docker 이미지 빌드 중..."
docker build -t "$IMAGE_NAME" . -q
echo "      완료"

# 기존 잔여 컨테이너 정리
echo "[2/3] 기존 컨테이너 정리 중..."
docker ps -a --filter "name=cracker_" --format "{{.Names}}" | \
    xargs -r docker rm -f > /dev/null 2>&1
echo "      완료"

# 컨테이너 실행
echo "[3/3] 컨테이너 ${PARTITION_COUNT}개 실행 중..."
for i in $(seq 0 $((PARTITION_COUNT - 1))); do
    docker run -d \
        --name "cracker_${i}" \
        -e PARTITION_INDEX="$i" \
        -e PARTITION_COUNT="$PARTITION_COUNT" \
        -e OUTPUT_FILE='/output/password.txt' \
        -v "${OUTPUT_DIR}:/output" \
        "$IMAGE_NAME" \
        python door_hacking.py > /dev/null
done
echo "      완료"
echo ""
echo "탐색 중... (로그 확인: docker logs cracker_0)"
echo ""

# 정답 대기
START_TIME=$(date +%s)

while [ ! -f "$OUTPUT_FILE" ]; do
    sleep 1
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
PASSWORD=$(cat "$OUTPUT_FILE")

echo "========================================"
echo " 암호 해제 성공!"
echo " 비밀번호  : ${PASSWORD}"
echo " 소요 시간 : ${ELAPSED}초"
echo "========================================"

# 전체 컨테이너 정리
echo ""
echo "컨테이너 정리 중..."
for i in $(seq 0 $((PARTITION_COUNT - 1))); do
    docker stop "cracker_${i}" > /dev/null 2>&1
    docker rm   "cracker_${i}" > /dev/null 2>&1
done
echo "완료"
