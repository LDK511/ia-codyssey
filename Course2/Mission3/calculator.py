import sys
import os
import math
import random
import warnings

warnings.filterwarnings('ignore')  # 제약조건: 경고 메시지 없이 실행

# PyQt5 플랫폼 플러그인 경로 설정
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'venv', 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins', 'platforms'
)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeyEvent

GAP = 8


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.current_input = '0'
        self.first_operand = None
        self.operator = None
        self.reset_next = False
        self.is_landscape = False
        self.use_deg = True
        self.memory = 0           # 메모리 저장값
        self.pending_pow = False  # xʸ 대기 상태
        self.pending_root = False # ʸ√x 대기 상태
        self.ee_mode = False      # EE 입력 상태
        self.setWindowTitle('Calculator')
        self.setStyleSheet('background-color: #000000;')
        self._build()
        self._center()

    # ── 레이아웃 구성 ──────────────────────────────────────────────

    def _build(self):
        """레이아웃 전체를 새로 구성한다."""
        old = self.layout()
        if old:
            self._clear_layout(old)
            tmp = QWidget()
            tmp.setLayout(old)

        screen = QApplication.primaryScreen().availableGeometry()
        if self.is_landscape:
            win_w = min(780, screen.width() - 40)
            win_h = min(440, screen.height() - 50)
            disp_h = 80
            rotate_h = 26
            margin_v = 6 + 10
            gap_total = 4 * GAP
            btn_h = max(38, (win_h - disp_h - rotate_h - margin_v - gap_total) // 5)
            disp_font = 44
        else:
            win_w = 320
            win_h = 620
            disp_h = 120
            btn_h = 65
            disp_font = 52

        self.setFixedSize(win_w, win_h)
        self._btn_h = btn_h

        root = QVBoxLayout()
        root.setSpacing(0)
        root.setContentsMargins(12, 6, 12, 10)

        # 디스플레이
        self.display = QLabel(self.current_input)
        self.display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.display.setFont(QFont('Arial', disp_font, QFont.Light))
        self.display.setStyleSheet('color: white; padding: 4px 8px;')
        self.display.setMinimumHeight(disp_h)
        self.display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        root.addWidget(self.display)

        # 회전 버튼 바
        rotate_bar = QHBoxLayout()
        rotate_bar.setContentsMargins(0, 0, 0, 2)
        rotate_bar.addStretch()
        rotate_btn = QPushButton('⟳')
        rotate_btn.setFixedSize(22, 22)
        rotate_btn.setFont(QFont('Arial', 11))
        rotate_btn.setStyleSheet(
            'QPushButton { background-color: #2c2c2e; color: white; border-radius: 11px; }'
            'QPushButton:pressed { background-color: #555; }'
        )
        rotate_btn.clicked.connect(self.toggle_orientation)
        rotate_bar.addWidget(rotate_btn)
        root.addLayout(rotate_bar)

        # 버튼 그리드
        grid = QGridLayout()
        grid.setSpacing(GAP)
        if self.is_landscape:
            self._build_landscape(grid)
        else:
            self._build_portrait(grid)
        root.addLayout(grid)

        self.setLayout(root)

    def _clear_layout(self, layout):
        """레이아웃 안의 위젯/서브레이아웃을 재귀적으로 제거한다."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _center(self):
        """창을 화면 중앙으로 이동한다."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def _build_portrait(self, grid):
        buttons = [
            ('⌫',   0, 0, 'func'), ('AC',  0, 1, 'func'),
            ('%',   0, 2, 'func'), ('÷',   0, 3, 'op'),
            ('7',   1, 0, 'num'),  ('8',   1, 1, 'num'),
            ('9',   1, 2, 'num'),  ('×',   1, 3, 'op'),
            ('4',   2, 0, 'num'),  ('5',   2, 1, 'num'),
            ('6',   2, 2, 'num'),  ('-',   2, 3, 'op'),
            ('1',   3, 0, 'num'),  ('2',   3, 1, 'num'),
            ('3',   3, 2, 'num'),  ('+',   3, 3, 'op'),
            ('+/-', 4, 0, 'func'), ('0',   4, 1, 'num'),
            ('.',   4, 2, 'num'),  ('=',   4, 3, 'op'),
        ]
        for text, row, col, btn_type in buttons:
            btn = self._make_btn(text, btn_type, self._btn_h, 22)
            btn.clicked.connect(lambda checked, t=text: self.on_click(t))
            grid.addWidget(btn, row, col)

    def _build_landscape(self, grid):
        deg_label = 'Deg' if self.use_deg else 'Rad'
        buttons = [
            ('(',      0, 0, 'sci'), (')',     0, 1, 'sci'),
            ('mc',     0, 2, 'sci'), ('m+',   0, 3, 'sci'),
            ('m-',     0, 4, 'sci'), ('mr',   0, 5, 'sci'),
            ('⌫',      0, 6, 'func'), ('AC',  0, 7, 'func'),
            ('%',      0, 8, 'func'), ('÷',   0, 9, 'op'),

            ('2nd',    1, 0, 'sci'), ('x²',   1, 1, 'sci'),
            ('x³',     1, 2, 'sci'), ('xʸ',   1, 3, 'sci'),
            ('eˣ',     1, 4, 'sci'), ('10ˣ',  1, 5, 'sci'),
            ('7',      1, 6, 'num'), ('8',    1, 7, 'num'),
            ('9',      1, 8, 'num'), ('×',    1, 9, 'op'),

            ('¹/x',    2, 0, 'sci'), ('²√x',  2, 1, 'sci'),
            ('³√x',    2, 2, 'sci'), ('ʸ√x',  2, 3, 'sci'),
            ('ln',     2, 4, 'sci'), ('log₁₀', 2, 5, 'sci'),
            ('4',      2, 6, 'num'), ('5',    2, 7, 'num'),
            ('6',      2, 8, 'num'), ('-',    2, 9, 'op'),

            ('x!',     3, 0, 'sci'), ('sin',  3, 1, 'sci'),
            ('cos',    3, 2, 'sci'), ('tan',  3, 3, 'sci'),
            ('e',      3, 4, 'sci'), ('EE',   3, 5, 'sci'),
            ('1',      3, 6, 'num'), ('2',    3, 7, 'num'),
            ('3',      3, 8, 'num'), ('+',    3, 9, 'op'),

            ('Rand',   4, 0, 'sci'), ('sinh', 4, 1, 'sci'),
            ('cosh',   4, 2, 'sci'), ('tanh', 4, 3, 'sci'),
            ('π',      4, 4, 'sci'), (deg_label, 4, 5, 'sci'),
            ('+/-',    4, 6, 'func'), ('0',  4, 7, 'num'),
            ('.',      4, 8, 'num'), ('=',   4, 9, 'op'),
        ]
        for text, row, col, btn_type in buttons:
            fs = 10 if len(text) > 3 else 13
            btn = self._make_btn(text, btn_type, self._btn_h, fs)
            btn.clicked.connect(lambda checked, t=text: self.on_click(t))
            grid.addWidget(btn, row, col)

    def _make_btn(self, text, btn_type, height, font_size):
        btn = QPushButton(text)
        btn.setFixedHeight(height)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setFont(QFont('Arial', font_size))
        r = str(height // 2) + 'px'
        colors = {
            'num':  ('#333333', 'white'),
            'func': ('#505050', 'white'),
            'op':   ('#ff9f0a', 'white'),
            'sci':  ('#1c1c1e', 'white'),
        }
        bg, fg = colors.get(btn_type, ('#333333', 'white'))
        btn.setStyleSheet(
            'QPushButton { background-color: ' + bg + '; color: ' + fg
            + '; border-radius: ' + r + '; }'
            'QPushButton:pressed { background-color: #888; }'
        )
        return btn

    # ── 이벤트 ────────────────────────────────────────────────────

    def toggle_orientation(self):
        self.is_landscape = not self.is_landscape
        self._build()
        self._center()

    def on_click(self, text):
        if text.isdigit():
            self.input_digit(text)
        elif text == '.':
            self.input_dot()
        elif text == 'AC':
            self.clear_all()
        elif text == '⌫':
            self.backspace()
        elif text == '+/-':
            self.toggle_sign()
        elif text == '%':
            self.percent()
        elif text in ('÷', '×', '-', '+'):
            self.input_operator(text)
        elif text == '=':
            self.calculate()
        elif text == 'Rand':
            self.current_input = self.format_num(random.random())
            self.reset_next = True
            self.update_display()
        elif text == 'π':
            self.current_input = self.format_num(math.pi)
            self.reset_next = True
            self.update_display()
        elif text == 'e':
            self.current_input = self.format_num(math.e)
            self.reset_next = True
            self.update_display()
        elif text in ('Deg', 'Rad'):
            self.use_deg = not self.use_deg
            self._build()
        elif text == 'x²':
            self.apply_func(lambda x: x ** 2)
        elif text == 'x³':
            self.apply_func(lambda x: x ** 3)
        elif text == '¹/x':
            self.apply_func(lambda x: 1 / x if x != 0 else None)
        elif text == '²√x':
            self.apply_func(lambda x: math.sqrt(x) if x >= 0 else None)
        elif text == '³√x':
            self.apply_func(lambda x: -((-x) ** (1 / 3)) if x < 0 else x ** (1 / 3))
        elif text == 'ln':
            self.apply_func(lambda x: math.log(x) if x > 0 else None)
        elif text == 'log₁₀':
            self.apply_func(lambda x: math.log10(x) if x > 0 else None)
        elif text == 'sin':
            self.apply_func(
                lambda x: math.sin(math.radians(x) if self.use_deg else x))
        elif text == 'cos':
            self.apply_func(
                lambda x: math.cos(math.radians(x) if self.use_deg else x))
        elif text == 'tan':
            self.apply_func(
                lambda x: math.tan(math.radians(x) if self.use_deg else x))
        elif text == 'sinh':
            self.apply_func(math.sinh)
        elif text == 'cosh':
            self.apply_func(math.cosh)
        elif text == 'tanh':
            self.apply_func(math.tanh)
        elif text == 'eˣ':
            self.apply_func(math.exp)
        elif text == '10ˣ':
            self.apply_func(lambda x: 10 ** x)
        elif text == 'x!':
            self.apply_func(
                lambda x: math.factorial(int(x))
                if x >= 0 and x == int(x) else None
            )
        # ── 메모리 ──
        elif text == 'mc':
            self.memory = 0
        elif text == 'm+':
            try:
                self.memory += float(self.current_input)
            except Exception:
                pass
        elif text == 'm-':
            try:
                self.memory -= float(self.current_input)
            except Exception:
                pass
        elif text == 'mr':
            self.current_input = self.format_num(self.memory)
            self.reset_next = True
            self.update_display()
        # ── xʸ : x의 y제곱 ──
        elif text == 'xʸ':
            try:
                self.first_operand = float(self.current_input)
                self.operator = 'xʸ'
                self.pending_pow = True
                self.reset_next = True
            except Exception:
                self.current_input = 'Error'
                self.update_display()
        # ── ʸ√x : x의 y제곱근 ──
        elif text == 'ʸ√x':
            try:
                self.first_operand = float(self.current_input)
                self.operator = 'ʸ√x'
                self.pending_root = True
                self.reset_next = True
            except Exception:
                self.current_input = 'Error'
                self.update_display()
        # ── EE : ×10^n 입력 ──
        elif text == 'EE':
            if 'e' not in self.current_input.lower():
                self.current_input += 'e+'
                self.ee_mode = True
                self.update_display()
        # ── ( ) 괄호: 표시만 (단순 입력) ──
        elif text in ('(', ')'):
            pass  # 괄호 계산은 미지원 (아이폰 원본도 단순 표시)
        # ── 2nd: 현재는 토글 없이 무시 (레이블 전환 없음) ──
        elif text == '2nd':
            pass

    # ── 계산 로직 ─────────────────────────────────────────────────

    def apply_func(self, func):
        try:
            val = float(self.current_input)
            result = func(val)
            self.current_input = 'Error' if result is None else self.format_num(result)
            self.reset_next = True
        except Exception:
            self.current_input = 'Error'
        self.update_display()

    def input_digit(self, digit):
        if self.ee_mode:
            # EE 모드: 지수 부분에 숫자 추가
            self.current_input += digit
            self.update_display()
            return
        if self.reset_next:
            self.current_input = digit
            self.reset_next = False
        elif self.current_input == '0':
            self.current_input = digit
        else:
            self.current_input += digit
        self.update_display()

    def input_dot(self):
        if self.reset_next:
            self.current_input = '0.'
            self.reset_next = False
        elif '.' not in self.current_input:
            self.current_input += '.'
        self.update_display()

    def clear_all(self):
        self.current_input = '0'
        self.first_operand = None
        self.operator = None
        self.reset_next = False
        self.ee_mode = False
        self.pending_pow = False
        self.pending_root = False
        self.update_display()

    def backspace(self):
        if self.current_input not in ('0', 'Error'):
            self.current_input = self.current_input[:-1] or '0'
        self.update_display()

    def toggle_sign(self):
        if self.current_input not in ('0', 'Error'):
            if self.current_input.startswith('-'):
                self.current_input = self.current_input[1:]
            else:
                self.current_input = '-' + self.current_input
        self.update_display()

    def percent(self):
        try:
            self.current_input = self.format_num(float(self.current_input) / 100)
        except Exception:
            self.current_input = 'Error'
        self.update_display()

    def input_operator(self, op):
        if (self.first_operand is not None
                and self.operator is not None
                and not self.reset_next):
            self.calculate()
        self.first_operand = float(self.current_input)
        self.operator = op
        self.reset_next = True

    def calculate(self):
        if self.first_operand is None or self.operator is None:
            return
        try:
            second = float(self.current_input)
            result = None
            if self.operator == '+':
                result = self.first_operand + second
            elif self.operator == '-':
                result = self.first_operand - second
            elif self.operator == '×':
                result = self.first_operand * second
            elif self.operator == '÷':
                if second == 0:
                    self.current_input = 'Error'
                    self.first_operand = None
                    self.operator = None
                    self.pending_pow = False
                    self.pending_root = False
                    self.update_display()
                    return
                result = self.first_operand / second
            elif self.operator == 'xʸ':
                result = self.first_operand ** second
                self.pending_pow = False
            elif self.operator == 'ʸ√x':
                if second == 0:
                    result = None
                else:
                    base = self.first_operand
                    exp = 1.0 / second
                    result = -((-base) ** exp) if base < 0 else base ** exp
                self.pending_root = False
            if result is None:
                self.current_input = 'Error'
            else:
                self.current_input = self.format_num(result)
            self.first_operand = None
            self.operator = None
            self.reset_next = True
        except Exception:
            self.current_input = 'Error'
            self.first_operand = None
            self.operator = None
        self.update_display()

    def _parse_input(self):
        """current_input을 float로 변환 (EE 표기 포함)."""
        try:
            return float(self.current_input.replace('e+', 'e').replace('e-', 'e-'))
        except Exception:
            return None

    def format_num(self, value):
        try:
            if value != value:          # NaN
                return 'Error'
            if abs(value) == float('inf'):
                return 'Error'
            if value == int(value) and abs(value) < 1e15:
                return str(int(value))
            result = str(round(value, 10))
            if '.' in result:
                result = result.rstrip('0').rstrip('.')
            return result
        except Exception:
            return 'Error'

    def update_display(self):
        self.display.setText(self.current_input)

    # ── 키보드 입력 ───────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        if text.isdigit():
            self.on_click(text)
        elif text == '.':
            self.on_click('.')
        elif text == '+':
            self.on_click('+')
        elif text == '-':
            self.on_click('-')
        elif text == '*':
            self.on_click('×')
        elif text == '/':
            self.on_click('÷')
        elif text == '%':
            self.on_click('%')
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.on_click('=')
        elif key == Qt.Key_Escape:
            self.on_click('AC')
        elif key == Qt.Key_Backspace:
            self.backspace()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    calc = Calculator()
    calc.show()
    sys.exit(app.exec_())