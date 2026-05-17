"""javis.py - J.A.R.V.I.S 음성 녹음 및 관리 시스템."""

import os
import re
import time
import wave
import struct
import logging
import sqlite3
import zipfile
import shutil
import datetime
import platform
import argparse
import threading
import statistics
import subprocess
import configparser
import tkinter as tk
from tkinter import messagebox
import pyaudio


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
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    config.read(CONFIG_FILE, encoding='utf-8')
    return config


CONFIG = load_config()
RECORDS_DIR = CONFIG['paths']['records_dir']
LOG_FILE = CONFIG['paths']['log_file']
DB_FILE = CONFIG['paths']['db_file']
CHUNK = int(CONFIG['audio']['chunk'])
FORMAT = pyaudio.paInt16
CHANNELS = int(CONFIG['audio']['channels'])
RATE = int(CONFIG['audio']['rate'])


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
            has_memo    INTEGER DEFAULT 0
        )
    ''')
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
        cursor.execute(
            'SELECT id FROM recordings WHERE filename = ?', (filename,)
        )
        if cursor.fetchone():
            continue
        filepath = os.path.join(RECORDS_DIR, filename)
        try:
            info = get_wav_info(filepath)
            memo_path = filepath.replace('.wav', '.txt')
            has_memo = 1 if os.path.exists(memo_path) else 0
            parts = filename.replace('.wav', '').split('-')
            recorded_at = datetime.datetime.strptime(
                parts[0] + parts[1], '%Y%m%d%H%M%S'
            ).isoformat()
            cursor.execute('''
                INSERT INTO recordings
                    (filename, recorded_at, duration,
                     sample_rate, channels, bit_depth, has_memo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename, recorded_at, info['duration'],
                info['sample_rate'], info['channels'],
                info['sample_width'], has_memo,
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
             sample_rate, channels, bit_depth, has_memo)
        VALUES (?, ?, ?, ?, ?, ?, 0)
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


