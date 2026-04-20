import sys
import os
import warnings
warnings.filterwarnings('ignore')  # 제약조건: 경고 메시지 없이 실행

# PyQt5 플랫폼 플러그인 경로 설정 - windows 플러그인을 찾지 못하는 오류 방지
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'venv', 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins', 'platforms'
)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.current_input = '0'
        self.first_operand = None
        self.operator = None
        self.reset_next = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Calculator')
        self.setFixedSize(320, 520)
        self.setStyleSheet('background-color: #1c1c1e;')

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.display = QLabel(self.current_input)
        self.display.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.display.setFont(QFont('Arial', 48, QFont.Light))
        self.display.setStyleSheet('color: white; padding: 10px 10px 0px 10px;')
        self.display.setFixedHeight(120)
        main_layout.addWidget(self.display)

        button_layout = QGridLayout()
        button_layout.setSpacing(10)

        buttons = [
            ('AC', 0, 0, 'func'), ('+/-', 0, 1, 'func'), ('%', 0, 2, 'func'), ('÷', 0, 3, 'op'),
            ('7',  1, 0, 'num'),  ('8',  1, 1, 'num'),   ('9',  1, 2, 'num'), ('×', 1, 3, 'op'),
            ('4',  2, 0, 'num'),  ('5',  2, 1, 'num'),   ('6',  2, 2, 'num'), ('-', 2, 3, 'op'),
            ('1',  3, 0, 'num'),  ('2',  3, 1, 'num'),   ('3',  3, 2, 'num'), ('+', 3, 3, 'op'),
            ('0',  4, 0, 'zero'), ('.',  4, 2, 'num'),   ('=',  4, 3, 'op'),
        ]

        for btn_data in buttons:
            text, row, col, btn_type = btn_data
            btn = QPushButton(text)
            btn.setFont(QFont('Arial', 22))
            btn.setFixedHeight(70)

            if btn_type == 'num':
                btn.setStyleSheet(self.style_btn('#333333', 'white'))
            elif btn_type == 'func':
                btn.setStyleSheet(self.style_btn('#a5a5a5', 'black'))
            elif btn_type == 'op':
                btn.setStyleSheet(self.style_btn('#ff9f0a', 'white'))
            elif btn_type == 'zero':
                btn.setStyleSheet(self.style_zero())
                btn.setFixedWidth(150)

            btn.clicked.connect(lambda checked, t=text: self.on_click(t))

            if text == '0':
                button_layout.addWidget(btn, row, col, 1, 2)
            else:
                button_layout.addWidget(btn, row, col)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def style_btn(self, bg, fg):
        return (
            'QPushButton { background-color: ' + bg + '; color: ' + fg + '; border-radius: 35px; }'
            'QPushButton:pressed { background-color: #888888; }'
        )

    def style_zero(self):
        return (
            'QPushButton { background-color: #333333; color: white; border-radius: 35px;'
            '   text-align: left; padding-left: 25px; }'
            'QPushButton:pressed { background-color: #888888; }'
        )

    def on_click(self, text):
        if text.isdigit():
            self.input_digit(text)
        elif text == '.':
            self.input_dot()
        elif text == 'AC':
            self.clear_all()
        elif text == '+/-':
            self.toggle_sign()
        elif text == '%':
            self.percent()
        elif text in ('÷', '×', '-', '+'):
            self.input_operator(text)
        elif text == '=':
            self.calculate()

    def input_digit(self, digit):
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
            value = float(self.current_input) / 100
            self.current_input = self.format_num(value)
        except Exception:
            self.current_input = 'Error'
        self.update_display()

    def input_operator(self, op):
        # 연산자 연속 입력 시 이전 연산 먼저 계산
        if self.first_operand is not None and self.operator is not None and not self.reset_next:
            self.calculate()
        self.first_operand = float(self.current_input)
        self.operator = op
        self.reset_next = True

    def calculate(self):
        if self.first_operand is None or self.operator is None:
            return
        try:
            second = float(self.current_input)
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
                    self.update_display()
                    return
                result = self.first_operand / second
            self.current_input = self.format_num(result)
            self.first_operand = None
            self.operator = None
            self.reset_next = True
        except Exception:
            self.current_input = 'Error'
            self.first_operand = None
            self.operator = None
        self.update_display()

    def format_num(self, value):
        try:
            if value != value:  # NaN 체크
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    calc = Calculator()
    calc.show()
    sys.exit(app.exec_())