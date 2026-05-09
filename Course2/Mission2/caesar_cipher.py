import sys

sys.stdout.reconfigure(encoding='utf-8')


PASSWORD_FILE = 'password.txt'
RESULT_FILE = 'result.txt'

# 영어 알파벳 빈도 순위 (높은 순서)
# 출처: Cornell University - Mathematical Exploration of Cryptography
# https://pi.math.cornell.edu/~mec/2003-2004/cryptography/subs/frequencies.html
ENGLISH_FREQ = [
    'E', 'T', 'A', 'O', 'I', 'N', 'S', 'R', 'H', 'D',
    'L', 'U', 'C', 'M', 'F', 'Y', 'W', 'G', 'P', 'B',
    'V', 'K', 'X', 'Q', 'J', 'Z',
]

# 보너스: 영어 사전 단어 목록 (자동 탐지용)
# Oxford 3000 A1 레벨 기반 고빈도 500개 (3글자 이상)
# 출처: Oxford Learner's Dictionaries - The Oxford 3000 (American English)
# https://www.oxfordlearnersdictionaries.com/external/pdf/wordlists/oxford-3000-5000/American_Oxford_3000.pdf
DICTIONARY = [
    'about', 'above', 'across', 'action', 'active', 'activity', 'actor', 'actress',
    'add', 'address', 'adult', 'advice', 'afraid', 'after', 'afternoon', 'again',
    'against', 'age', 'ago', 'agree', 'air', 'airport', 'all', 'allow',
    'almost', 'alone', 'along', 'already', 'also', 'always', 'amazing', 'and',
    'angry', 'animal', 'another', 'answer', 'any', 'anyone', 'anything', 'anyway',
    'anywhere', 'apple', 'area', 'arm', 'around', 'arrive', 'art', 'article',
    'artist', 'ask', 'away', 'awesome', 'awful', 'baby', 'back', 'bad',
    'bag', 'ball', 'band', 'bank', 'baseball', 'basketball', 'bath', 'bathroom',
    'beach', 'beautiful', 'because', 'become', 'bed', 'bedroom', 'beer', 'before',
    'begin', 'behind', 'believe', 'best', 'better', 'between', 'bicycle', 'big',
    'bike', 'bill', 'bird', 'birthday', 'black', 'blog', 'blond', 'blue',
    'body', 'book', 'boot', 'bored', 'boring', 'born', 'both', 'bottle',
    'box', 'boy', 'boyfriend', 'bread', 'break', 'breakfast', 'bright', 'bring',
    'broken', 'brother', 'brown', 'build', 'building', 'bus', 'business', 'busy',
    'but', 'butter', 'buy', 'cake', 'call', 'camera', 'can', 'capital',
    'car', 'card', 'careful', 'carefully', 'carry', 'cat', 'cent', 'center',
    'chart', 'cheap', 'check', 'cheese', 'chicken', 'child', 'chocolate', 'choose',
    'circle', 'city', 'class', 'classroom', 'clean', 'climb', 'clock', 'close',
    'clothes', 'club', 'coffee', 'cold', 'color', 'come', 'common', 'company',
    'compare', 'compete', 'competition', 'complete', 'completely', 'computer', 'concert', 'cook',
    'cooking', 'cool', 'correct', 'correctly', 'cost', 'could', 'country', 'course',
    'cousin', 'cow', 'create', 'crime', 'criminal', 'crowd', 'cultural', 'culture',
    'cup', 'customer', 'cut', 'dad', 'dance', 'dancer', 'dancing', 'danger',
    'dangerous', 'dark', 'data', 'date', 'daughter', 'day', 'dear', 'decide',
    'deep', 'definitely', 'degree', 'design', 'desk', 'detail', 'different', 'difficult',
    'dinner', 'dirty', 'doctor', 'dog', 'door', 'down', 'draw', 'dress',
    'drink', 'drive', 'driver', 'dry', 'during', 'each', 'early', 'east',
    'easy', 'eat', 'egg', 'eight', 'either', 'email', 'end', 'enough',
    'enter', 'even', 'evening', 'ever', 'every', 'everybody', 'everyone', 'everything',
    'everywhere', 'example', 'excuse', 'eye', 'face', 'fact', 'fall', 'family',
    'famous', 'far', 'fast', 'father', 'feel', 'few', 'film', 'find',
    'fine', 'fire', 'first', 'fish', 'five', 'floor', 'fly', 'follow',
    'food', 'foot', 'for', 'foreign', 'forget', 'four', 'free', 'friend',
    'from', 'front', 'full', 'fun', 'funny', 'game', 'get', 'girl',
    'give', 'good', 'great', 'green', 'ground', 'grow', 'guess', 'gun',
    'guy', 'hand', 'happen', 'happy', 'hard', 'have', 'head', 'health',
    'hear', 'heart', 'heavy', 'hello', 'help', 'here', 'high', 'history',
    'home', 'hope', 'horse', 'hospital', 'hot', 'hotel', 'hour', 'house',
    'how', 'hundred', 'hungry', 'husband', 'idea', 'important', 'include', 'information',
    'inside', 'instead', 'interest', 'interesting', 'internet', 'into', 'island', 'job',
    'join', 'just', 'keep', 'key', 'kid', 'kitchen', 'know', 'language',
    'large', 'last', 'late', 'laugh', 'learn', 'leave', 'left', 'leg',
    'let', 'letter', 'level', 'life', 'light', 'like', 'list', 'listen',
    'little', 'live', 'local', 'long', 'look', 'lose', 'lot', 'love',
    'lunch', 'main', 'make', 'man', 'many', 'map', 'market', 'meal',
    'mean', 'meet', 'menu', 'message', 'minute', 'miss', 'mom', 'money',
    'month', 'more', 'morning', 'most', 'mother', 'move', 'movie', 'much',
    'music', 'name', 'near', 'need', 'never', 'new', 'news', 'next',
    'nice', 'night', 'not', 'note', 'nothing', 'now', 'number', 'off',
    'office', 'often', 'old', 'one', 'only', 'open', 'order', 'other',
    'our', 'out', 'outside', 'over', 'own', 'page', 'paper', 'park',
    'part', 'party', 'pay', 'people', 'phone', 'photo', 'picture', 'place',
    'plan', 'play', 'player', 'please', 'point', 'police', 'popular', 'possible',
    'prefer', 'problem', 'program', 'put', 'question', 'quick', 'quickly', 'quiet',
    'read', 'ready', 'really', 'red', 'remember', 'restaurant', 'right', 'room',
    'run', 'same', 'say', 'school', 'season', 'see', 'send', 'set',
    'shop', 'short', 'show', 'simple', 'since', 'sing', 'sister', 'sit',
    'six', 'size', 'sleep', 'slow', 'small', 'smile', 'some', 'sometimes',
    'son', 'song', 'soon', 'sorry', 'speak', 'spend', 'sport', 'start',
    'stay', 'still', 'stop', 'store', 'story', 'street', 'strong', 'student',
    'study', 'such', 'summer', 'sure', 'swim', 'table', 'take', 'talk',
    'tall', 'tea', 'teach', 'teacher', 'team', 'ten', 'than', 'that',
    'the', 'their', 'them', 'then',
]