def query_recordings(start_date=None, end_date=None):
    """DB에서 녹음 목록을 조회하여 반환한다.

    Args:
        start_date (datetime.date): 조회 시작 날짜 (선택).
        end_date (datetime.date): 조회 종료 날짜 (선택).

    Returns:
        list: (filename, recorded_at, duration, has_memo) 튜플 목록.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    sql = '''
        SELECT filename, recorded_at, duration, has_memo
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
    """WAV 파일의 메타데이터를 반환한다.

    Args:
        filepath (str): WAV 파일 경로.

    Returns:
        dict: duration, channels, sample_rate, sample_width 정보.
    """
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
    """시스템 마이크를 인식하고 음성을 녹음한다.

    Args:
        on_chunk (callable): 청크마다 호출되는 콜백 (bytes → None).

    Returns:
        tuple: (frames, sample_width)
    """
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
    """녹음된 데이터를 WAV 파일로 저장하고 DB에 등록한다.

    Args:
        frames (list): 녹음된 오디오 데이터 프레임 목록.
        sample_width (int): 오디오 샘플의 바이트 너비.

    Returns:
        tuple: (filepath, filename)
    """
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


# ── 검색 (re) ─────────────────────────────────────────────
def search_memos(keyword):
    """메모 파일에서 키워드(정규식 지원)를 검색한다.

    Args:
        keyword (str): 검색할 키워드 또는 정규식 패턴.

    Returns:
        list: (filename, matched_line) 튜플 목록.
    """
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


# ── 통계 (statistics) ─────────────────────────────────────
def get_recording_stats():
    """녹음 파일의 통계 정보를 반환한다.

    Returns:
        dict: count, total, mean, median, stdev 정보. 없으면 None.
    """
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


# ── 백업 (zipfile + shutil) ───────────────────────────────
def backup_recordings():
    """records 디렉토리를 ZIP 파일로 백업한다.

    Returns:
        str: 생성된 백업 파일 경로.
    """
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
    """자비스 홀로그램 스타일 tkinter GUI."""

    BG = '#000000'
    FG = '#00FFAA'
    ACCENT = '#00CCFF'
    DIM = '#004433'
    FONT_TITLE = ('Courier', 15, 'bold')
    FONT_MAIN = ('Courier', 11)
    FONT_SMALL = ('Courier', 9)

    def __init__(self, root):
        self.root = root
        self.root.title('J.A.R.V.I.S')
        self.root.configure(bg=self.BG)
        self.root.geometry('900x640')
        self.is_recording = False
        self.record_frames = []
        self.record_sample_width = 2
        self.elapsed_secs = 0
        self.waveform_data = [0.0] * 200
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        """UI 컴포넌트를 구성한다."""
        tk.Label(
            self.root,
            text='[ J.A.R.V.I.S  AUDIO SYSTEM ]',
            font=self.FONT_TITLE, bg=self.BG, fg=self.ACCENT,
        ).pack(pady=(14, 0))

        self.canvas = tk.Canvas(
            self.root, width=860, height=90,
            bg=self.BG, highlightthickness=1,
            highlightbackground=self.DIM,
        )
        self.canvas.pack(padx=20, pady=(10, 0))
        self._draw_waveform()

        self.timer_label = tk.Label(
            self.root, text='00:00',
            font=('Courier', 22, 'bold'), bg=self.BG, fg=self.FG,
        )
        self.timer_label.pack(pady=(4, 0))

        btn_frame = tk.Frame(self.root, bg=self.BG)
        btn_frame.pack(pady=6)
        self._make_btn(btn_frame, '[ REC ]', self._toggle_record, self.ACCENT)
        self._make_btn(btn_frame, '[ PLAY ]', self._play_selected, self.FG)
        self._make_btn(btn_frame, '[ BACKUP ]', self._do_backup, self.FG)
        self._make_btn(btn_frame, '[ STATS ]', self._show_stats, self.FG)

        search_frame = tk.Frame(self.root, bg=self.BG)
        search_frame.pack(fill='x', padx=20, pady=(4, 0))
        tk.Label(
            search_frame, text='SEARCH >',
            font=self.FONT_SMALL, bg=self.BG, fg=self.DIM,
        ).pack(side='left')
        self.search_var = tk.StringVar()
        entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            font=self.FONT_MAIN, bg='#001a11', fg=self.FG,
            insertbackground=self.FG, relief='flat', width=30,
        )
        entry.pack(side='left', padx=6)
        entry.bind('<Return>', lambda _e: self._do_search())
        self._make_btn(
            search_frame, '[ GO ]', self._do_search, self.FG, side='left'
        )
        self._make_btn(
            search_frame, '[ RESET ]', self._refresh_list, self.DIM,
            side='left',
        )

        list_frame = tk.Frame(self.root, bg=self.BG)
        list_frame.pack(fill='both', expand=True, padx=20, pady=8)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical')
        scrollbar.pack(side='right', fill='y')
        self.listbox = tk.Listbox(
            list_frame, font=self.FONT_MAIN,
            bg='#001a11', fg=self.FG,
            selectbackground=self.DIM, selectforeground=self.ACCENT,
            relief='flat', yscrollcommand=scrollbar.set, activestyle='none',
        )
        self.listbox.pack(fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)

        self.status_var = tk.StringVar(value='SYSTEM READY')
        tk.Label(
            self.root, textvariable=self.status_var,
            font=self.FONT_SMALL, bg='#001a11', fg=self.DIM, anchor='w',
        ).pack(fill='x', padx=20, pady=(0, 10))

    def _make_btn(self, parent, text, cmd, color, side='left'):
        """스타일이 적용된 버튼을 생성하여 반환한다."""
        btn = tk.Button(
            parent, text=text, command=cmd,
            font=self.FONT_MAIN, bg=self.BG, fg=color,
            activebackground=self.DIM, activeforeground=self.ACCENT,
            relief='flat', bd=0, cursor='hand2', padx=10,
        )
        btn.pack(side=side, padx=4)
        return btn

    def _draw_waveform(self):
        """캔버스에 실시간 파형을 그린다."""
        self.canvas.delete('wave')
        canvas_w = 860
        canvas_h = 90
        mid = canvas_h // 2
        step = canvas_w / len(self.waveform_data)
        for i, val in enumerate(self.waveform_data):
            x = i * step
            bar_h = int(abs(val) * mid * 0.9)
            color = self.ACCENT if bar_h > mid * 0.5 else self.FG
            self.canvas.create_line(
                x, mid - bar_h, x, mid + bar_h,
                fill=color, tags='wave',
            )

    def _refresh_list(self):
        """파일 목록을 DB에서 불러와 갱신한다."""
        self.listbox.delete(0, 'end')
        sync_db()
        rows = query_recordings()
        for filename, _, duration, has_memo in rows:
            memo_mark = ' [M]' if has_memo else ''
            line = f'  {filename}  {format_duration(duration)}{memo_mark}'
            self.listbox.insert('end', line)
        self.status_var.set(f'{len(rows)} FILE(S) INDEXED')

    def _toggle_record(self):
        """녹음 시작과 중지를 전환한다."""
        if self.is_recording:
            self.is_recording = False
            return
        self.is_recording = True
        self.record_frames = []
        self.elapsed_secs = 0
        threading.Thread(target=self._record_worker, daemon=True).start()
        threading.Thread(target=self._timer_worker, daemon=True).start()
        self.status_var.set('RECORDING...')

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
        self.waveform_data = [0.0] * 200
        self._draw_waveform()
        self.status_var.set(f'SAVED: {filename}')
        self._refresh_list()

    def _play_selected(self):
        """선택된 파일을 재생한다."""
        selection = self.listbox.curselection()
        if not selection:
            self.status_var.set('SELECT A FILE FIRST')
            return
        filename = self.listbox.get(selection[0]).strip().split()[0]
        filepath = os.path.join(RECORDS_DIR, filename)
        self.status_var.set(f'PLAYING: {filename}')
        threading.Thread(
            target=play_recording, args=(filepath,), daemon=True
        ).start()

    def _do_search(self):
        """메모 키워드 검색을 실행하고 결과를 표시한다."""
        keyword = self.search_var.get().strip()
        if not keyword:
            self._refresh_list()
            return
        results = search_memos(keyword)
        self.listbox.delete(0, 'end')
        for filename, matched_line in results:
            self.listbox.insert('end', f'  {filename}  >> {matched_line}')
        self.status_var.set(f'{len(results)} RESULT(S) FOR "{keyword}"')

    def _do_backup(self):
        """백업을 실행하고 결과를 상태 바에 표시한다."""
        backup_path = backup_recordings()
        self.status_var.set(f'BACKUP: {backup_path}')

    def _show_stats(self):
        """통계 정보를 팝업으로 표시한다."""
        stats = get_recording_stats()
        if not stats:
            messagebox.showinfo('Stats', '녹음 파일이 없습니다.')
            return
        msg = (
            f'총 녹음 수   : {stats["count"]}개\n'
            f'총 녹음 시간 : {format_duration(stats["total"])}\n'
            f'평균 길이    : {format_duration(stats["mean"])}\n'
            f'중간값       : {format_duration(stats["median"])}\n'
            f'표준편차     : {format_duration(stats["stdev"])}'
        )
        messagebox.showinfo('JARVIS STATS', msg)


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
    for filename, _, duration, has_memo in rows:
        memo_mark = ' [메모]' if has_memo else ''
        print(f'  {filename}  {format_duration(duration)}{memo_mark}')


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


# ── 진입점 ────────────────────────────────────────────────
def main():
    """argparse로 CLI / GUI 모드를 분기하는 메인 함수."""
    init_db()
    sync_db()

    parser = argparse.ArgumentParser(
        prog='javis',
        description='J.A.R.V.I.S 음성 녹음 시스템',
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
    else:
        root = tk.Tk()
        JarvisGui(root)
        root.mainloop()


if __name__ == '__main__':
    main()
