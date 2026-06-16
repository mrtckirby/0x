from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Callable

import flet as ft

QUESTION_TYPES = ("a", "b", "c", "d")
QUESTION_BATCH_SIZE = 20
FLOAT_TOLERANCE = 0.01
MONOSPACE_FONT = "Courier New"
QUESTION_TYPE_DETAILS = {
    "a": {
        "label": "Base conversion",
        "color": ft.colors.BLUE_700,
    },
    "b": {
        "label": "Binary arithmetic",
        "color": ft.colors.DEEP_PURPLE_700,
    },
    "c": {
        "label": "Unit conversion",
        "color": ft.colors.TEAL_700,
    },
    "d": {
        "label": "Number of values",
        "color": ft.colors.ORANGE_800,
    },
}
UNIT_VALUES = {
    "bit": 1,
    "byte": 8,
    "kilobyte": 8_000,
    "megabyte": 8_000_000,
    "gigabyte": 8_000_000_000,
}
UNIT_VALUES_BINARY = {
    "bit": 1,
    "byte": 8,
    "kilobyte": 8 * 1024,
    "megabyte": 8 * 1024**2,
    "gigabyte": 8 * 1024**3,
}
UNIT_LABELS = {
    "bit": "bits",
    "byte": "bytes",
    "kilobyte": "kilobytes",
    "megabyte": "megabytes",
    "gigabyte": "gigabytes",
}


@dataclass
class AppState:
    firstname: str = ""
    lastname: str = ""
    scores: dict[str, int] = field(
        default_factory=lambda: {question_type: 0 for question_type in QUESTION_TYPES}
    )


@dataclass
class Question:
    question_type: str
    prompt: str
    validator: Callable[[str], bool]


def format_binary(value: int) -> str:
    return format(value, "08b")


def format_hexadecimal(value: int) -> str:
    return format(value, "02X")


