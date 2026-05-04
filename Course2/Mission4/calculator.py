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
MAX_VALUE = 1e15  # 처리 가능한 숫자 범위 상한


class Calculator:
    # 계산기 핵심 로직 클래스
    def __init__(self):
        self.current_input = '0'
        self.first_operand = None
        self.operator = None
        self.reset_next = False
        self.use_deg = True

    def add(self, a, b):
        result = a + b
        if abs(result) >= MAX_VALUE:
            raise OverflowError('숫자 범위 초과')
        return result

    def subtract(self, a, b):
        result = a - b
        if abs(result) >= MAX_VALUE:
            raise OverflowError('숫자 범위 초과')
        return result

    def multiply(self, a, b):
        result = a * b
        if abs(result) >= MAX_VALUE:
            raise OverflowError('숫자 범위 초과')
        return result

    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError('0으로 나눌 수 없습니다')
        result = a / b
        if abs(result) >= MAX_VALUE:
            raise OverflowError('숫자 범위 초과')
        return result

    def reset(self):
        self.current_input = '0'
        self.first_operand = None
        self.operator = None
        self.reset_next = False

    def negative_positive(self):
        if self.current_input not in ('0', 'Error'):
            if self.current_input.startswith('-'):
                self.current_input = self.current_input[1:]
            else:
                self.current_input = '-' + self.current_input

    def percent(self):
        try:
            value = float(self.current_input) / 100
            self.current_input = self.format_num(value)
        except Exception:
            self.current_input = 'Error'

    def equal(self):
        if self.first_operand is None or self.operator is None:
            return
        try:
            second = float(self.current_input)
            if self.operator == '+':
                result = self.add(self.first_operand, second)
            elif self.operator == '-':
                result = self.subtract(self.first_operand, second)
            elif self.operator == '×':
                result = self.multiply(self.first_operand, second)
            elif self.operator == '÷':
                result = self.divide(self.first_operand, second)
            self.current_input = self.format_num(result)
            self.first_operand = None
            self.operator = None
            self.reset_next = True
        except ZeroDivisionError:
            self.current_input = 'Error'
            self.first_operand = None
            self.operator = None
        except OverflowError:
            self.current_input = 'Error'
            self.first_operand = None
            self.operator = None
        except Exception:
            self.current_input = 'Error'
            self.first_operand = None
            self.operator = None

    def input_digit(self, digit):
        if self.reset_next:
            self.current_input = digit
            self.reset_next = False
        elif self.current_input == '0':
            self.current_input = digit
        else:
            if len(self.current_input.replace('-', '').replace('.', '')) >= 15:
                return
            self.current_input += digit

    def input_dot(self):
        if self.reset_next:
            self.current_input = '0.'
            self.reset_next = False
        elif '.' not in self.current_input:
            self.current_input += '.'

    def input_operator(self, op):
        # 연산자 연속 입력 시 이전 연산 먼저 계산
        if self.first_operand is not None and self.operator is not None and not self.reset_next:
            self.equal()
        self.first_operand = float(self.current_input)
        self.operator = op
        self.reset_next = True

    def backspace(self):
        if self.current_input not in ('0', 'Error'):
            self.current_input = self.current_input[:-1] or '0'

    def apply_func(self, func):
        try:
            val = float(self.current_input)
            result = func(val)
            if result is None:
                self.current_input = 'Error'
            elif abs(result) >= MAX_VALUE:
                self.current_input = 'Error'
            else:
                self.current_input = self.format_num(result)
            self.reset_next = True
        except Exception:
            self.current_input = 'Error'

    def format_num(self, value):
        # 보너스: 소수점 6자리 이하 반올림
        try:
            if value != value:  # NaN 체크
                return 'Error'
            if abs(value) == float('inf'):
                return 'Error'
            if abs(value) >= MAX_VALUE:
                return 'Error'
            if value == int(value):
                return str(int(value))
            # 소수점 6자리로 반올림
            result = round(value, 6)
            text = '{:.6f}'.format(result).rstrip('0').rstrip('.')
            return text
        except Exception:
            return 'Error'


