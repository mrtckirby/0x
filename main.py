from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field
from typing import Callable

import flet as ft

QUESTION_TYPES = ("a", "b", "c", "d")
QUESTION_BATCH_SIZE = 20
SCROLL_THRESHOLD = 400
FLOAT_TOLERANCE = 0.01
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


def format_hex(value: int) -> str:
    return format(value, "02X")


def normalise_hex(value: str) -> str:
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


def hex_validator(expected: int) -> Callable[[str], bool]:
    expected_hex = format_hex(expected).lower()

    def validate(answer: str) -> bool:
        cleaned = normalise_hex(answer)
        return cleaned == expected_hex

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
    source_base, target_base = random.sample(("binary", "denary", "hex"), 2)

    representations = {
        "binary": format_binary(value),
        "denary": str(value),
        "hex": format_hex(value),
    }
    validators = {
        "binary": binary_validator(value),
        "denary": integer_validator(value),
        "hex": hex_validator(value),
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
        max_value = (255 >> shift)
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
    generator = random.choice((generate_binary_addition_question, generate_bit_shift_question))
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

        self.answer_field = ft.TextField(
            width=180,
            hint_text="Type answer",
            dense=True,
            on_change=self._handle_change,
        )

        prompt = f"[{self.question_type.upper()}] {question.prompt}"

        self.control = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=ft.Text(prompt), expand=True),
                    self.answer_field,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            border=ft.Border(
                left=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT),
                top=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT),
                right=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT),
                bottom=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT),
            ),
            border_radius=10,
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


def main(page: ft.Page) -> None:
    page.title = "CS Maths Practice"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    state = AppState()

    name_text = ft.Text("Student: —", weight=ft.FontWeight.BOLD)
    score_texts = {
        question_type: ft.Text(f"{question_type.upper()}: 0")
        for question_type in QUESTION_TYPES
    }

    def refresh_dashboard() -> None:
        if state.firstname or state.lastname:
            name_text.value = f"Student: {state.firstname} {state.lastname}"
        else:
            name_text.value = "Student: —"

        for question_type in QUESTION_TYPES:
            score_texts[question_type].value = (
                f"{question_type.upper()}: {state.scores[question_type]}"
            )

        dashboard.update()

    def update_score(question_type: str, delta: int) -> None:
        state.scores[question_type] += delta
        refresh_dashboard()

    question_list = ft.ListView(
        expand=True,
        spacing=12,
        padding=16,
    )

    def append_questions(count: int) -> None:
        for _ in range(count):
            question_type = random.choice(QUESTION_TYPES)
            question = QUESTION_GENERATORS[question_type]()
            question_row = QuestionRow(
                question=question,
                on_score_change=update_score,
            )
            question_list.controls.append(question_row.control)

    def handle_scroll(e: ft.OnScrollEvent) -> None:
        if e.pixels >= e.max_scroll_extent - SCROLL_THRESHOLD:
            append_questions(QUESTION_BATCH_SIZE)
            page.update()

    question_list.on_scroll = handle_scroll
    append_questions(QUESTION_BATCH_SIZE)

    dashboard = ft.Container(
        content=ft.Row(
            controls=[
                name_text,
                ft.VerticalDivider(width=1),
                *[score_texts[question_type] for question_type in QUESTION_TYPES],
            ],
            wrap=True,
            spacing=16,
        ),
        padding=16,
        bgcolor=ft.colors.SURFACE_CONTAINER_HIGHEST,
        border=ft.border.only(bottom=ft.BorderSide(1, ft.colors.OUTLINE_VARIANT)),
    )

    firstname_field = ft.TextField(label="Firstname", autofocus=True)
    lastname_field = ft.TextField(label="Lastname")

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
        title=ft.Text("Start your session"),
        content=ft.Column(
            controls=[
                ft.Text("Enter your name to begin."),
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
    page.add(
        ft.Column(
            controls=[
                dashboard,
                question_list,
            ],
            expand=True,
            spacing=0,
        )
    )

    refresh_dashboard()
    name_dialog.open = True
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