def frequency_analysis(target_text):
    '''암호문의 알파벳 빈도를 분석해 유력한 자리수를 반환한다.

    영어에서 가장 자주 쓰이는 알파벳은 E이므로,
    암호문에서 가장 많이 등장한 알파벳이 E라고 가정해 자리수를 계산한다.

    Args:
        target_text (str): 분석할 암호화된 문자열

    Returns:
        int or None: 유력한 자리수, 알파벳이 없으면 None
    '''
    counts = {}
    for char in target_text.upper():
        if char.isalpha():
            counts[char] = counts.get(char, 0) + 1

    if not counts:
        return None

    most_common = max(counts, key=lambda c: counts[c])
    shift = (ord(most_common) - ord('E')) % 26

    print(f'  암호문 최다 등장 알파벳: {most_common} ({counts[most_common]}회)')
    print(f'  영어 통계 기준 E로 가정 → 유력 자리수: {shift if shift != 0 else 26}')

    return shift if shift != 0 else 26


def caesar_cipher_encode(target_text, shift):
    '''평문을 카이사르 암호로 암호화한다.

    Args:
        target_text (str): 암호화할 평문
        shift (int): 밀 자리수 (1~26)

    Returns:
        str: 암호화된 문자열
    '''
    encoded = ''
    for char in target_text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            encoded += chr((ord(char) - base + shift) % 26 + base)
        else:
            encoded += char
    return encoded


