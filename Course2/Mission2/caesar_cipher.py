import sys
import tkinter as tk
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8')


# ─────────────────────────────────────────
#  설정 상수
# ─────────────────────────────────────────
PASSWORD_FILE = 'password.txt'
RESULT_FILE = 'result.txt'

# Oxford 3000 단어 목록 크롤링 URL
# 출처: https://github.com/sapbmw/The-Oxford-3000
OXFORD_3000_URL = (
    'https://raw.githubusercontent.com/'
    'sapbmw/The-Oxford-3000/master/The_Oxford_3000.txt'
)

# 영어 알파벳 빈도 순위 (높은 순서)
# 출처: Cornell University - Mathematical Exploration of Cryptography
# https://pi.math.cornell.edu/~mec/2003-2004/cryptography/subs/frequencies.html
ENGLISH_FREQ = [
    'E', 'T', 'A', 'O', 'I', 'N', 'S', 'R', 'H', 'D',
    'L', 'U', 'C', 'M', 'F', 'Y', 'W', 'G', 'P', 'B',
    'V', 'K', 'X', 'Q', 'J', 'Z',
]

# 폴백용 기본 사전 (크롤링 실패 시 사용)
FALLBACK_DICTIONARY = [
    'about', 'above', 'across', 'action', 'active', 'add', 'after',
    'again', 'age', 'ago', 'agree', 'air', 'all', 'allow', 'almost',
    'alone', 'also', 'always', 'and', 'angry', 'animal', 'answer',
    'any', 'area', 'arm', 'around', 'arrive', 'art', 'ask', 'away',
    'baby', 'back', 'bad', 'ball', 'bank', 'beach', 'because', 'become',
    'bed', 'before', 'begin', 'behind', 'believe', 'best', 'better',
    'between', 'big', 'bird', 'black', 'blue', 'body', 'book', 'born',
    'both', 'box', 'boy', 'bread', 'break', 'bright', 'bring', 'brother',
    'build', 'business', 'busy', 'buy', 'call', 'car', 'card', 'carry',
    'cat', 'check', 'child', 'choose', 'city', 'class', 'clean', 'close',
    'clothes', 'cold', 'color', 'come', 'common', 'company', 'computer',
    'cook', 'cool', 'cost', 'could', 'country', 'course', 'cow', 'create',
    'cup', 'cut', 'dad', 'dance', 'danger', 'dark', 'data', 'day',
    'dear', 'decide', 'deep', 'design', 'different', 'difficult', 'dog',
    'door', 'down', 'draw', 'dress', 'drink', 'drive', 'dry', 'each',
    'early', 'east', 'easy', 'eat', 'egg', 'end', 'enough', 'even',
    'evening', 'ever', 'every', 'everyone', 'everything', 'example',
    'eye', 'face', 'fact', 'fall', 'family', 'famous', 'fast', 'father',
    'feel', 'few', 'film', 'find', 'fine', 'fire', 'first', 'fish',
    'five', 'floor', 'fly', 'follow', 'food', 'foot', 'forget', 'four',
    'free', 'friend', 'from', 'front', 'full', 'fun', 'funny', 'game',
    'get', 'girl', 'give', 'good', 'great', 'green', 'ground', 'grow',
    'hand', 'happen', 'happy', 'hard', 'have', 'head', 'health', 'hear',
    'heart', 'heavy', 'hello', 'help', 'here', 'high', 'history', 'home',
    'hope', 'horse', 'hot', 'hotel', 'hour', 'house', 'how', 'hundred',
    'husband', 'idea', 'important', 'include', 'information', 'inside',
    'interest', 'into', 'island', 'job', 'join', 'just', 'keep', 'kid',
    'know', 'language', 'large', 'last', 'late', 'laugh', 'learn',
    'leave', 'left', 'leg', 'letter', 'level', 'life', 'light', 'like',
    'list', 'listen', 'little', 'live', 'long', 'look', 'lose', 'lot',
    'love', 'lunch', 'main', 'make', 'man', 'many', 'map', 'meal',
    'mean', 'meet', 'message', 'minute', 'miss', 'money', 'month',
    'more', 'morning', 'most', 'mother', 'move', 'movie', 'much', 'music',
    'name', 'near', 'need', 'never', 'new', 'news', 'next', 'nice',
    'night', 'note', 'nothing', 'now', 'number', 'off', 'office', 'often',
    'old', 'one', 'only', 'open', 'order', 'other', 'our', 'out',
    'outside', 'over', 'own', 'page', 'paper', 'park', 'part', 'party',
    'pay', 'people', 'phone', 'picture', 'place', 'plan', 'play',
    'please', 'point', 'police', 'popular', 'possible', 'problem',
    'program', 'put', 'question', 'quick', 'quiet', 'read', 'ready',
    'really', 'red', 'remember', 'right', 'room', 'run', 'same', 'say',
    'school', 'season', 'see', 'send', 'set', 'shop', 'short', 'show',
    'simple', 'since', 'sing', 'sister', 'sit', 'six', 'size', 'sleep',
    'slow', 'small', 'smile', 'some', 'son', 'song', 'soon', 'sorry',
    'speak', 'spend', 'sport', 'start', 'stay', 'still', 'stop', 'store',
    'story', 'street', 'strong', 'student', 'study', 'such', 'summer',
    'sure', 'swim', 'table', 'take', 'talk', 'tall', 'teach', 'teacher',
    'team', 'ten', 'than', 'that', 'the', 'their', 'them', 'then',
    'there', 'these', 'they', 'thing', 'think', 'this', 'three', 'time',
    'tired', 'today', 'together', 'too', 'top', 'town', 'train', 'travel',
    'tree', 'try', 'turn', 'two', 'under', 'until', 'use', 'usually',
    'very', 'visit', 'wait', 'walk', 'want', 'watch', 'water', 'way',
    'weather', 'week', 'well', 'what', 'when', 'where', 'which', 'while',
    'white', 'who', 'why', 'wife', 'win', 'window', 'with', 'woman',
    'word', 'work', 'world', 'write', 'year', 'yes', 'you', 'young', 'your',
]