class CalculatorWindow(QWidget):
    # UI 클래스 - Calculator 클래스와 연결
    def __init__(self):
        super().__init__()
        self.calc = Calculator()
        self.is_landscape = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Calculator')
        self.setStyleSheet('background-color: #000000;')
        self.build_layout()

    def build_layout(self):
        old = self.layout()
        if old:
            while old.count():
                item = old.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
            QWidget().setLayout(old)

        if self.is_landscape:
            self.setFixedSize(760, 420)
        else:
            self.setFixedSize(320, 620)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(12, 6, 12, 10)

        # 디스플레이
        self.display = QLabel(self.calc.current_input)
        self.display.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.display.setStyleSheet('color: white; padding: 0 4px 4px 4px;')
        self.display.setFixedHeight(140 if not self.is_landscape else 90)
        self.update_display_font()
        main_layout.addWidget(self.display)

        # 회전 버튼
        rotate_bar = QHBoxLayout()
        rotate_bar.setContentsMargins(0, 0, 0, 4)
        rotate_bar.addStretch()
        rotate_btn = QPushButton('⟳')
        rotate_btn.setFixedSize(28, 28)
        rotate_btn.setFont(QFont('Arial', 13))
        rotate_btn.setStyleSheet(
            'QPushButton { background-color: #2c2c2e; color: white; border-radius: 14px; }'
            'QPushButton:pressed { background-color: #555; }'
        )
        rotate_btn.clicked.connect(self.toggle_orientation)
        rotate_bar.addWidget(rotate_btn)
        main_layout.addLayout(rotate_bar)

        grid = QGridLayout()
        grid.setSpacing(GAP)

        if self.is_landscape:
            self.build_landscape(grid)
        else:
            self.build_portrait(grid)

        main_layout.addLayout(grid)
        self.setLayout(main_layout)

    def build_portrait(self, grid):
        buttons = [
            ('⌫',  0, 0, 'func'), ('AC',  0, 1, 'func'),
            ('%',  0, 2, 'func'), ('÷',   0, 3, 'op'),
            ('7',  1, 0, 'num'),  ('8',   1, 1, 'num'),
            ('9',  1, 2, 'num'),  ('×',   1, 3, 'op'),
            ('4',  2, 0, 'num'),  ('5',   2, 1, 'num'),
            ('6',  2, 2, 'num'),  ('-',   2, 3, 'op'),
            ('1',  3, 0, 'num'),  ('2',   3, 1, 'num'),
            ('3',  3, 2, 'num'),  ('+',   3, 3, 'op'),
            ('+/-',4, 0, 'func'), ('0',   4, 1, 'num'),
            ('.',  4, 2, 'num'),  ('=',   4, 3, 'op'),
        ]
        for text, row, col, btn_type in buttons:
            btn = self.make_btn(text, btn_type, 65, 22)
            btn.clicked.connect(lambda checked, t=text: self.on_click(t))
            grid.addWidget(btn, row, col)

    def build_landscape(self, grid):
        deg_label = 'Deg' if self.calc.use_deg else 'Rad'
        buttons = [
            ('(',    0, 0, 'sci'), (')',    0, 1, 'sci'),
            ('mc',   0, 2, 'sci'), ('m+',  0, 3, 'sci'),
            ('m-',   0, 4, 'sci'), ('mr',  0, 5, 'sci'),
            ('⌫',    0, 6, 'func'), ('AC',  0, 7, 'func'),
            ('%',    0, 8, 'func'), ('÷',   0, 9, 'op'),

            ('2nd',  1, 0, 'sci'), ('x²',  1, 1, 'sci'),
            ('x³',   1, 2, 'sci'), ('xʸ',  1, 3, 'sci'),
            ('eˣ',   1, 4, 'sci'), ('10ˣ', 1, 5, 'sci'),
            ('7',    1, 6, 'num'), ('8',   1, 7, 'num'),
            ('9',    1, 8, 'num'), ('×',   1, 9, 'op'),

            ('¹/x',  2, 0, 'sci'), ('²√x', 2, 1, 'sci'),
            ('³√x',  2, 2, 'sci'), ('ʸ√x', 2, 3, 'sci'),
            ('ln',   2, 4, 'sci'), ('log₁₀',2,5,'sci'),
            ('4',    2, 6, 'num'), ('5',   2, 7, 'num'),
            ('6',    2, 8, 'num'), ('-',   2, 9, 'op'),

            ('x!',   3, 0, 'sci'), ('sin', 3, 1, 'sci'),
            ('cos',  3, 2, 'sci'), ('tan', 3, 3, 'sci'),
            ('e',    3, 4, 'sci'), ('EE',  3, 5, 'sci'),
            ('1',    3, 6, 'num'), ('2',   3, 7, 'num'),
            ('3',    3, 8, 'num'), ('+',   3, 9, 'op'),

            ('Rand', 4, 0, 'sci'), ('sinh',4, 1, 'sci'),
            ('cosh', 4, 2, 'sci'), ('tanh',4, 3, 'sci'),
            ('π',    4, 4, 'sci'), (deg_label, 4, 5, 'sci'),
            ('+/-',  4, 6, 'func'), ('0',  4, 7, 'num'),
            ('.',    4, 8, 'num'), ('=',   4, 9, 'op'),
        ]
        for text, row, col, btn_type in buttons:
            fs = 10 if len(text) > 3 else 13
            btn = self.make_btn(text, btn_type, 52, fs)
            btn.clicked.connect(lambda checked, t=text: self.on_click(t))
            grid.addWidget(btn, row, col)

    def make_btn(self, text, btn_type, height, font_size):
        btn = QPushButton(text)
        btn.setFixedHeight(height)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setFont(QFont('Arial', font_size))
        r = str(height // 2) + 'px'
        style_map = {
            'num':  ('#333333', 'white'),
            'func': ('#505050', 'white'),
            'op':   ('#ff9f0a', 'white'),
            'sci':  ('#1c1c1e', 'white'),
        }
        bg, fg = style_map.get(btn_type, ('#333333', 'white'))
        btn.setStyleSheet(
            'QPushButton { background-color: ' + bg + '; color: ' + fg
            + '; border-radius: ' + r + '; }'
            'QPushButton:pressed { background-color: #888; }'
        )
        return btn

    def toggle_orientation(self):
        self.is_landscape = not self.is_landscape
        self.build_layout()

    def on_click(self, text):
        if text.isdigit():
            self.calc.input_digit(text)
        elif text == '.':
            self.calc.input_dot()
        elif text == 'AC':
            self.calc.reset()
        elif text == '⌫':
            self.calc.backspace()
        elif text == '+/-':
            self.calc.negative_positive()
        elif text == '%':
            self.calc.percent()
        elif text in ('÷', '×', '-', '+'):
            self.calc.input_operator(text)
        elif text == '=':
            self.calc.equal()
        elif text == 'Rand':
            self.calc.current_input = self.calc.format_num(random.random())
            self.calc.reset_next = True
        elif text == 'π':
            self.calc.current_input = self.calc.format_num(math.pi)
            self.calc.reset_next = True
        elif text == 'e':
            self.calc.current_input = self.calc.format_num(math.e)
            self.calc.reset_next = True
        elif text in ('Deg', 'Rad'):
            self.calc.use_deg = not self.calc.use_deg
            self.build_layout()
            return
        elif text == 'x²':
            self.calc.apply_func(lambda x: x ** 2)
        elif text == 'x³':
            self.calc.apply_func(lambda x: x ** 3)
        elif text == '¹/x':
            self.calc.apply_func(lambda x: 1 / x if x != 0 else None)
        elif text == '²√x':
            self.calc.apply_func(lambda x: math.sqrt(x) if x >= 0 else None)
        elif text == '³√x':
            self.calc.apply_func(lambda x: x ** (1 / 3))
        elif text == 'ln':
            self.calc.apply_func(lambda x: math.log(x) if x > 0 else None)
        elif text == 'log₁₀':
            self.calc.apply_func(lambda x: math.log10(x) if x > 0 else None)
        elif text == 'sin':
            self.calc.apply_func(
                lambda x: math.sin(math.radians(x) if self.calc.use_deg else x)
            )
        elif text == 'cos':
            self.calc.apply_func(
                lambda x: math.cos(math.radians(x) if self.calc.use_deg else x)
            )
        elif text == 'tan':
            self.calc.apply_func(
                lambda x: math.tan(math.radians(x) if self.calc.use_deg else x)
            )
        elif text == 'sinh':
            self.calc.apply_func(math.sinh)
        elif text == 'cosh':
            self.calc.apply_func(math.cosh)
        elif text == 'tanh':
            self.calc.apply_func(math.tanh)
        elif text == 'eˣ':
            self.calc.apply_func(math.exp)
        elif text == '10ˣ':
            self.calc.apply_func(lambda x: 10 ** x)
        elif text == 'x!':
            self.calc.apply_func(
                lambda x: math.factorial(int(x)) if x >= 0 and x == int(x) else None
            )
        self.update_display()

    def update_display(self):
        self.display.setText(self.calc.current_input)
        self.update_display_font()

    def update_display_font(self):
        # 보너스: 숫자 길이에 따라 폰트 크기 자동 조절
        length = len(self.calc.current_input)
        if length <= 9:
            size = 52
        elif length <= 13:
            size = 38
        elif length <= 17:
            size = 28
        else:
            size = 20
        self.display.setFont(QFont('Arial', size, QFont.Light))

    def keyPressEvent(self, event: QKeyEvent):
        # 키보드 입력 지원
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
            self.calc.backspace()
            self.update_display()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CalculatorWindow()
    window.show()
    sys.exit(app.exec_())