def normalise_hexadecimal(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    return cleaned


def parse_float(value: str) -> float | None:
    try:
        return float(value.strip())
    except ValueError:
        return None


def is_close_to_any(value: float, expected_values: list[float]) -> bool:
    return any(abs(value - expected) <= FLOAT_TOLERANCE for expected in expected_values)


def integer_validator(expected: int) -> Callable[[str], bool]:
    def validate(answer: str) -> bool:
        try:
            return int(answer.strip()) == expected
        except ValueError:
            return False

    return validate


def binary_validator(expected: int) -> Callable[[str], bool]:
    expected_binary = format_binary(expected)

    def validate(answer: str) -> bool:
        cleaned = answer.strip()
        return bool(re.fullmatch(r"[01]{8}", cleaned)) and cleaned == expected_binary

    return validate


def hexadecimal_validator(expected: int) -> Callable[[str], bool]:
    expected_hexadecimal = format_hexadecimal(expected).lower()

    def validate(answer: str) -> bool:
        cleaned = normalise_hexadecimal(answer)
        return cleaned == expected_hexadecimal

    return validate


def float_validator(expected_values: list[float]) -> Callable[[str], bool]:
    def validate(answer: str) -> bool:
        parsed = parse_float(answer)
        return parsed is not None and is_close_to_any(parsed, expected_values)

    return validate


def number_validator(expected_values: list[float]) -> Callable[[str], bool]:
    if all(float(value).is_integer() for value in expected_values):
        integer_values = {int(value) for value in expected_values}

        def validate(answer: str) -> bool:
            cleaned = answer.strip()
            try:
                integer_answer = int(cleaned)
            except ValueError:
                parsed = parse_float(cleaned)
                return parsed is not None and is_close_to_any(
                    parsed, [float(value) for value in integer_values]
                )
            return integer_answer in integer_values

        return validate

    return float_validator(expected_values)


def generate_base_conversion_question() -> Question:
    value = random.randint(0, 255)
    source_base, target_base = random.sample(("binary", "denary", "hexadecimal"), 2)

    representations = {
        "binary": format_binary(value),
        "denary": str(value),
        "hexadecimal": format_hexadecimal(value),
    }
    validators = {
        "binary": binary_validator(value),
        "denary": integer_validator(value),
        "hexadecimal": hexadecimal_validator(value),
    }

    prompt = (
        f"Convert {representations[source_base]} from {source_base} to {target_base}."
    )
    return Question("a", prompt, validators[target_base])


def generate_binary_addition_question() -> Question:
    term_count = random.choice((2, 3))

    while True:
        values = [random.randint(0, 255) for _ in range(term_count)]
        total = sum(values)
        if total <= 255:
            break

    binary_values = [format_binary(value) for value in values]
    prompt = "Add these 8-bit binary numbers: " + " + ".join(binary_values)
    return Question("b", prompt, binary_validator(total))


def generate_bit_shift_question() -> Question:
    direction = random.choice(("left", "right"))
    shift = random.randint(1, 3)

    if direction == "left":
        max_value = 255 >> shift
        value = random.randint(0, max_value)
        result = value << shift
    else:
        value = random.randint(0, 255)
        result = value >> shift

    prompt = (
        f"Apply a {direction} shift by {shift} to the 8-bit binary number "
        f"{format_binary(value)}. Give the result in binary."
    )
    return Question("b", prompt, binary_validator(result))


def generate_binary_arithmetic_question() -> Question:
    generator = random.choice(
        (generate_binary_addition_question, generate_bit_shift_question)
    )
    return generator()


def generate_unit_conversion_question() -> Question:
    source_unit, target_unit = random.sample(tuple(UNIT_VALUES.keys()), 2)
    amount = random.randint(1, 500)

    decimal_result = amount * UNIT_VALUES[source_unit] / UNIT_VALUES[target_unit]
    binary_result = (
        amount * UNIT_VALUES_BINARY[source_unit] / UNIT_VALUES_BINARY[target_unit]
    )

    prompt = (
        f"Convert {amount} {UNIT_LABELS[source_unit]} to {UNIT_LABELS[target_unit]}. "
        f"You may use either base-10 or base-2 conventions."
    )
    return Question("c", prompt, number_validator([decimal_result, binary_result]))


def generate_bit_capacity_question() -> Question:
    bits = random.randint(1, 8)
    prompt = f"How many different values can be represented using {bits} bits?"
    return Question("d", prompt, integer_validator(2**bits))


def generate_denary_digit_capacity_question() -> Question:
    digits = random.randint(1, 6)
    prompt = (
        f"How many different values can be represented using {digits} denary digits?"
    )
    return Question("d", prompt, integer_validator(10**digits))


def generate_capacity_question() -> Question:
    generator = random.choice(
        (generate_bit_capacity_question, generate_denary_digit_capacity_question)
    )
    return generator()


QUESTION_GENERATORS = {
    "a": generate_base_conversion_question,
    "b": generate_binary_arithmetic_question,
    "c": generate_unit_conversion_question,
    "d": generate_capacity_question,
}


class QuestionRow:
    def __init__(
        self,
        question: Question,
        on_score_change,
    ) -> None:
        self.question_type = question.question_type
        self.validator = question.validator
        self.on_score_change = on_score_change
        self.is_correct = False
        self.question_color = QUESTION_TYPE_DETAILS[self.question_type]["color"]

        self.answer_field = ft.TextField(
            width=180,
            hint_text="Type answer",
            dense=True,
            on_change=self._handle_change,
            text_style=ft.TextStyle(font_family=MONOSPACE_FONT, size=16),
            hint_style=ft.TextStyle(font_family=MONOSPACE_FONT),
        )

        prompt_text = ft.Text(
            question.prompt,
            color=self.question_color,
            size=18,
            weight=ft.FontWeight.W_600,
            font_family=MONOSPACE_FONT,
        )

        self.control = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=prompt_text, expand=True),
                    self.answer_field,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=16,
            border=ft.Border(
                left=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT),
                top=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT),
                right=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT),
                bottom=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT),
            ),
            border_radius=12,
        )

    def _handle_change(self, e: ft.ControlEvent) -> None:
        value = e.control.value.strip()
        is_correct = self.validator(value)

        if is_correct != self.is_correct:
            self.is_correct = is_correct
            self.on_score_change(self.question_type, 1 if is_correct else -1)

        e.control.bgcolor = ft.colors.GREEN_100 if is_correct else None
        e.control.border_color = ft.colors.GREEN if is_correct else None
        e.control.update()


