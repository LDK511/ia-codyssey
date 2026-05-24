"""javis.py - J.A.R.V.I.S 음성 녹음 및 STT 관리 시스템.

Mission 8: 녹음된 음성 파일을 텍스트로 변환(STT)하고 시간 정보와
함께 CSV 로 저장한다. 또한 CSV 안의 인식 텍스트에서 키워드를
검색할 수 있는 기능을 함께 제공한다 (보너스 과제).
"""

import os
import re
import csv
import time
import wave
import struct
import logging
import sqlite3
import zipfile
import datetime
import platform
import argparse
import threading
import statistics
import tempfile
import subprocess
import configparser
import tkinter as tk
from tkinter import messagebox
import pyaudio
import speech_recognition as sr


# ── 설정 파일 (configparser) ──────────────────────────────
CONFIG_FILE = 'javis.ini'


def load_config():
    """설정 파일을 읽고 ConfigParser 객체를 반환한다.

    파일이 없으면 기본값으로 생성한다.
    """
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        config['audio'] = {
            'rate': '44100',
            'channels': '1',
            'chunk': '1024',
        }
        config['paths'] = {
            'records_dir': 'records',
            'log_file': 'javis.log',
            'db_file': 'javis.db',
        }
        config['stt'] = {
            'language': 'ko-KR',
            'segment_seconds': '5',
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    config.read(CONFIG_FILE, encoding='utf-8')
    if 'stt' not in config:
        config['stt'] = {
            'language': 'ko-KR',
            'segment_seconds': '5',
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    return config


CONFIG = load_config()
RECORDS_DIR = CONFIG['paths']['records_dir']
LOG_FILE = CONFIG['paths']['log_file']
DB_FILE = CONFIG['paths']['db_file']
CHUNK = int(CONFIG['audio']['chunk'])
FORMAT = pyaudio.paInt16
CHANNELS = int(CONFIG['audio']['channels'])
RATE = int(CONFIG['audio']['rate'])
STT_LANGUAGE = CONFIG['stt'].get('language', 'ko-KR')
STT_SEGMENT_SECONDS = int(CONFIG['stt'].get('segment_seconds', '5'))


# ── 로깅 (logging) ────────────────────────────────────────
def setup_logging():
    """파일 로그 시스템을 초기화한다."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        encoding='utf-8',
    )


setup_logging()
logger = logging.getLogger(__name__)


# ── 유틸 ──────────────────────────────────────────────────
def ensure_records_dir():
    """records 디렉토리가 없으면 생성한다."""
    if not os.path.exists(RECORDS_DIR):
        os.makedirs(RECORDS_DIR)
        logger.info('records 디렉토리 생성: %s', RECORDS_DIR)


def get_filename():
    """현재 날짜와 시간을 기반으로 WAV 파일명을 반환한다."""
    now = datetime.datetime.now()
    return now.strftime('%Y%m%d-%H%M%S') + '.wav'


def format_duration(seconds):
    """초를 mm:ss 형식의 문자열로 반환한다."""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f'{minutes:02d}:{secs:02d}'


# ── PyAudio 경고 억제 ──────────────────────────────────────
def suppress_stderr():
    """stderr를 임시로 억제하고 원래 디스크립터를 반환한다."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    return old_stderr


def restore_stderr(old_stderr):
    """억제된 stderr를 복원한다."""
    os.dup2(old_stderr, 2)
    os.close(old_stderr)


def create_pyaudio():
    """경고 메시지 없이 PyAudio 인스턴스를 생성하여 반환한다."""
    old_stderr = suppress_stderr()
    try:
        audio = pyaudio.PyAudio()
    finally:
        restore_stderr(old_stderr)
    return audio


# ── DB (sqlite3) ──────────────────────────────────────────
def init_db():
    """DB를 초기화하고 recordings 테이블을 생성한다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recordings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT UNIQUE NOT NULL,
            recorded_at TEXT NOT NULL,
            duration    REAL NOT NULL,
            sample_rate INTEGER NOT NULL,
            channels    INTEGER NOT NULL,
            bit_depth   INTEGER NOT NULL,
            has_memo    INTEGER DEFAULT 0,
            has_stt     INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('PRAGMA table_info(recordings)')
    columns = [row[1] for row in cursor.fetchall()]
    if 'has_stt' not in columns:
        cursor.execute(
            'ALTER TABLE recordings ADD COLUMN has_stt INTEGER DEFAULT 0'
        )
    conn.commit()
    conn.close()


def sync_db():
    """records 디렉토리의 파일을 DB에 동기화한다."""
    ensure_records_dir()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for filename in os.listdir(RECORDS_DIR):
        if not filename.endswith('.wav'):
            continue
        filepath = os.path.join(RECORDS_DIR, filename)
        memo_path = filepath.replace('.wav', '.txt')
        csv_path = filepath.replace('.wav', '.csv')
        has_memo = 1 if os.path.exists(memo_path) else 0
        has_stt = 1 if os.path.exists(csv_path) else 0
        cursor.execute(
            'SELECT id FROM recordings WHERE filename = ?', (filename,)
        )
        if cursor.fetchone():
            cursor.execute(
                'UPDATE recordings SET has_memo = ?, has_stt = ? '
                'WHERE filename = ?',
                (has_memo, has_stt, filename),
            )
            continue
        try:
            info = get_wav_info(filepath)
            parts = filename.replace('.wav', '').split('-')
            recorded_at = datetime.datetime.strptime(
                parts[0] + parts[1], '%Y%m%d%H%M%S'
            ).isoformat()
            cursor.execute('''
                INSERT INTO recordings
                    (filename, recorded_at, duration,
                     sample_rate, channels, bit_depth, has_memo, has_stt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename, recorded_at, info['duration'],
                info['sample_rate'], info['channels'],
                info['sample_width'], has_memo, has_stt,
            ))
        except Exception as exc:
            logger.warning('DB 동기화 실패 (%s): %s', filename, exc)
    conn.commit()
    conn.close()


def insert_recording(filename, info):
    """새 녹음 파일 정보를 DB에 삽입한다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    recorded_at = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT OR IGNORE INTO recordings
            (filename, recorded_at, duration,
             sample_rate, channels, bit_depth, has_memo, has_stt)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0)
    ''', (
        filename, recorded_at, info['duration'],
        info['sample_rate'], info['channels'], info['sample_width'],
    ))
    conn.commit()
    conn.close()


def update_memo_flag(filename):
    """DB에서 has_memo 플래그를 1로 업데이트한다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE recordings SET has_memo = 1 WHERE filename = ?',
        (filename,)
    )
    conn.commit()
    conn.close()


def update_stt_flag(filename):
    """DB에서 has_stt 플래그를 1로 업데이트한다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE recordings SET has_stt = 1 WHERE filename = ?',
        (filename,)
    )
    conn.commit()
    conn.close()


def query_recordings(start_date=None, end_date=None):
    """DB에서 녹음 목록을 조회하여 반환한다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    sql = '''
        SELECT filename, recorded_at, duration, has_memo, has_stt
        FROM recordings
    '''
    params = []
    if start_date and end_date:
        sql += ' WHERE recorded_at >= ? AND recorded_at <= ?'
        params = [
            start_date.isoformat(),
            end_date.isoformat() + 'T23:59:59',
        ]
    sql += ' ORDER BY recorded_at'
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


# ── WAV 유틸 ──────────────────────────────────────────────
def get_wav_info(filepath):
    """WAV 파일의 메타데이터를 반환한다."""
    with wave.open(filepath, 'rb') as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return {
            'duration': frames / rate,
            'channels': wf.getnchannels(),
            'sample_rate': rate,
            'sample_width': wf.getsampwidth() * 8,
        }


def get_wav_files():
    """records 디렉토리의 WAV 파일 목록을 정렬하여 반환한다."""
    ensure_records_dir()
    return sorted([
        f for f in os.listdir(RECORDS_DIR)
        if f.endswith('.wav')
    ])


# ── 마이크 / 녹음 ──────────────────────────────────────────
def list_microphones():
    """사용 가능한 마이크 목록을 출력한다."""
    audio = create_pyaudio()
    print('사용 가능한 마이크 목록:')
    found = False
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            device_name = info['name']
            print(f'  [{i}] {device_name}')
            found = True
    if not found:
        print('  인식된 마이크가 없습니다.')
    audio.terminate()


def record_audio(on_chunk=None):
    """시스템 마이크를 인식하고 음성을 녹음한다."""
    audio = create_pyaudio()
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )
    frames = []
    try:
        while True:
            data = stream.read(CHUNK)
            frames.append(data)
            if on_chunk:
                on_chunk(data)
    except KeyboardInterrupt:
        pass
    stream.stop_stream()
    stream.close()
    sample_width = audio.get_sample_size(FORMAT)
    audio.terminate()
    return frames, sample_width


def save_recording(frames, sample_width):
    """녹음된 데이터를 WAV 파일로 저장하고 DB에 등록한다."""
    ensure_records_dir()
    filename = get_filename()
    filepath = os.path.join(RECORDS_DIR, filename)
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(sample_width)
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    info = get_wav_info(filepath)
    insert_recording(filename, info)
    logger.info('녹음 저장: %s (%.1fs)', filename, info['duration'])
    print(f'파일이 저장되었습니다: {filepath}')
    return filepath, filename


# ── 재생 ──────────────────────────────────────────────────
def play_recording(filepath):
    """WAV 파일을 시스템 기본 플레이어로 재생한다."""
    system = platform.system()
    try:
        if system == 'Darwin':
            subprocess.run(['afplay', filepath], check=True)
        elif system == 'Linux':
            subprocess.run(['aplay', filepath], check=True)
        elif system == 'Windows':
            subprocess.run(
                ['start', '', filepath], shell=True, check=True
            )
        else:
            print(f'지원하지 않는 운영체제입니다: {system}')
    except FileNotFoundError:
        print('오디오 재생 명령어를 찾을 수 없습니다.')
    except subprocess.CalledProcessError:
        print('재생 중 오류가 발생했습니다.')


# ── 메모 ──────────────────────────────────────────────────
def add_memo(filepath):
    """녹음 파일과 함께 텍스트 메모를 저장한다."""
    memo_path = filepath.replace('.wav', '.txt')
    print('메모를 입력하세요 (빈 줄에서 Enter를 누르면 저장됩니다):')
    lines = []
    while True:
        line = input()
        if line == '':
            break
        lines.append(line)
    if not lines:
        print('메모 없이 저장합니다.')
        return
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    wav_name = os.path.basename(filepath)
    with open(memo_path, 'w', encoding='utf-8') as f:
        f.write(f'날짜: {now}\n')
        f.write(f'녹음 파일: {wav_name}\n')
        f.write('-' * 30 + '\n')
        f.write('\n'.join(lines))
    update_memo_flag(wav_name)
    logger.info('메모 저장: %s', memo_path)
    print(f'메모가 저장되었습니다: {memo_path}')


# ── 메모 검색 (re) ────────────────────────────────────────
def search_memos(keyword):
    """메모 파일에서 키워드(정규식 지원)를 검색한다."""
    results = []
    pattern = re.compile(keyword, re.IGNORECASE)
    for filename in get_wav_files():
        memo_path = os.path.join(
            RECORDS_DIR, filename.replace('.wav', '.txt')
        )
        if not os.path.exists(memo_path):
            continue
        with open(memo_path, 'r', encoding='utf-8') as f:
            for line in f:
                if pattern.search(line):
                    results.append((filename, line.strip()))
    return results


# ── STT (Speech to Text) ──────────────────────────────────
def transcribe_audio(filepath, segment_seconds=None, language=None):
    """WAV 파일을 일정 구간으로 잘라 STT 를 수행한다."""
    if segment_seconds is None:
        segment_seconds = STT_SEGMENT_SECONDS
    if language is None:
        language = STT_LANGUAGE
    recognizer = sr.Recognizer()
    results = []
    with sr.AudioFile(filepath) as source:
        total_duration = source.DURATION or 0
        offset = 0.0
        while offset < total_duration:
            remaining = total_duration - offset
            duration = min(segment_seconds, remaining)
            try:
                audio = recognizer.record(source, duration=duration)
            except Exception as exc:
                logger.warning('오디오 읽기 실패 (%s): %s', filepath, exc)
                break
            try:
                text = recognizer.recognize_google(
                    audio, language=language
                )
            except sr.UnknownValueError:
                text = ''
            except sr.RequestError as exc:
                logger.warning('STT 요청 실패: %s', exc)
                text = f'[STT 오류: {exc}]'
            text = text.strip()
            if text:
                results.append((format_duration(int(offset)), text))
            offset += duration
    return results


def save_transcript_csv(filepath, results):
    """STT 결과를 동일 이름의 CSV 파일로 저장한다."""
    csv_path = filepath.replace('.wav', '.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'text'])
        for time_str, text in results:
            writer.writerow([time_str, text])
    update_stt_flag(os.path.basename(filepath))
    logger.info('STT CSV 저장: %s (%d 구간)', csv_path, len(results))
    return csv_path


def run_stt_on_file(filename):
    """단일 파일에 대해 STT를 실행하고 CSV로 저장한다."""
    filepath = os.path.join(RECORDS_DIR, filename)
    if not os.path.exists(filepath):
        return None, []
    results = transcribe_audio(filepath)
    csv_path = save_transcript_csv(filepath, results)
    return csv_path, results


def run_stt_on_all():
    """records 디렉토리의 모든 WAV 파일에 대해 STT를 실행한다."""
    ensure_records_dir()
    summary = []
    for filename in get_wav_files():
        csv_path, results = run_stt_on_file(filename)
        summary.append((filename, csv_path, len(results)))
    return summary


# ── CSV 키워드 검색 (보너스) ──────────────────────────────
def search_transcripts(keyword):
    """CSV 파일 안의 인식된 텍스트에서 키워드를 검색한다."""
    ensure_records_dir()
    results = []
    pattern = re.compile(keyword, re.IGNORECASE)
    for filename in sorted(os.listdir(RECORDS_DIR)):
        if not filename.endswith('.csv'):
            continue
        csv_path = os.path.join(RECORDS_DIR, filename)
        try:
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) < 2:
                        continue
                    time_str, text = row[0], row[1]
                    if pattern.search(text):
                        results.append((filename, time_str, text))
        except Exception as exc:
            logger.warning('CSV 읽기 실패 (%s): %s', filename, exc)
    return results


# ── 통계 / 백업 ───────────────────────────────────────────
def get_recording_stats():
    """녹음 파일의 통계 정보를 반환한다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT duration FROM recordings')
    durations = [row[0] for row in cursor.fetchall()]
    conn.close()
    if not durations:
        return None
    return {
        'count': len(durations),
        'total': sum(durations),
        'mean': statistics.mean(durations),
        'median': statistics.median(durations),
        'stdev': statistics.stdev(durations) if len(durations) >= 2 else 0.0,
    }


def backup_recordings():
    """records 디렉토리를 ZIP 파일로 백업한다."""
    ensure_records_dir()
    now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_name = f'javis_backup_{now}.zip'
    with zipfile.ZipFile(backup_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in os.listdir(RECORDS_DIR):
            filepath = os.path.join(RECORDS_DIR, filename)
            zf.write(filepath, os.path.join('records', filename))
    logger.info('백업 생성: %s', backup_name)
    return backup_name


# ── GUI (tkinter) ─────────────────────────────────────────
class JarvisGui:
    """자비스 HUD 스타일 tkinter GUI."""

    BG = '#050810'
    SURFACE = '#0B1424'
    SURFACE_HI = '#11203A'
    PANEL = '#08111F'
    CYAN = '#00D9FF'
    CYAN_BRIGHT = '#7DEBFF'
    CYAN_DIM = '#0E5A7A'
    BORDER = '#1A3548'
    TEXT = '#E8F4FF'
    TEXT_DIM = '#6E8AA8'
    GOLD = '#FFB400'
    RED = '#FF4655'
    GRID = '#0F2236'

    FONT_FAMILY = 'Segoe UI'
    FONT_MONO = 'Consolas'
    FONT_BRAND = (FONT_FAMILY, 22, 'bold')
    FONT_SUB = (FONT_FAMILY, 9)
    FONT_TIMER = (FONT_MONO, 36, 'bold')
    FONT_BTN = (FONT_FAMILY, 9, 'bold')
    FONT_LIST = (FONT_MONO, 10)
    FONT_STATUS = (FONT_FAMILY, 9)
    FONT_LABEL = (FONT_FAMILY, 9, 'bold')

    WAVE_W = 840
    WAVE_H = 140
    LIVE_SEGMENT_SECONDS = 4
    MAX_LIVE_LINES = 8
    VOICE_START_KEYWORDS = (
        '시작', '시잭', '시잡', '녹음', '레코드', '레코딩',
        'start', 'record',
    )
    VOICE_STOP_KEYWORDS = (
        '종료', '정지', '멈춰', '멈춤', '스톱', '스탑',
        '그만', '끝', 'stop',
    )

    def __init__(self, root):
        self.root = root
        self.root.title('J.A.R.V.I.S  ::  Mark II Audio Cortex')
        self.root.configure(bg=self.BG)
        self.root.geometry('960x860')
        self.root.minsize(900, 820)
        self.is_recording = False
        self.record_frames = []
        self.record_sample_width = 2
        self.elapsed_secs = 0
        self.waveform_data = [0.0] * 220
        self.search_mode = tk.StringVar(value='memo')
        self._pulse_phase = 0
        self._scan_x = 0
        self._rec_btn = None
        self._voice_btn = None
        self.voice_enabled = True
        self.voice_listener_stop = None
        self.live_lines = []
        self.live_text = None
        self._build_ui()
        self._refresh_list()
        self._animate()
        # 앱 시작과 동시에 음성 리스너를 켠다
        self.root.after(400, self._start_voice_listener)

    def _round_rect(self, canvas, x1, y1, x2, y2, r, **kwargs):
        """라운드 사각형을 그려서 id를 반환한다."""
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1,
            x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2,
            x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_brackets(self, canvas, x1, y1, x2, y2, size=14, color=None):
        """HUD 스타일의 코너 브래킷을 그린다."""
        color = color or self.CYAN_DIM
        canvas.create_line(x1, y1, x1 + size, y1, fill=color, width=2)
        canvas.create_line(x1, y1, x1, y1 + size, fill=color, width=2)
        canvas.create_line(x2, y1, x2 - size, y1, fill=color, width=2)
        canvas.create_line(x2, y1, x2, y1 + size, fill=color, width=2)
        canvas.create_line(x1, y2, x1 + size, y2, fill=color, width=2)
        canvas.create_line(x1, y2, x1, y2 - size, fill=color, width=2)
        canvas.create_line(x2, y2, x2 - size, y2, fill=color, width=2)
        canvas.create_line(x2, y2, x2, y2 - size, fill=color, width=2)

    def _build_button(self, parent, label, command, kind='primary', width=128):
        """라운드 캔버스 버튼을 생성하여 반환한다."""
        if kind == 'primary':
            outline = self.CYAN
            fill = self.SURFACE
            fg = self.CYAN_BRIGHT
            hover_fill = self.SURFACE_HI
        elif kind == 'danger':
            outline = self.RED
            fill = '#1A0A0E'
            fg = self.RED
            hover_fill = '#2A0F14'
        else:
            outline = self.BORDER
            fill = self.SURFACE
            fg = self.TEXT_DIM
            hover_fill = self.SURFACE_HI
        height = 34
        cv = tk.Canvas(
            parent, width=width, height=height,
            bg=self.BG, highlightthickness=0, cursor='hand2',
        )
        rect = self._round_rect(
            cv, 1, 1, width - 1, height - 1, 8,
            fill=fill, outline=outline, width=1,
        )
        text_id = cv.create_text(
            width // 2, height // 2,
            text=label, fill=fg, font=self.FONT_BTN,
        )
        state = {
            'fill': fill, 'hover_fill': hover_fill, 'fg': fg,
            'outline': outline, 'kind': kind,
        }
        cv.bind(
            '<Enter>',
            lambda _e: cv.itemconfig(rect, fill=state['hover_fill']),
        )
        cv.bind(
            '<Leave>',
            lambda _e: cv.itemconfig(rect, fill=state['fill']),
        )
        cv.bind('<Button-1>', lambda _e: command())
        cv._rect = rect
        cv._text = text_id
        cv._state = state
        return cv

    def _set_button_kind(self, btn, label, kind):
        """버튼의 색상/라벨을 동적으로 변경한다."""
        if kind == 'primary':
            outline, fill, fg, hover = (
                self.CYAN, self.SURFACE, self.CYAN_BRIGHT, self.SURFACE_HI
            )
        elif kind == 'danger':
            outline, fill, fg, hover = (
                self.RED, '#1A0A0E', self.RED, '#2A0F14'
            )
        else:
            outline, fill, fg, hover = (
                self.BORDER, self.SURFACE, self.TEXT_DIM, self.SURFACE_HI
            )
        btn.itemconfig(btn._rect, outline=outline, fill=fill)
        btn.itemconfig(btn._text, text=label, fill=fg)
        btn._state.update({
            'fill': fill, 'hover_fill': hover, 'fg': fg,
            'outline': outline, 'kind': kind,
        })

    def _build_ui(self):
        """UI 컴포넌트를 구성한다."""
        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill='x', padx=24, pady=(20, 4))
        tk.Label(
            header, text='J A R V I S',
            font=self.FONT_BRAND, bg=self.BG, fg=self.CYAN,
        ).pack(anchor='w')
        sub = tk.Frame(header, bg=self.BG)
        sub.pack(anchor='w', pady=(2, 0))
        tk.Label(
            sub, text='MARK II  /  AUDIO CORTEX',
            font=self.FONT_SUB, bg=self.BG, fg=self.TEXT_DIM,
        ).pack(side='left')
        tk.Label(
            sub, text='   v8.0', font=self.FONT_SUB,
            bg=self.BG, fg=self.CYAN_DIM,
        ).pack(side='left')

        sep = tk.Canvas(
            self.root, height=1, bg=self.BG, highlightthickness=0,
        )
        sep.pack(fill='x', padx=24, pady=(8, 14))
        sep.bind(
            '<Configure>',
            lambda e: (
                sep.delete('all'),
                sep.create_line(0, 0, e.width, 0, fill=self.BORDER),
            ),
        )

        wave_wrap = tk.Frame(self.root, bg=self.BG)
        wave_wrap.pack(fill='x', padx=24)
        tk.Label(
            wave_wrap, text='AUDIO STREAM',
            font=self.FONT_LABEL, bg=self.BG, fg=self.CYAN_DIM,
        ).pack(anchor='w')
        self.canvas = tk.Canvas(
            wave_wrap, width=self.WAVE_W, height=self.WAVE_H,
            bg=self.PANEL, highlightthickness=0,
        )
        self.canvas.pack(fill='x', pady=(4, 0))
        self._draw_waveform()

        meter = tk.Frame(self.root, bg=self.BG)
        meter.pack(pady=(14, 10))
        self.timer_label = tk.Label(
            meter, text='00:00',
            font=self.FONT_TIMER, bg=self.BG, fg=self.CYAN_BRIGHT,
        )
        self.timer_label.pack()
        status_row = tk.Frame(meter, bg=self.BG)
        status_row.pack(pady=(2, 0))
        self.indicator = tk.Canvas(
            status_row, width=12, height=12, bg=self.BG,
            highlightthickness=0,
        )
        self.indicator.pack(side='left', padx=(0, 6))
        self._draw_indicator(self.CYAN)
        self.status_var = tk.StringVar(value='SYSTEM READY')
        tk.Label(
            status_row, textvariable=self.status_var,
            font=self.FONT_STATUS, bg=self.BG, fg=self.TEXT_DIM,
        ).pack(side='left')

        btn_frame = tk.Frame(self.root, bg=self.BG)
        btn_frame.pack(pady=(4, 16))
        self._rec_btn = self._build_button(
            btn_frame, '● RECORD', self._toggle_record, kind='primary'
        )
        self._rec_btn.pack(side='left', padx=4)
        self._voice_btn = self._build_button(
            btn_frame, '◉ VOICE ON', self._toggle_voice,
            kind='primary', width=128,
        )
        self._voice_btn.pack(side='left', padx=4)
        self._build_button(
            btn_frame, '▶ PLAY', self._play_selected, kind='ghost'
        ).pack(side='left', padx=4)
        self._build_button(
            btn_frame, '◈ TRANSCRIBE', self._stt_selected, kind='primary'
        ).pack(side='left', padx=4)
        self._build_button(
            btn_frame, '◈ ALL', self._stt_all,
            kind='ghost', width=90,
        ).pack(side='left', padx=4)
        self._build_button(
            btn_frame, '⤓ BACKUP', self._do_backup, kind='ghost'
        ).pack(side='left', padx=4)
        self._build_button(
            btn_frame, '⌖ STATS', self._show_stats, kind='ghost'
        ).pack(side='left', padx=4)

        # LIVE TRANSCRIPT 패널
        live_wrap = tk.Frame(self.root, bg=self.BG)
        live_wrap.pack(fill='x', padx=24, pady=(0, 12))
        tk.Label(
            live_wrap, text='LIVE TRANSCRIPT',
            font=self.FONT_LABEL, bg=self.BG, fg=self.CYAN_DIM,
        ).pack(anchor='w')
        live_panel = tk.Frame(
            live_wrap, bg=self.PANEL,
            highlightthickness=1, highlightbackground=self.BORDER,
        )
        live_panel.pack(fill='x', pady=(4, 0))
        self.live_text = tk.Text(
            live_panel, height=5, font=self.FONT_LIST,
            bg=self.PANEL, fg=self.CYAN_BRIGHT,
            insertbackground=self.CYAN, relief='flat',
            bd=0, highlightthickness=0, wrap='word', state='disabled',
            padx=10, pady=8,
        )
        self.live_text.pack(fill='x')

        archive = tk.Frame(self.root, bg=self.BG)
        archive.pack(fill='both', expand=True, padx=24, pady=(0, 16))
        tk.Label(
            archive, text='ARCHIVE',
            font=self.FONT_LABEL, bg=self.BG, fg=self.CYAN_DIM,
        ).pack(anchor='w')

        search_frame = tk.Frame(archive, bg=self.BG)
        search_frame.pack(fill='x', pady=(6, 6))
        tk.Label(
            search_frame, text='▸', font=self.FONT_LABEL,
            bg=self.BG, fg=self.CYAN,
        ).pack(side='left', padx=(0, 4))
        self.search_var = tk.StringVar()
        entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            font=self.FONT_LIST, bg=self.SURFACE, fg=self.TEXT,
            insertbackground=self.CYAN, relief='flat', width=28,
            highlightthickness=1, highlightbackground=self.BORDER,
            highlightcolor=self.CYAN,
        )
        entry.pack(side='left', padx=(0, 10), ipady=5)
        entry.bind('<Return>', lambda _e: self._do_search())

        tk.Radiobutton(
            search_frame, text='MEMO', variable=self.search_mode,
            value='memo', font=self.FONT_SUB, bg=self.BG, fg=self.TEXT_DIM,
            selectcolor=self.BG, activebackground=self.BG,
            activeforeground=self.CYAN, bd=0, highlightthickness=0,
        ).pack(side='left')
        tk.Radiobutton(
            search_frame, text='STT', variable=self.search_mode,
            value='stt', font=self.FONT_SUB, bg=self.BG, fg=self.TEXT_DIM,
            selectcolor=self.BG, activebackground=self.BG,
            activeforeground=self.CYAN, bd=0, highlightthickness=0,
        ).pack(side='left', padx=(0, 10))

        self._build_button(
            search_frame, 'SEARCH', self._do_search,
            kind='primary', width=92,
        ).pack(side='left', padx=2)
        self._build_button(
            search_frame, 'RESET', self._refresh_list,
            kind='ghost', width=80,
        ).pack(side='left', padx=2)

        list_wrap = tk.Frame(
            archive, bg=self.PANEL,
            highlightthickness=1, highlightbackground=self.BORDER,
        )
        list_wrap.pack(fill='both', expand=True)
        scrollbar = tk.Scrollbar(list_wrap, orient='vertical')
        scrollbar.pack(side='right', fill='y')
        self.listbox = tk.Listbox(
            list_wrap, font=self.FONT_LIST,
            bg=self.PANEL, fg=self.TEXT,
            selectbackground=self.SURFACE_HI,
            selectforeground=self.CYAN_BRIGHT,
            relief='flat', yscrollcommand=scrollbar.set,
            activestyle='none', bd=0, highlightthickness=0,
        )
        self.listbox.pack(fill='both', expand=True, padx=8, pady=6)
        scrollbar.config(command=self.listbox.yview)

    def _draw_indicator(self, color):
        """상태 인디케이터 점을 그린다."""
        self.indicator.delete('all')
        self.indicator.create_oval(
            2, 2, 10, 10, fill=color, outline=color,
        )

    def _draw_waveform(self):
        """미러 파형 + 그리드 + 스캔라인을 그린다."""
        self.canvas.delete('all')
        w = self.canvas.winfo_width() or self.WAVE_W
        h = self.WAVE_H
        mid = h // 2
        for gy in (mid - 40, mid - 20, mid + 20, mid + 40):
            self.canvas.create_line(0, gy, w, gy, fill=self.GRID)
        for gx in range(0, w, 60):
            self.canvas.create_line(gx, 0, gx, h, fill=self.GRID)
        self.canvas.create_line(0, mid, w, mid, fill=self.CYAN_DIM)
        n = len(self.waveform_data)
        step = w / n
        for i, val in enumerate(self.waveform_data):
            x = i * step
            bar = int(abs(val) * (mid - 8) * 1.1)
            if bar < 1:
                bar = 1
            color = self.CYAN_BRIGHT if bar > mid * 0.6 else self.CYAN
            self.canvas.create_line(
                x, mid - bar, x, mid + bar, fill=color, width=2,
            )
        if self.is_recording:
            sx = self._scan_x % w
            self.canvas.create_line(
                sx, 0, sx, h, fill=self.CYAN_BRIGHT,
            )
        self._draw_brackets(self.canvas, 4, 4, w - 4, h - 4, size=12)

    def _refresh_list(self):
        """파일 목록을 DB에서 불러와 갱신한다."""
        self.listbox.delete(0, 'end')
        sync_db()
        rows = query_recordings()
        for filename, _, duration, has_memo, has_stt in rows:
            tags = []
            if has_memo:
                tags.append('MEMO')
            if has_stt:
                tags.append('STT')
            tag_str = '  '.join(f'[{t}]' for t in tags)
            line = (
                f'  ▸ {filename}   {format_duration(duration)}'
                f'   {tag_str}'
            )
            self.listbox.insert('end', line)
        self.status_var.set(f'{len(rows)} FILE(S) INDEXED')

    def _animate(self):
        """녹음 중 인디케이터 펄스와 스캔라인을 갱신한다."""
        self._pulse_phase = (self._pulse_phase + 1) % 30
        if self.is_recording:
            color = self.RED if self._pulse_phase < 15 else '#330000'
            self._draw_indicator(color)
            self._scan_x += 8
            self._draw_waveform()
        self.root.after(60, self._animate)

    def _toggle_record(self):
        """녹음 시작과 중지를 전환한다."""
        if self.is_recording:
            self.is_recording = False
            self._set_button_kind(self._rec_btn, '● RECORD', 'primary')
            return
        # 녹음 시작 전, 음성 리스너가 마이크를 잡고 있으면 해제
        self._stop_voice_listener()
        self.is_recording = True
        self.record_frames = []
        self.elapsed_secs = 0
        self._scan_x = 0
        self._clear_live_text()
        self._set_button_kind(self._rec_btn, '■ STOP', 'danger')
        threading.Thread(target=self._record_worker, daemon=True).start()
        threading.Thread(target=self._timer_worker, daemon=True).start()
        threading.Thread(
            target=self._live_transcribe_worker, daemon=True
        ).start()
        self.status_var.set('RECORDING IN PROGRESS')

    def _record_worker(self):
        """백그라운드 녹음 스레드 함수."""
        audio = create_pyaudio()
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        while self.is_recording:
            data = stream.read(CHUNK)
            self.record_frames.append(data)
            self._update_waveform(data)
        stream.stop_stream()
        stream.close()
        self.record_sample_width = audio.get_sample_size(FORMAT)
        audio.terminate()
        if self.record_frames:
            self.root.after(0, self._save_after_record)

    def _timer_worker(self):
        """녹음 경과 시간을 업데이트하는 스레드 함수."""
        while self.is_recording:
            time.sleep(1)
            self.elapsed_secs += 1
            display = format_duration(self.elapsed_secs)
            self.root.after(
                0, lambda d=display: self.timer_label.config(text=d)
            )

    def _update_waveform(self, data):
        """오디오 청크를 파형 데이터로 변환하여 갱신한다."""
        num_samples = len(data) // 2
        if num_samples == 0:
            return
        samples = struct.unpack(f'{num_samples}h', data)
        peak = max(abs(s) for s in samples) / 32768.0
        self.waveform_data.pop(0)
        self.waveform_data.append(peak)
        self.root.after(0, self._draw_waveform)

    def _save_after_record(self):
        """녹음 완료 후 파일을 저장하고 목록을 갱신한다."""
        _, filename = save_recording(
            self.record_frames, self.record_sample_width
        )
        self.timer_label.config(text='00:00')
        self.waveform_data = [0.0] * 220
        self._draw_waveform()
        self._draw_indicator(self.CYAN)
        self.status_var.set(f'ARCHIVED  ::  {filename}')
        self._refresh_list()
        # 음성 명령이 활성화 상태였다면 다시 리스너 시작
        if self.voice_enabled:
            self._start_voice_listener()

    def _selected_filename(self):
        """리스트박스에서 선택된 파일명을 반환한다."""
        selection = self.listbox.curselection()
        if not selection:
            return None
        line = self.listbox.get(selection[0]).strip()
        for part in line.split():
            if part.endswith('.wav'):
                return part
        return None

    def _play_selected(self):
        """선택된 파일을 재생한다."""
        filename = self._selected_filename()
        if not filename:
            self.status_var.set('SELECT A FILE FIRST')
            return
        filepath = os.path.join(RECORDS_DIR, filename)
        self.status_var.set(f'PLAYBACK  ::  {filename}')
        threading.Thread(
            target=play_recording, args=(filepath,), daemon=True
        ).start()

    def _stt_selected(self):
        """선택된 파일에 대해 STT를 실행한다."""
        filename = self._selected_filename()
        if not filename:
            self.status_var.set('SELECT A FILE FIRST')
            return
        self.status_var.set(f'TRANSCRIBING  ::  {filename}')
        self._draw_indicator(self.GOLD)
        threading.Thread(
            target=self._stt_worker, args=(filename,), daemon=True
        ).start()

    def _stt_worker(self, filename):
        """STT 백그라운드 스레드 함수."""
        try:
            csv_path, results = run_stt_on_file(filename)
        except Exception as exc:
            logger.exception('STT 실패: %s', filename)
            err = str(exc)
            self.root.after(0, lambda: self._on_stt_error(err))
            return
        if csv_path is None:
            self.root.after(
                0, lambda: self._on_stt_error(f'NOT FOUND: {filename}')
            )
            return
        msg = f'TRANSCRIBED  ::  {filename}  ({len(results)} SEGMENTS)'
        self.root.after(0, lambda: self._on_stt_done(msg))

    def _on_stt_error(self, message):
        """STT 실패 시 UI 갱신."""
        self.status_var.set(f'TRANSCRIBE FAILED  ::  {message}')
        self._draw_indicator(self.RED)

    def _on_stt_done(self, message):
        """STT 성공 시 UI 갱신."""
        self.status_var.set(message)
        self._draw_indicator(self.CYAN)
        self._refresh_list()

    def _stt_all(self):
        """모든 파일에 대해 STT를 실행한다."""
        self.status_var.set('BATCH TRANSCRIBE IN PROGRESS')
        self._draw_indicator(self.GOLD)
        threading.Thread(target=self._stt_all_worker, daemon=True).start()

    def _stt_all_worker(self):
        """STT 일괄 처리 스레드."""
        try:
            summary = run_stt_on_all()
        except Exception as exc:
            logger.exception('STT 일괄 처리 실패')
            err = str(exc)
            self.root.after(
                0, lambda: self._on_stt_error(f'BATCH :: {err}')
            )
            return
        count = len(summary)
        msg = f'BATCH COMPLETE  ::  {count} FILE(S) PROCESSED'
        self.root.after(0, lambda: self._on_stt_done(msg))

    def _do_search(self):
        """선택된 모드에 따라 메모 또는 STT CSV에서 검색한다."""
        keyword = self.search_var.get().strip()
        if not keyword:
            self._refresh_list()
            return
        mode = self.search_mode.get()
        self.listbox.delete(0, 'end')
        if mode == 'stt':
            results = search_transcripts(keyword)
            for filename, time_str, text in results:
                self.listbox.insert(
                    'end',
                    f'  ▸ {filename}   [{time_str}]   >> {text}',
                )
            label = 'STT'
        else:
            results = search_memos(keyword)
            for filename, matched_line in results:
                self.listbox.insert(
                    'end', f'  ▸ {filename}   >> {matched_line}'
                )
            label = 'MEMO'
        count = len(results)
        self.status_var.set(
            f'QUERY  ::  {count} {label} MATCH(ES) FOR "{keyword}"'
        )

    def _do_backup(self):
        """백업을 실행하고 결과를 상태 바에 표시한다."""
        backup_path = backup_recordings()
        self.status_var.set(f'BACKUP ARCHIVED  ::  {backup_path}')

    def _show_stats(self):
        """통계 정보를 팝업으로 표시한다."""
        stats = get_recording_stats()
        if not stats:
            messagebox.showinfo('JARVIS STATS', '녹음 파일이 없습니다.')
            return
        msg = (
            f'총 녹음 수   : {stats["count"]}개\n'
            f'총 녹음 시간 : {format_duration(stats["total"])}\n'
            f'평균 길이    : {format_duration(stats["mean"])}\n'
            f'중간값       : {format_duration(stats["median"])}\n'
            f'표준편차     : {format_duration(stats["stdev"])}'
        )
        messagebox.showinfo('JARVIS STATS', msg)

    # ── 실시간 자막 ───────────────────────────────────────
    def _clear_live_text(self):
        """실시간 자막 패널을 비운다."""
        self.live_lines = []
        if self.live_text is None:
            return
        self.live_text.config(state='normal')
        self.live_text.delete('1.0', 'end')
        self.live_text.config(state='disabled')

    def _on_live_text(self, timestamp, text):
        """실시간 STT 텍스트를 패널에 추가한다."""
        self.live_lines.append(f'[{timestamp}]  {text}')
        if len(self.live_lines) > self.MAX_LIVE_LINES:
            self.live_lines = self.live_lines[-self.MAX_LIVE_LINES:]
        if self.live_text is None:
            return
        self.live_text.config(state='normal')
        self.live_text.delete('1.0', 'end')
        self.live_text.insert('1.0', '\n'.join(self.live_lines))
        self.live_text.see('end')
        self.live_text.config(state='disabled')

    def _transcribe_segment(self, recognizer, segment):
        """frames 한 토막을 임시 WAV로 만들고 STT 텍스트를 반환한다."""
        if not segment:
            return ''
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix='.wav', delete=False
            ) as tmp:
                tmp_path = tmp.name
            with wave.open(tmp_path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.record_sample_width)
                wf.setframerate(RATE)
                wf.writeframes(b''.join(segment))
            with sr.AudioFile(tmp_path) as src:
                audio = recognizer.record(src)
            return recognizer.recognize_google(
                audio, language=STT_LANGUAGE
            ).strip()
        except (sr.UnknownValueError, sr.RequestError):
            return ''
        except Exception as exc:
            logger.warning('실시간 STT 실패: %s', exc)
            return ''
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def _live_transcribe_worker(self):
        """녹음 중 일정 구간마다 STT를 수행한다."""
        recognizer = sr.Recognizer()
        chunks_per_second = max(1, RATE // CHUNK)
        segment_chunks = chunks_per_second * self.LIVE_SEGMENT_SECONDS
        last_processed = 0
        while self.is_recording:
            time.sleep(0.5)
            current = len(self.record_frames)
            if current - last_processed < segment_chunks:
                continue
            segment = self.record_frames[last_processed:current]
            offset_secs = last_processed * CHUNK / RATE
            last_processed = current
            text = self._transcribe_segment(recognizer, segment)
            if not text:
                continue
            ts = format_duration(int(offset_secs))
            self.root.after(
                0, lambda t=text, s=ts: self._on_live_text(s, t)
            )
            if self.voice_enabled and any(
                k in text.lower() for k in self.VOICE_STOP_KEYWORDS
            ):
                self.root.after(0, self._voice_stop_record)

    # ── 음성 명령 ─────────────────────────────────────────
    def _toggle_voice(self):
        """음성 명령 모드를 토글한다."""
        self.voice_enabled = not self.voice_enabled
        if self.voice_enabled:
            self._set_button_kind(
                self._voice_btn, '◉ VOICE ON', 'primary'
            )
            if not self.is_recording:
                self._start_voice_listener()
            self.status_var.set(
                'VOICE CONTROL ACTIVE  ::  SAY "시작" TO RECORD'
            )
        else:
            self._set_button_kind(
                self._voice_btn, '◉ VOICE OFF', 'ghost'
            )
            self._stop_voice_listener()
            self.status_var.set('VOICE CONTROL DEACTIVATED')

    def _start_voice_listener(self):
        """음성 명령 백그라운드 리스너를 시작한다."""
        if self.voice_listener_stop is not None:
            return
        threading.Thread(
            target=self._voice_listener_setup, daemon=True
        ).start()

    def _voice_listener_setup(self):
        """리스너를 셋업하고 listen_in_background로 등록한다."""
        self.root.after(
            0,
            lambda: self.status_var.set(
                'VOICE LISTENER INITIALIZING...'
            ),
        )
        try:
            mic = sr.Microphone()
            recognizer = sr.Recognizer()
            recognizer.pause_threshold = 0.6
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
        except Exception as exc:
            logger.warning('음성 명령 리스너 초기화 실패: %s', exc)
            err = str(exc)
            self.root.after(
                0,
                lambda: self.status_var.set(
                    f'VOICE LISTENER ERROR  ::  {err}'
                ),
            )
            return

        def callback(_rec, audio):
            if not self.voice_enabled or self.is_recording:
                return
            try:
                text = recognizer.recognize_google(
                    audio, language=STT_LANGUAGE
                )
            except sr.UnknownValueError:
                return
            except sr.RequestError as exc:
                logger.warning('STT 요청 실패: %s', exc)
                return
            text = text.strip()
            if not text:
                return
            logger.info('음성 인식: %s', text)
            # 인식된 모든 텍스트를 LIVE 패널에 표시 (디버깅용)
            self.root.after(
                0,
                lambda t=text: self._on_live_text('HEARD', t),
            )
            if any(k in text.lower() for k in self.VOICE_START_KEYWORDS):
                self.root.after(0, self._voice_start_record)

        try:
            self.voice_listener_stop = recognizer.listen_in_background(
                mic, callback, phrase_time_limit=4
            )
            self.root.after(
                0,
                lambda: self.status_var.set(
                    'VOICE LISTENER READY  ::  SAY "시작" TO RECORD'
                ),
            )
            self.root.after(0, lambda: self._draw_indicator(self.CYAN))
        except Exception as exc:
            logger.warning('백그라운드 리스너 등록 실패: %s', exc)
            err = str(exc)
            self.root.after(
                0,
                lambda: self.status_var.set(
                    f'VOICE LISTENER FAILED  ::  {err}'
                ),
            )

    def _stop_voice_listener(self):
        """음성 명령 리스너를 중지한다."""
        if self.voice_listener_stop is None:
            return
        try:
            self.voice_listener_stop(wait_for_stop=False)
        except Exception:
            pass
        self.voice_listener_stop = None

    def _voice_start_record(self):
        """음성 명령으로 녹음을 시작한다."""
        if self.is_recording:
            return
        self.status_var.set('VOICE COMMAND  ::  START')
        self._toggle_record()

    def _voice_stop_record(self):
        """음성 명령으로 녹음을 중지한다."""
        if not self.is_recording:
            return
        self.status_var.set('VOICE COMMAND  ::  STOP')
        self._toggle_record()


# ── CLI 모드 ──────────────────────────────────────────────
def cli_record():
    """CLI에서 녹음을 실행한다."""
    list_microphones()
    print('녹음을 시작합니다. 종료하려면 Ctrl+C를 누르세요.')
    elapsed = [0]
    stop_event = threading.Event()

    def timer_worker():
        while not stop_event.is_set():
            time.sleep(1)
            elapsed[0] += 1
            display = format_duration(elapsed[0])
            print(f'\r  경과: {display}', end='', flush=True)

    threading.Thread(target=timer_worker, daemon=True).start()
    frames, sample_width = record_audio()
    stop_event.set()
    print()
    if not frames:
        print('녹음된 데이터가 없습니다.')
        return
    filepath, _ = save_recording(frames, sample_width)
    answer = input('메모를 추가하시겠습니까? (y/n): ').strip().lower()
    if answer == 'y':
        add_memo(filepath)


def cli_list(start_str=None, end_str=None):
    """CLI에서 녹음 목록을 출력한다."""
    sync_db()
    start_date = None
    end_date = None
    if start_str and end_str:
        try:
            start_date = datetime.datetime.strptime(
                start_str, '%Y%m%d'
            ).date()
            end_date = datetime.datetime.strptime(
                end_str, '%Y%m%d'
            ).date()
        except ValueError:
            print('날짜 형식이 올바르지 않습니다. YYYYMMDD 형식을 사용해 주세요.')
            return
    rows = query_recordings(start_date, end_date)
    if not rows:
        print('녹음 파일이 없습니다.')
        return
    for filename, _, duration, has_memo, has_stt in rows:
        marks = ''
        if has_memo:
            marks += ' [메모]'
        if has_stt:
            marks += ' [STT]'
        print(f'  {filename}  {format_duration(duration)}{marks}')


def cli_search(keyword):
    """CLI에서 메모 키워드 검색을 실행한다."""
    results = search_memos(keyword)
    if not results:
        print(f'"{keyword}"에 대한 결과가 없습니다.')
        return
    for filename, matched_line in results:
        print(f'  {filename}: {matched_line}')


def cli_stats():
    """CLI에서 녹음 통계를 출력한다."""
    sync_db()
    stats = get_recording_stats()
    if not stats:
        print('녹음 파일이 없습니다.')
        return
    print(f'  총 녹음 수   : {stats["count"]}개')
    print(f'  총 녹음 시간 : {format_duration(stats["total"])}')
    print(f'  평균 길이    : {format_duration(stats["mean"])}')
    print(f'  중간값       : {format_duration(stats["median"])}')
    print(f'  표준편차     : {format_duration(stats["stdev"])}')


def cli_backup():
    """CLI에서 백업을 실행한다."""
    backup_path = backup_recordings()
    print(f'백업이 완료되었습니다: {backup_path}')


def cli_stt(filename=None):
    """CLI에서 STT를 실행한다."""
    ensure_records_dir()
    sync_db()
    if filename:
        targets = [filename]
    else:
        targets = get_wav_files()
    if not targets:
        print('녹음 파일이 없습니다.')
        return
    for name in targets:
        filepath = os.path.join(RECORDS_DIR, name)
        if not os.path.exists(filepath):
            print(f'파일을 찾을 수 없습니다: {name}')
            continue
        print(f'STT 처리 중: {name}')
        try:
            csv_path, results = run_stt_on_file(name)
        except Exception as exc:
            print(f'  실패: {exc}')
            logger.exception('STT 실패: %s', name)
            continue
        print(f'  -> {len(results)}개 구간 인식, 저장: {csv_path}')
        for time_str, text in results:
            print(f'     {time_str}  {text}')


def cli_search_text(keyword):
    """CLI에서 CSV(STT 결과) 안의 키워드를 검색한다."""
    results = search_transcripts(keyword)
    if not results:
        print(f'"{keyword}"에 대한 결과가 없습니다.')
        return
    for filename, time_str, text in results:
        print(f'  {filename} [{time_str}] {text}')


# ── 진입점 ────────────────────────────────────────────────
def main():
    """argparse로 CLI / GUI 모드를 분기하는 메인 함수."""
    init_db()
    sync_db()

    parser = argparse.ArgumentParser(
        prog='javis',
        description='J.A.R.V.I.S 음성 녹음 및 STT 시스템',
    )
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('record', help='음성 녹음 (CLI)')
    sub.add_parser('gui', help='GUI 실행 (기본값)')
    sub.add_parser('stats', help='녹음 통계 출력')
    sub.add_parser('backup', help='녹음 파일 백업')

    list_parser = sub.add_parser('list', help='녹음 파일 목록')
    list_parser.add_argument(
        '--from', dest='start', metavar='YYYYMMDD', default=None
    )
    list_parser.add_argument(
        '--to', dest='end', metavar='YYYYMMDD', default=None
    )

    search_parser = sub.add_parser('search', help='메모 키워드 검색')
    search_parser.add_argument('keyword')

    stt_parser = sub.add_parser(
        'stt', help='음성을 텍스트로 변환하여 CSV로 저장'
    )
    stt_parser.add_argument(
        'filename', nargs='?', default=None,
        help='특정 WAV 파일명 (생략 시 전체 처리)',
    )

    search_text_parser = sub.add_parser(
        'search-text', help='STT CSV 안에서 키워드 검색 (보너스)'
    )
    search_text_parser.add_argument('keyword')

    args = parser.parse_args()

    if args.command == 'record':
        cli_record()
    elif args.command == 'list':
        cli_list(args.start, args.end)
    elif args.command == 'search':
        cli_search(args.keyword)
    elif args.command == 'stats':
        cli_stats()
    elif args.command == 'backup':
        cli_backup()
    elif args.command == 'stt':
        cli_stt(args.filename)
    elif args.command == 'search-text':
        cli_search_text(args.keyword)
    else:
        root = tk.Tk()
        JarvisGui(root)
        root.mainloop()


if __name__ == '__main__':
    main()
