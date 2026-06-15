from __future__ import annotations

import random
from dataclasses import dataclass, field

import flet as ft

QUESTION_TYPES = ("a", "b", "c", "d")
QUESTION_BATCH_SIZE = 20
SCROLL_THRESHOLD = 400


@dataclass
class AppState:
    firstname: str = ""
    lastname: str = ""
    scores: dict[str, int] = field(
        default_factory=lambda: {question_type: 0 for question_type in QUESTION_TYPES}
    )


class QuestionRow:
    def __init__(
        self,
        index: int,
        question_type: str,
        on_score_change,
    ) -> None:
        self.question_type = question_type
        self.expected_answer = str(index)
        self.on_score_change = on_score_change
        self.is_correct = False

        self.answer_field = ft.TextField(
            width=180,
            hint_text="Type answer",
            dense=True,
            on_change=self._handle_change,
        )

        prompt = (
            f"[{question_type.upper()}] Placeholder question {index}: "
            f"type {self.expected_answer} to mark it correct."
        )

        self.control = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=ft.Text(prompt), expand=True),
                    self.answer_field,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
        )

    def _handle_change(self, e: ft.ControlEvent) -> None:
        value = e.control.value.strip()
        is_correct = value == self.expected_answer

        if is_correct != self.is_correct:
            self.is_correct = is_correct
            self.on_score_change(self.question_type, 1 if is_correct else -1)

        e.control.bgcolor = ft.Colors.GREEN_100 if is_correct else None
        e.control.border_color = ft.Colors.GREEN if is_correct else None
        e.control.update()


def main(page: ft.Page) -> None:
    page.title = "CS Maths Practice"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    state = AppState()
    question_count = 0

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
        padding=ft.padding.all(16),
    )

    def append_questions(count: int) -> None:
        nonlocal question_count
        for _ in range(count):
            question_count += 1
            question_type = random.choice(QUESTION_TYPES)
            question_row = QuestionRow(
                index=question_count,
                question_type=question_type,
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
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
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