def build_score_block(label: str, value_text: ft.Text, color: str) -> ft.Control:
    return ft.Container(
        width=100,
        content=ft.Column(
            controls=[
                ft.Text(
                    label,
                    size=11,
                    color=color,
                    font_family=MONOSPACE_FONT,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=2,
                ),
                value_text,
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
    )


def main(page: ft.Page) -> None:
    page.title = "CS Maths Practice"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    state = AppState()

    name_text = ft.Text(
        "Student: —",
        weight=ft.FontWeight.BOLD,
        size=18,
        font_family=MONOSPACE_FONT,
    )
    score_value_texts = {
        question_type: ft.Text(
            "0",
            size=28,
            weight=ft.FontWeight.BOLD,
            color=QUESTION_TYPE_DETAILS[question_type]["color"],
            font_family=MONOSPACE_FONT,
            text_align=ft.TextAlign.CENTER,
        )
        for question_type in QUESTION_TYPES
    }
    average_value_text = ft.Text(
        "0.00",
        size=28,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.GREEN_700,
        font_family=MONOSPACE_FONT,
        text_align=ft.TextAlign.CENTER,
    )

    dashboard = ft.Container(width=float("inf"))

    def refresh_dashboard() -> None:
        if state.firstname or state.lastname:
            name_text.value = f"Student: {state.firstname} {state.lastname}"
        else:
            name_text.value = "Student: —"

        total_score = 0
        for question_type in QUESTION_TYPES:
            score = state.scores[question_type]
            total_score += score
            score_value_texts[question_type].value = str(score)

        average_score = total_score / len(QUESTION_TYPES)
        average_value_text.value = f"{average_score:.2f}"

        dashboard.update()

    def update_score(question_type: str, delta: int) -> None:
        state.scores[question_type] += delta
        refresh_dashboard()

    question_column = ft.Column(spacing=12)

    def append_questions(count: int) -> None:
        for _ in range(count):
            question_type = random.choice(QUESTION_TYPES)
            question = QUESTION_GENERATORS[question_type]()
            question_row = QuestionRow(
                question=question,
                on_score_change=update_score,
            )
            question_column.controls.append(question_row.control)

    def load_more_questions(_: ft.ControlEvent) -> None:
        append_questions(QUESTION_BATCH_SIZE)
        page.update()

    append_questions(QUESTION_BATCH_SIZE)

    totals_row = ft.Row(
        controls=[
            *[
                build_score_block(
                    QUESTION_TYPE_DETAILS[question_type]["label"],
                    score_value_texts[question_type],
                    QUESTION_TYPE_DETAILS[question_type]["color"],
                )
                for question_type in QUESTION_TYPES
            ],
            build_score_block("Average", average_value_text, ft.colors.GREEN_700),
        ],
        wrap=True,
        spacing=12,
        run_spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    dashboard.content = ft.Column(
        controls=[
            totals_row,
            name_text,
        ],
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        tight=True,
    )
    dashboard.padding = ft.padding.symmetric(horizontal=16, vertical=12)
    dashboard.bgcolor = ft.colors.SURFACE_CONTAINER_HIGHEST
    dashboard.border = ft.border.only(bottom=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT))

    load_more_button = ft.FilledButton(
        text=f"Load {QUESTION_BATCH_SIZE} more questions",
        on_click=load_more_questions,
    )

    firstname_field = ft.TextField(
        label="Firstname",
        autofocus=True,
        text_style=ft.TextStyle(font_family=MONOSPACE_FONT),
        label_style=ft.TextStyle(font_family=MONOSPACE_FONT),
    )
    lastname_field = ft.TextField(
        label="Lastname",
        text_style=ft.TextStyle(font_family=MONOSPACE_FONT),
        label_style=ft.TextStyle(font_family=MONOSPACE_FONT),
    )

    def start_session(_: ft.ControlEvent) -> None:
        firstname = firstname_field.value.strip()
        lastname = lastname_field.value.strip()

        firstname_field.error_text = None if firstname else "Enter a firstname"
        lastname_field.error_text = None if lastname else "Enter a lastname"

        if not firstname or not lastname:
            name_dialog.update()
            return

        state.firstname = firstname
        state.lastname = lastname
        refresh_dashboard()
        name_dialog.open = False
        page.update()

    name_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Start your session", font_family=MONOSPACE_FONT),
        content=ft.Column(
            controls=[
                ft.Text("Enter your name to begin.", font_family=MONOSPACE_FONT),
                firstname_field,
                lastname_field,
            ],
            tight=True,
            width=360,
        ),
        actions=[ft.FilledButton("Start", on_click=start_session)],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.dialog = name_dialog
    page.overlay.append(
        ft.SafeArea(
            content=dashboard,
            top=True,
            bottom=False,
            left=False,
            right=False,
        )
    )
    page.add(
        ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=130),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                question_column,
                                ft.Container(
                                    content=load_more_button,
                                    alignment=ft.alignment.center,
                                    padding=ft.padding.only(top=8, bottom=16),
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=16,
                    ),
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )
    )

    refresh_dashboard()
    name_dialog.open = True
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