def caesar_cipher_decode(target_text):
    '''카이사르 암호를 26가지 자리수로 해독하여 출력한다.

    Args:
        target_text (str): 해독할 암호화된 문자열

    Returns:
        tuple: (results dict, auto_detected_shift or None)
    '''
    print('=' * 60)
    print('카이사르 암호 해독 결과')
    print('=' * 60)

    results = {}
    auto_shift = None

    for shift in range(1, 27):
        decoded = ''
        for char in target_text:
            if char.isalpha():
                base = ord('A') if char.isupper() else ord('a')
                decoded += chr((ord(char) - base - shift) % 26 + base)
            else:
                decoded += char

        results[shift] = decoded
        print(f'[{shift:2d}] {decoded}')

        # 보너스: 사전 단어 자동 탐지
        if auto_shift is None:
            words = decoded.lower().split()
            matched = [w for w in words if w in DICTIONARY]
            if len(matched) >= 2:
                auto_shift = shift
                print(f'      ★ 사전 단어 발견: {matched}')

    return results, auto_shift


def save_result(mode, shift, text):
    '''처리 결과를 result.txt로 저장한다.

    Args:
        mode (str): 'decode' 또는 'encode'
        shift (int): 사용된 자리수
        text (str): 처리된 텍스트
    '''
    try:
        with open(RESULT_FILE, 'w', encoding='utf-8') as f:
            if mode == 'decode':
                f.write('카이사르 암호 해독 결과\n')
            else:
                f.write('카이사르 암호 암호화 결과\n')
            f.write(f'자리수: {shift}\n')
            f.write(f'결과 텍스트: {text}\n')
        print(f'result.txt 저장 완료')
        print(f'자리수: {shift}, 결과: {text}')
    except IOError as e:
        print(f'파일 저장 오류: {e}')


def run_decode(target_text):
    '''해독 모드 실행'''
    # 빈도 분석으로 유력 자리수 사전 제시
    print('\n[빈도 분석]')
    freq_shift = frequency_analysis(target_text)

    print()
    results, auto_shift = caesar_cipher_decode(target_text)
    print('=' * 60)

    # 최종 자리수 결정 우선순위: 사전탐지 > 빈도분석 > 수동입력
    if auto_shift is not None:
        print(f'\n★ 사전 자동 탐지: {auto_shift}번 자리수가 유력합니다.')
        hint = auto_shift
    elif freq_shift is not None:
        print(f'\n★ 빈도 분석 추천: {freq_shift}번 자리수가 유력합니다.')
        hint = freq_shift
    else:
        hint = None

    if hint is not None:
        user_input = input(
            f'자리수를 입력하세요 (Enter 시 {hint}번 적용): '
        ).strip()
        selected = hint if user_input == '' else None
    else:
        user_input = input('\n몇 번째 자리수로 해독되었나요? (1~26): ').strip()
        selected = None

    if selected is None:
        if user_input.isdigit() and 1 <= int(user_input) <= 26:
            selected = int(user_input)
        else:
            print('잘못된 입력입니다. 1~26 사이 숫자를 입력하세요.')
            return

    save_result('decode', selected, results[selected])


def run_encode():
    '''암호화 모드 실행'''
    plain_text = input('암호화할 텍스트를 입력하세요: ').strip()
    if not plain_text:
        print('텍스트를 입력하세요.')
        return

    shift_input = input('자리수를 입력하세요 (1~26): ').strip()
    if not shift_input.isdigit() or not (1 <= int(shift_input) <= 26):
        print('잘못된 입력입니다. 1~26 사이 숫자를 입력하세요.')
        return

    shift = int(shift_input)
    encoded = caesar_cipher_encode(plain_text, shift)

    print(f'\n원문:   {plain_text}')
    print(f'자리수: {shift}')
    print(f'암호문: {encoded}')

    save_result('encode', shift, encoded)


def main():
    print('=' * 60)
    print('카이사르 암호 도구')
    print('=' * 60)
    print('[1] 암호 해독 (password.txt)')
    print('[2] 암호화')
    mode_input = input('모드를 선택하세요 (1 또는 2): ').strip()

    if mode_input == '1':
        # password.txt 읽기
        try:
            with open(PASSWORD_FILE, 'r', encoding='utf-8') as f:
                target_text = f.read().strip()
        except FileNotFoundError:
            print(f'오류: {PASSWORD_FILE} 파일을 찾을 수 없습니다.')
            return
        except IOError as e:
            print(f'파일 읽기 오류: {e}')
            return

        print(f'\n암호화된 텍스트: {target_text}')
        run_decode(target_text)

    elif mode_input == '2':
        run_encode()

    else:
        print('잘못된 입력입니다. 1 또는 2를 입력하세요.')


if __name__ == '__main__':
    main()