def load_dictionary():
    '''Oxford 3000 단어 목록을 크롤링해서 반환한다.
    실패 시 폴백 사전을 반환한다.

    Returns:
        tuple: (단어 set, 출처 문자열)
    '''
    try:
        req = urllib.request.Request(
            OXFORD_3000_URL,
            headers={'User-Agent': 'Mozilla/5.0'},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read().decode('utf-8')

        # 한 줄에 한 단어, 공백 포함 구문은 첫 단어만 추출
        words = set()
        for line in raw.splitlines():
            line = line.strip().lower()
            if line:
                word = line.split()[0]
                if word.isalpha():
                    words.add(word)

        return words, 'Oxford 3000 (크롤링)'

    except (urllib.error.URLError, OSError):
        return set(FALLBACK_DICTIONARY), 'Oxford 3000 (오프라인 폴백)'


DICT_SET, DICT_SOURCE = load_dictionary()


# ─────────────────────────────────────────
#  핵심 로직
# ─────────────────────────────────────────
def extract_words(text):
    '''텍스트에서 알파벳 단어만 추출한다. (숫자, 특수문자 제외)

    Args:
        text (str): 추출할 텍스트

    Returns:
        list: 알파벳으로만 이루어진 단어 목록
    '''
    words = []
    current = ''
    for char in text.lower():
        if char.isalpha():
            current += char
        else:
            if current:
                words.append(current)
                current = ''
    if current:
        words.append(current)
    return words


def is_match(decoded):
    '''해독 결과에서 사전 단어가 1개 이상 발견되면 매칭으로 판단한다.

    Args:
        decoded (str): 해독된 텍스트

    Returns:
        tuple: (matched 단어 목록, 매칭 여부)
    '''
    words = extract_words(decoded)
    if not words:
        return [], False
    matched = [w for w in words if w in DICT_SET]
    return matched, len(matched) >= 1


def decode(text, shift):
    '''카이사르 복호화.

    Args:
        text (str): 암호화된 텍스트
        shift (int): 복호화 자리수

    Returns:
        str: 복호화된 텍스트
    '''
    result = ''
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            result += chr((ord(char) - base - shift) % 26 + base)
        else:
            result += char
    return result


def encode(text, shift):
    '''카이사르 암호화.

    Args:
        text (str): 평문
        shift (int): 암호화 자리수

    Returns:
        str: 암호화된 텍스트
    '''
    result = ''
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            result += chr((ord(char) - base + shift) % 26 + base)
        else:
            result += char
    return result


def caesar_cipher_decode(target_text):
    '''1~26 자리수로 전부 해독하고 결과와 탐지된 자리수를 반환한다.

    Args:
        target_text (str): 해독할 암호화된 문자열

    Returns:
        tuple: (results dict, auto_detected_shift or None)
    '''
    results = {}
    auto_shift = None
    for shift in range(1, 27):
        decoded = decode(target_text, shift)
        results[shift] = decoded
        if auto_shift is None:
            _, matched = is_match(decoded)
            if matched:
                auto_shift = shift
    return results, auto_shift


def frequency_analysis(text):
    '''빈도 분석으로 유력한 자리수를 반환한다.
    영어 알파벳 빈도 순위(ENGLISH_FREQ)를 기준으로 계산한다.

    Args:
        text (str): 분석할 암호화된 텍스트

    Returns:
        int or None: 유력한 자리수
    '''
    counts = {}
    for char in text.upper():
        if char.isalpha():
            counts[char] = counts.get(char, 0) + 1
    if not counts:
        return None
    most_common = max(counts, key=lambda c: counts[c])
    # ENGLISH_FREQ[0] = 'E' → 가장 자주 나오는 알파벳이 E라고 가정
    target = ENGLISH_FREQ[0]
    shift = (ord(most_common) - ord(target)) % 26
    return shift if shift != 0 else 26


def save_result(shift, text):
    '''결과를 result.txt로 저장한다.

    Args:
        shift (int): 사용된 자리수
        text (str): 해독된 텍스트

    Returns:
        bool: 저장 성공 여부
    '''
    try:
        with open(RESULT_FILE, 'w', encoding='utf-8') as f:
            f.write('카이사르 암호 해독 결과\n')
            f.write(f'자리수: {shift}\n')
            f.write(f'결과 텍스트: {text}\n')
        return True
    except IOError as e:
        print(f'파일 저장 오류: {e}')
        return False


# ─────────────────────────────────────────
#  tkinter GUI 클래스
# ─────────────────────────────────────────

# tkinter 색상 팔레트 (모던 다크 테마)
CLR_BG = '#0f0f11'          # 배경
CLR_PANEL = '#1a1a1f'       # 카드 패널
CLR_BORDER = '#2a2a35'      # 테두리
CLR_ACCENT = '#6366f1'      # 메인 액센트 (인디고)
CLR_ACCENT_DARK = '#4338ca' # 어두운 액센트
CLR_GREEN = '#10b981'       # 탐지 성공 녹색
CLR_AMBER = '#f59e0b'       # 경고 앰버
CLR_RED = '#ef4444'         # 정지 빨강
CLR_TEXT = '#e4e4e7'        # 기본 텍스트
CLR_TEXT_DIM = '#71717a'    # 흐린 텍스트
CLR_GRAY = '#27272a'        # 비활성 버튼


class CaesarGUI:
    def __init__(self, root, cipher_text):
        # tkinter 루트 윈도우 설정
        self.root = root
        self.root.title('Caesar Cipher Decoder')
        self.root.resizable(False, False)
        self.root.configure(bg=CLR_BG)

        self.cipher_text = cipher_text
        self.current_shift = tk.IntVar(value=1)
        self.ignored_shifts = set()
        self.popup_open = False
        self.auto_running = False
        self.after_id = None
        self.scan_active = False  # 자동 탐색 중일 때만 팝업 허용

        # 사전 탐지 및 빈도 분석 미리 계산
        self.results, self.auto_shift = caesar_cipher_decode(cipher_text)
        self.freq_shift = frequency_analysis(cipher_text)

        self._build_ui()
        self._update(1)

    # ── tkinter UI 구성 ──────────────────────
    def _build_ui(self):
        # tkinter: 최상단 타이틀 바
        frame_title = tk.Frame(self.root, bg=CLR_BG)
        frame_title.pack(fill='x', padx=20, pady=(20, 16))

        tk.Label(
            frame_title,
            text='Caesar Cipher Decoder',
            fg=CLR_TEXT, bg=CLR_BG,
            font=('Segoe UI', 15, 'bold'),
        ).pack(side='left')

        # tkinter: 사전 출처 배지
        tk.Label(
            frame_title,
            text=f'Oxford 3000  ·  {len(DICT_SET)} words',
            fg=CLR_TEXT_DIM, bg=CLR_BG,
            font=('Segoe UI', 9),
        ).pack(side='right', pady=(4, 0))

        # tkinter: 암호문 카드
        frame_cipher = tk.Frame(
            self.root, bg=CLR_PANEL,
            highlightbackground=CLR_BORDER, highlightthickness=1,
        )
        frame_cipher.pack(fill='x', padx=20, pady=(0, 8))

        tk.Label(
            frame_cipher,
            text='ENCRYPTED',
            fg=CLR_TEXT_DIM, bg=CLR_PANEL,
            font=('Segoe UI', 8),
        ).pack(anchor='w', padx=16, pady=(12, 2))

        tk.Label(
            frame_cipher,
            text=self.cipher_text,
            fg=CLR_TEXT, bg=CLR_PANEL,
            font=('Segoe UI', 14), wraplength=560,
        ).pack(anchor='w', padx=16, pady=(0, 12))

        # tkinter: 해독 결과 카드
        frame_decoded = tk.Frame(
            self.root, bg=CLR_PANEL,
            highlightbackground=CLR_BORDER, highlightthickness=1,
        )
        frame_decoded.pack(fill='x', padx=20, pady=(0, 8))

        tk.Label(
            frame_decoded,
            text='DECODED',
            fg=CLR_TEXT_DIM, bg=CLR_PANEL,
            font=('Segoe UI', 8),
        ).pack(anchor='w', padx=16, pady=(12, 2))

        # tkinter: 해독 결과 라벨
        self.lbl_decoded = tk.Label(
            frame_decoded,
            text='—',
            fg=CLR_TEXT, bg=CLR_PANEL,
            font=('Segoe UI', 20, 'bold'), wraplength=560,
        )
        self.lbl_decoded.pack(anchor='w', padx=16, pady=(0, 4))

        # tkinter: 탐지 결과 라벨
        self.lbl_matched = tk.Label(
            frame_decoded,
            text='',
            fg=CLR_TEXT_DIM, bg=CLR_PANEL,
            font=('Segoe UI', 9),
        )
        self.lbl_matched.pack(anchor='w', padx=16, pady=(0, 12))

        # tkinter: 슬라이더 카드
        frame_ctrl = tk.Frame(
            self.root, bg=CLR_PANEL,
            highlightbackground=CLR_BORDER, highlightthickness=1,
        )
        frame_ctrl.pack(fill='x', padx=20, pady=(0, 8))

        # tkinter: 자리수 헤더 행
        shift_header = tk.Frame(frame_ctrl, bg=CLR_PANEL)
        shift_header.pack(fill='x', padx=16, pady=(12, 6))

        tk.Label(
            shift_header,
            text='SHIFT',
            fg=CLR_TEXT_DIM, bg=CLR_PANEL,
            font=('Segoe UI', 8),
        ).pack(side='left')

        # tkinter: 자리수 숫자 표시
        self.lbl_shift = tk.Label(
            shift_header,
            text='1',
            fg=CLR_ACCENT, bg=CLR_PANEL,
            font=('Segoe UI', 13, 'bold'),
        )
        self.lbl_shift.pack(side='right')

        # tkinter: Scale 슬라이더 위젯
        self.slider = tk.Scale(
            frame_ctrl, from_=1, to=26,
            orient='horizontal',
            variable=self.current_shift,
            command=self._on_slide,
            bg=CLR_PANEL, fg=CLR_TEXT_DIM,
            troughcolor=CLR_BORDER,
            activebackground=CLR_ACCENT,
            highlightthickness=0,
            length=552, showvalue=False,
            bd=0, sliderlength=16,
        )
        self.slider.pack(padx=16, pady=(0, 6))

        # tkinter: 진행바 Canvas
        self.canvas_prog = tk.Canvas(
            frame_ctrl, width=552, height=3,
            bg=CLR_BORDER, highlightthickness=0, bd=0,
        )
        self.canvas_prog.pack(padx=16, pady=(0, 8))
        self.prog_bar = self.canvas_prog.create_rectangle(
            0, 0, 0, 3, fill=CLR_ACCENT, outline='',
        )

        # tkinter: 힌트 행
        hint_row = tk.Frame(frame_ctrl, bg=CLR_PANEL)
        hint_row.pack(fill='x', padx=16, pady=(0, 12))

        if self.auto_shift:
            tk.Label(
                hint_row,
                text=f'단어 탐지  →  {self.auto_shift}번',
                fg=CLR_GREEN, bg=CLR_PANEL,
                font=('Segoe UI', 9),
            ).pack(side='left', padx=(0, 16))

        if self.freq_shift:
            tk.Label(
                hint_row,
                text=f'빈도 분석  →  {self.freq_shift}번',
                fg=CLR_AMBER, bg=CLR_PANEL,
                font=('Segoe UI', 9),
            ).pack(side='left')

        # tkinter: 버튼 행
        frame_btn = tk.Frame(self.root, bg=CLR_BG)
        frame_btn.pack(fill='x', padx=20, pady=(0, 8))

        # tkinter: 자동 탐색 버튼
        self.btn_auto = tk.Button(
            frame_btn,
            text='자동 탐색',
            command=self._toggle_auto,
            bg=CLR_ACCENT, fg='white',
            font=('Segoe UI', 10),
            relief='flat', padx=16, pady=8,
            cursor='hand2',
            activebackground=CLR_ACCENT_DARK,
            activeforeground='white',
        )
        self.btn_auto.pack(side='left', padx=(0, 6))

        # tkinter: 수동 저장 버튼
        tk.Button(
            frame_btn,
            text='저장',
            command=self._manual_save,
            bg=CLR_GRAY, fg=CLR_TEXT,
            font=('Segoe UI', 10),
            relief='flat', padx=16, pady=8,
            cursor='hand2',
            activebackground=CLR_BORDER,
            activeforeground=CLR_TEXT,
        ).pack(side='left', padx=(0, 6))

        # tkinter: 암호화 모드 버튼
        tk.Button(
            frame_btn,
            text='암호화',
            command=self._open_encode_window,
            bg=CLR_GRAY, fg=CLR_TEXT_DIM,
            font=('Segoe UI', 10),
            relief='flat', padx=16, pady=8,
            cursor='hand2',
            activebackground=CLR_BORDER,
            activeforeground=CLR_TEXT,
        ).pack(side='left')

        # tkinter: 하단 상태바
        self.lbl_status = tk.Label(
            self.root,
            text='슬라이더를 움직이거나 자동 탐색을 실행하세요.',
            fg=CLR_TEXT_DIM, bg=CLR_BG,
            font=('Segoe UI', 9), anchor='w', padx=20,
        )
        self.lbl_status.pack(fill='x', side='bottom', pady=(0, 12))

    # ── tkinter 이벤트 핸들러 ─────────────────
    def _on_slide(self, val):
        '''tkinter Scale 슬라이더 이동 이벤트 핸들러.'''
        if not self.auto_running:
            self._update(int(float(val)))

    def _update(self, shift):
        '''해독 결과를 UI에 반영한다.'''
        decoded = self.results[shift]
        matched, hit = is_match(decoded)

        # tkinter: 자리수 및 진행바 업데이트
        self.lbl_shift.config(text=str(shift))
        self.canvas_prog.coords(
            self.prog_bar, 0, 0, int(552 * shift / 26), 3,
        )

        if hit and shift not in self.ignored_shifts and not self.popup_open and self.scan_active:
            self.lbl_decoded.config(fg=CLR_GREEN, text=decoded)
            self.lbl_matched.config(
                fg=CLR_GREEN,
                text=f'단어 발견  ·  {", ".join(matched)}',
            )
            self.lbl_status.config(
                text=f'Shift {shift}  ·  {len(matched)}개 단어 매칭됨',
            )
            # 팝업 후 이어서 진행할 수 있도록 auto 상태 저장 후 일시 정지
            was_auto = self.auto_running
            self._stop_auto()
            self._show_detect_popup(shift, decoded, matched, was_auto)
        else:
            self.lbl_decoded.config(fg=CLR_TEXT, text=decoded)
            if hit and shift in self.ignored_shifts:
                self.lbl_matched.config(
                    fg=CLR_TEXT_DIM,
                    text=f'무시됨  ·  {", ".join(matched)}',
                )
            else:
                self.lbl_matched.config(text='', fg=CLR_TEXT_DIM)
            self.lbl_status.config(
                text=f'Shift {shift}  ·  매칭 없음',
            )

    # ── 자동 탐색 ─────────────────────────────
    def _toggle_auto(self):
        if self.auto_running:
            self._stop_auto()
        else:
            self._start_auto()

    def _start_auto(self):
        self.auto_running = True
        self.scan_active = True
        self.btn_auto.config(text='정지', bg=CLR_RED, activebackground='#b91c1c')
        self.slider.config(state='disabled')
        self.current_shift.set(1)
        self._auto_step()

    def _start_auto_from(self, shift):
        '''지정한 자리수부터 자동 탐색을 이어서 진행한다.'''
        self.auto_running = True
        self.scan_active = True
        self.btn_auto.config(text='정지', bg=CLR_RED, activebackground='#b91c1c')
        self.slider.config(state='disabled')
        self.current_shift.set(shift)
        self.after_id = self.root.after(200, self._auto_step)

    def _stop_auto(self):
        self.auto_running = False
        self.scan_active = False
        self.btn_auto.config(
            text='자동 탐색', bg=CLR_ACCENT, activebackground=CLR_ACCENT_DARK,
        )
        self.slider.config(state='normal')
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def _auto_step(self):
        '''자동 탐색 1스텝 - tkinter after로 반복 호출.'''
        if not self.auto_running:
            return
        shift = self.current_shift.get()
        self._update(shift)

        if self.popup_open:
            return

        if shift < 26:
            self.current_shift.set(shift + 1)
            # tkinter: 200ms 간격으로 다음 스텝 예약
            self.after_id = self.root.after(200, self._auto_step)
        else:
            self._stop_auto()
            self.lbl_status.config(
                text='자동 탐색 완료 · 매칭 없음. 수동으로 확인하세요.',
            )

    # ── 팝업 ─────────────────────────────────
    def _show_detect_popup(self, shift, decoded, matched, was_auto=False):
        '''tkinter Toplevel 팝업 - 단어 탐지 시 표시.'''
        self.popup_open = True
        self.slider.config(state='disabled')

        # tkinter: Toplevel 팝업 윈도우
        popup = tk.Toplevel(self.root)
        popup.title('단어 탐지됨')
        popup.resizable(False, False)
        popup.grab_set()
        popup.configure(bg=CLR_BG)
        popup.geometry('380x240')

        inner = tk.Frame(popup, bg=CLR_PANEL,
                         highlightbackground=CLR_BORDER, highlightthickness=1)
        inner.pack(fill='both', expand=True, padx=16, pady=16)

        tk.Label(
            inner,
            text='단어가 발견되었습니다',
            fg=CLR_TEXT, bg=CLR_PANEL,
            font=('Segoe UI', 12, 'bold'),
        ).pack(pady=(20, 4))

        tk.Label(
            inner,
            text=f'Shift {shift}  ·  {decoded}',
            fg=CLR_GREEN, bg=CLR_PANEL,
            font=('Segoe UI', 13, 'bold'), wraplength=330,
        ).pack(pady=(0, 4))

        tk.Label(
            inner,
            text=f'매칭 단어: {", ".join(matched)}',
            fg=CLR_TEXT_DIM, bg=CLR_PANEL,
            font=('Segoe UI', 9),
        ).pack(pady=(0, 16))

        # tkinter: 팝업 버튼 행
        btn_row = tk.Frame(inner, bg=CLR_PANEL)
        btn_row.pack(pady=(0, 16))

        def on_save():
            save_result(shift, decoded)
            self.lbl_status.config(text=f'Shift {shift}  ·  result.txt 저장 완료')
            popup.destroy()
            self.popup_open = False
            self.slider.config(state='normal')
            # 자동 탐색 중이었으면 다음 자리수부터 이어서 진행
            if was_auto and shift < 26:
                self.current_shift.set(shift + 1)
                self._start_auto_from(shift + 1)

        def on_ignore():
            self.ignored_shifts.add(shift)
            popup.destroy()
            self.popup_open = False
            self.slider.config(state='normal')
            self.lbl_status.config(text=f'Shift {shift} 무시됨  ·  계속 진행')
            # 자동 탐색 중이었으면 다음 자리수부터 이어서 진행
            if was_auto and shift < 26:
                self.current_shift.set(shift + 1)
                self._start_auto_from(shift + 1)

        # tkinter: 저장 버튼
        tk.Button(
            btn_row, text='저장',
            command=on_save,
            bg=CLR_ACCENT, fg='white',
            font=('Segoe UI', 10),
            relief='flat', padx=20, pady=7,
            cursor='hand2',
            activebackground=CLR_ACCENT_DARK,
            activeforeground='white',
        ).pack(side='left', padx=(0, 8))

        # tkinter: 무시 버튼
        tk.Button(
            btn_row, text='무시하고 계속',
            command=on_ignore,
            bg=CLR_GRAY, fg=CLR_TEXT,
            font=('Segoe UI', 10),
            relief='flat', padx=20, pady=7,
            cursor='hand2',
            activebackground=CLR_BORDER,
            activeforeground=CLR_TEXT,
        ).pack(side='left')

    # ── 수동 저장 ─────────────────────────────
    def _manual_save(self):
        shift = self.current_shift.get()
        decoded = self.results[shift]
        if save_result(shift, decoded):
            self.lbl_status.config(
                text=f'Shift {shift}  ·  result.txt 저장 완료',
            )

    # ── 암호화 모드 창 ────────────────────────
    def _open_encode_window(self):
        '''tkinter Toplevel - 암호화 모드 창.'''
        win = tk.Toplevel(self.root)
        win.title('Caesar Encoder')
        win.resizable(False, False)
        win.configure(bg=CLR_BG)
        win.geometry('380x240')

        inner = tk.Frame(win, bg=CLR_PANEL,
                         highlightbackground=CLR_BORDER, highlightthickness=1)
        inner.pack(fill='both', expand=True, padx=16, pady=16)

        tk.Label(
            inner, text='암호화',
            fg=CLR_TEXT, bg=CLR_PANEL,
            font=('Segoe UI', 12, 'bold'),
        ).pack(anchor='w', padx=16, pady=(16, 8))

        # tkinter: Entry 입력 위젯
        entry_text = tk.Entry(
            inner, font=('Segoe UI', 11), width=34,
            bg=CLR_GRAY, fg=CLR_TEXT,
            insertbackground=CLR_TEXT,
            relief='flat', bd=6,
        )
        entry_text.pack(padx=16, pady=(0, 10))

        shift_var = tk.IntVar(value=1)

        shift_row = tk.Frame(inner, bg=CLR_PANEL)
        shift_row.pack(fill='x', padx=16)

        tk.Label(
            shift_row, text='Shift',
            fg=CLR_TEXT_DIM, bg=CLR_PANEL,
            font=('Segoe UI', 9),
        ).pack(side='left')

        self.lbl_enc_shift = tk.Label(
            shift_row, text='1',
            fg=CLR_ACCENT, bg=CLR_PANEL,
            font=('Segoe UI', 9, 'bold'),
        )
        self.lbl_enc_shift.pack(side='right')

        # tkinter: Scale 슬라이더
        def on_enc_slide(val):
            self.lbl_enc_shift.config(text=str(int(float(val))))

        tk.Scale(
            inner, from_=1, to=26, orient='horizontal',
            variable=shift_var, command=on_enc_slide,
            bg=CLR_PANEL, fg=CLR_TEXT_DIM,
            troughcolor=CLR_BORDER,
            highlightthickness=0, length=316,
            showvalue=False, bd=0,
        ).pack(padx=16, pady=(2, 8))

        # tkinter: 결과 라벨
        lbl_result = tk.Label(
            inner, text='',
            fg=CLR_GREEN, bg=CLR_PANEL,
            font=('Segoe UI', 11, 'bold'),
        )
        lbl_result.pack(pady=(0, 4))

        def on_encode():
            plain = entry_text.get().strip()
            if not plain:
                return
            shift = shift_var.get()
            result = encode(plain, shift)
            lbl_result.config(text=result)
            save_result(shift, result)

        # tkinter: 실행 버튼
        tk.Button(
            inner, text='암호화 & 저장',
            command=on_encode,
            bg=CLR_ACCENT, fg='white',
            font=('Segoe UI', 10),
            relief='flat', padx=14, pady=6,
            cursor='hand2',
            activebackground=CLR_ACCENT_DARK,
            activeforeground='white',
        ).pack(pady=(0, 16))


# ─────────────────────────────────────────
#  메인 실행
# ─────────────────────────────────────────
def main():
    # password.txt 읽기
    try:
        with open(PASSWORD_FILE, 'r', encoding='utf-8') as f:
            cipher_text = f.read().strip()
    except FileNotFoundError:
        print(f'오류: {PASSWORD_FILE} 파일을 찾을 수 없습니다.')
        return
    except IOError as e:
        print(f'파일 읽기 오류: {e}')
        return

    # tkinter: 루트 윈도우 생성 및 실행
    root = tk.Tk()
    root.configure(bg=CLR_BG)
    root.geometry('600x520')
    CaesarGUI(root, cipher_text)
    root.mainloop()


if __name__ == '__main__':
    main()