from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QSettings
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QSpinBox,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ai_final_project.roster import read_student_names

# Theme strategy:
# - Use fixed dark neutrals for the overall shell so contrast stays stable.
# - Let a single accent palette drive "stateful" visuals (focus/selected/active),
#   which keeps the app coherent while still allowing personalization.
# Dark gray surfaces (fixed); accent drives borders, fills, and highlights like the default green.
_THEME_BG = "#252525"
_THEME_CARD = "#2e2e2e"
_THEME_CARD_DEEP = "#181818"
_THEME_TEXT = "#ffffff"
_THEME_MUTED = "#a8a8a8"
_LIST_HOVER_NEUTRAL = "#2c2c2c"

# Accent preset tuple order is intentionally compact because these values are
# expanded into `AccentPalette` and used all over the stylesheet.
# (border, border_bright, fill, fill_hover, fill_active, list_row_hover)
ACCENT_PRESETS: dict[str, tuple[str, str, str, str, str, str]] = {
    "green": ("#1a5c2e", "#247a3d", "#153d22", "#1e5230", "#0f2d18", "#2a3328"),
    "yellow": ("#7a6510", "#b89a1e", "#4a3d0c", "#5e4d12", "#2f2006", "#333024"),
    "orange": ("#8b4510", "#c45c12", "#4d2608", "#66350c", "#301604", "#33261c"),
    "hot_pink": ("#9d174d", "#e11d74", "#4a0f2a", "#6b1540", "#2a0818", "#331c28"),
    "blue": ("#1e3a8a", "#2563eb", "#152a55", "#1c3a70", "#0f1a36", "#1e2433"),
    "red": ("#7f1d1d", "#b91c1c", "#450a0a", "#5c1010", "#2c0505", "#331c1c"),
}


@dataclass(frozen=True)
class AccentPalette:
    # Slightly darker accent used for frame/control outlines.
    border: str
    # Slightly brighter accent used for selected/highlighted borders.
    border_bright: str
    # Base accent fill for selected/active surfaces.
    fill: str
    # Hover fill (lighter than active, darker than neutral card).
    fill_hover: str
    # Pressed/active fill for stronger interaction feedback.
    fill_active: str
    # List-row hover color (kept neutral to avoid visual noise).
    list_hover: str


def accent_palette_from_preset(key: str) -> AccentPalette:
    row = ACCENT_PRESETS.get(key, ACCENT_PRESETS["green"])
    return AccentPalette(*row)


def accent_palette_from_qcolor(c: QColor) -> AccentPalette:
    base = QColor(c)
    if not base.isValid():
        return accent_palette_from_preset("green")
    # Derive a complete interaction palette from one user-picked color.
    # Darker/lighter transforms keep contrast and hierarchy consistent.
    return AccentPalette(
        border=QColor(base).darker(135).name(QColor.NameFormat.HexRgb),
        border_bright=QColor(base).lighter(108).name(QColor.NameFormat.HexRgb),
        fill=QColor(base).darker(195).name(QColor.NameFormat.HexRgb),
        fill_hover=QColor(base).darker(165).name(QColor.NameFormat.HexRgb),
        fill_active=QColor(base).darker(225).name(QColor.NameFormat.HexRgb),
        list_hover=_LIST_HOVER_NEUTRAL,
    )


def load_saved_accent_palette() -> tuple[AccentPalette, str]:
    """Return (palette, preset_key) where preset_key is 'green'…'red' or 'custom'."""
    s = QSettings()
    # Keep the user's last accent choice between sessions.
    key = s.value("theme/accent_preset", "green", str)
    if key == "custom":
        hexv = s.value("theme/accent_custom", "#247a3d", str)
        qc = QColor(hexv)
        if not qc.isValid():
            return accent_palette_from_preset("green"), "green"
        return accent_palette_from_qcolor(qc), "custom"
    if key in ACCENT_PRESETS:
        return accent_palette_from_preset(key), key
    return accent_palette_from_preset("green"), "green"


def build_app_stylesheet(a: AccentPalette) -> str:
    # Centralized QSS keeps visual behavior deterministic and makes runtime
    # accent swaps cheap (just rebuild and re-apply this one string).
    return f"""
QMainWindow {{
    background-color: {_THEME_BG};
    color: {_THEME_TEXT};
}}
QWidget {{
    background-color: transparent;
    color: {_THEME_TEXT};
}}
QFrame#sideBar {{
    background-color: {_THEME_CARD_DEEP};
    border: 2px solid {a.border};
    border-radius: 16px;
    min-width: 72px;
    max-width: 72px;
}}
QFrame#topHeader {{
    background-color: {_THEME_CARD};
    border: 2px solid {a.border};
    border-radius: 16px;
    padding: 4px;
}}
QFrame#bodyCard {{
    background-color: {_THEME_CARD};
    border: 2px solid {a.border};
    border-radius: 18px;
}}
QFrame#navColumn {{
    background-color: {_THEME_CARD_DEEP};
    border: 2px solid {a.border};
    border-radius: 16px;
}}
QFrame#centerStack {{
    background-color: transparent;
    border: none;
}}
QFrame#commandColumn {{
    background-color: {_THEME_CARD_DEEP};
    border: 2px solid {a.border};
    border-radius: 16px;
}}
QFrame#innerListCard {{
    background-color: {_THEME_CARD_DEEP};
    border: 2px solid {a.border};
    border-radius: 14px;
}}
QFrame#mixedSection {{
    background-color: {_THEME_CARD};
    border: 2px solid {a.border};
    border-radius: 14px;
}}
QLabel#mixedHint {{
    font-size: 11px;
    color: {_THEME_MUTED};
    background: transparent;
}}
QFrame#reviewBanner {{
    background-color: {_THEME_CARD_DEEP};
    color: {_THEME_TEXT};
    border: 2px solid {a.border_bright};
    border-radius: 14px;
    padding: 8px;
}}
QLabel#AppTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {_THEME_TEXT};
    background: transparent;
    padding: 4px 8px;
}}
QLabel#CaptionMuted {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    color: {_THEME_MUTED};
    background: transparent;
}}
QLabel#ProfileBadge {{
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    border-radius: 22px;
    background-color: {_THEME_CARD_DEEP};
    border: 2px solid {a.border};
    color: {_THEME_TEXT};
    font-weight: 700;
    font-size: 13px;
}}
QLabel#SectionTitle {{
    font-weight: 600;
    font-size: 13px;
    color: {_THEME_TEXT};
    background: transparent;
}}
QLabel#PreviewPane {{
    background-color: {_THEME_CARD_DEEP};
    color: {_THEME_TEXT};
    border: 2px solid {a.border};
    border-radius: 14px;
    padding: 12px;
}}
QLabel#sideLogo {{
    font-weight: 800;
    font-size: 14px;
    color: {_THEME_TEXT};
    background: transparent;
    padding: 8px 4px;
}}
QToolButton#sideNavBtn {{
    border: 2px solid transparent;
    border-radius: 14px;
    background-color: transparent;
    min-width: 48px;
    max-width: 48px;
    min-height: 48px;
    max-height: 48px;
    padding: 0px;
}}
QToolButton#sideNavBtn:hover {{
    border: 2px solid {a.border};
    background-color: {_THEME_CARD};
}}
QToolButton#sideNavBtn:checked {{
    border: 2px solid {a.border_bright};
    background-color: {a.fill};
}}
QToolButton#modeNavBtn {{
    text-align: left;
    padding: 12px 14px;
    min-height: 44px;
    border-radius: 14px;
    border: 2px solid {a.border};
    background-color: {_THEME_CARD};
    color: {_THEME_TEXT};
    font-weight: 500;
}}
QToolButton#modeNavBtn:checked {{
    border: 2px solid {a.border_bright};
    background-color: {a.fill};
    font-weight: 700;
}}
QToolButton#modeNavBtn:hover {{
    background-color: {a.fill_hover};
}}
QPushButton#actionBtn {{
    padding: 12px 16px;
    min-height: 44px;
    border-radius: 14px;
    border: 2px solid {a.border};
    background-color: {_THEME_CARD};
    color: {_THEME_TEXT};
    font-weight: 600;
}}
QPushButton#actionBtn:hover {{
    background-color: {a.fill_hover};
    border-color: {a.border_bright};
}}
QPushButton#actionBtn:pressed {{
    background-color: {a.fill_active};
}}
QPushButton#primaryAccentBtn {{
    padding: 12px 16px;
    min-height: 44px;
    border-radius: 14px;
    border: 2px solid {a.border_bright};
    background-color: {a.fill};
    color: {_THEME_TEXT};
    font-weight: 700;
}}
QPushButton#primaryAccentBtn:hover {{
    background-color: {a.fill_hover};
}}
QListWidget {{
    background-color: {_THEME_CARD_DEEP};
    color: {_THEME_TEXT};
    border: none;
    border-radius: 10px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 8px;
    border-radius: 10px;
}}
QListWidget::item:selected {{
    background-color: {a.fill};
    border: 1px solid {a.border_bright};
}}
QListWidget::item:hover {{
    background-color: {a.list_hover};
}}
QLineEdit#headerSearch {{
    background-color: {_THEME_CARD_DEEP};
    color: {_THEME_TEXT};
    border: 2px solid {a.border};
    border-radius: 16px;
    padding: 10px 16px;
    font-size: 13px;
    min-height: 20px;
}}
QLineEdit#titleField {{
    background-color: {_THEME_CARD};
    color: {_THEME_TEXT};
    border: 2px solid {a.border};
    border-radius: 12px;
    padding: 10px 12px;
}}
QSpinBox#rosterSpin {{
    background-color: {_THEME_CARD};
    color: {_THEME_TEXT};
    border: 2px solid {a.border};
    border-radius: 12px;
    padding: 6px 10px;
    min-height: 32px;
}}
QSpinBox#rosterSpin::up-button, QSpinBox#rosterSpin::down-button {{
    width: 22px;
    border-left: 1px solid {a.border};
    background: {_THEME_CARD_DEEP};
}}
QProgressBar {{
    border: 2px solid {a.border};
    border-radius: 12px;
    height: 18px;
    text-align: center;
    background-color: {_THEME_CARD};
    color: {_THEME_TEXT};
}}
QProgressBar::chunk {{
    background-color: {a.border};
    border-radius: 8px;
}}
QSplitter::handle {{
    background-color: {_THEME_CARD_DEEP};
    width: 4px;
    margin: 4px 0;
    border-radius: 2px;
}}
QScrollBar:vertical {{
    background: {_THEME_CARD_DEEP};
    width: 10px;
    margin: 4px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {a.border};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar:horizontal {{
    height: 0px;
}}
QCheckBox {{
    color: {_THEME_MUTED};
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 40px;
    height: 22px;
    border-radius: 11px;
    border: 2px solid {a.border};
    background: {_THEME_CARD};
}}
QCheckBox::indicator:checked {{
    background: {a.fill};
    border-color: {a.border_bright};
}}
"""


class ThemeSettingsDialog(QDialog):
    """Accent presets + custom color picker; changes persist via QSettings."""

    def __init__(self, parent: MainWindow) -> None:
        super().__init__(parent)
        self._mw = parent
        self.setWindowTitle("Theme & accent color")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        root.setSpacing(12)
        intro = QLabel(
            "Dark gray layout stays the same. Pick a highlight color for borders, "
            "buttons, progress, and selections — like the default green.",
            self,
        )
        intro.setWordWrap(True)
        intro.setObjectName("CaptionMuted")
        root.addWidget(intro)

        grid = QGridLayout()
        grid.setSpacing(10)
        # Curated presets provide predictable contrast across the full UI.
        presets: list[tuple[str, str]] = [
            ("green", "Green"),
            ("yellow", "Yellow"),
            ("orange", "Orange"),
            ("hot_pink", "Hot pink"),
            ("blue", "Blue"),
            ("red", "Red"),
        ]
        for i, (key, title) in enumerate(presets):
            sw = ACCENT_PRESETS[key][1]
            edge = ACCENT_PRESETS[key][0]
            btn = QPushButton(title, self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {sw}; color: #ffffff; font-weight: 600; "
                f"min-height: 40px; border-radius: 12px; border: 2px solid {edge}; padding: 6px; }}"
                f"QPushButton:hover {{ border: 2px solid #ffffff; }}"
            )
            btn.clicked.connect(lambda _=False, k=key, t=title: self._apply_preset(k, t))
            grid.addWidget(btn, i // 3, i % 3)
        root.addLayout(grid)

        custom = QPushButton("Pick custom color…", self)
        custom.setObjectName("actionBtn")
        custom.clicked.connect(self._pick_custom)
        root.addWidget(custom)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.accept)
        root.addWidget(bb)

    def _apply_preset(self, key: str, title: str) -> None:
        # Delegate all persistence + repainting to the main window.
        pal = accent_palette_from_preset(key)
        self._mw._apply_accent_palette(pal, key, None)
        self._mw._status.setText(f"Theme accent: {title}.")

    def _pick_custom(self) -> None:
        # Start picker from the current bright accent so users fine-tune from
        # what they already see instead of jumping from an arbitrary default.
        initial = QColor(self._mw._accent.border_bright)
        c = QColorDialog.getColor(initial, self, "Accent highlight color")
        if not c.isValid():
            return
        pal = accent_palette_from_qcolor(c)
        hex_name = c.name(QColor.NameFormat.HexRgb)
        self._mw._apply_accent_palette(pal, "custom", hex_name)
        self._mw._status.setText(f"Theme accent: custom ({hex_name}).")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Homework Grader")
        self.setMinimumSize(1020, 640)

        self._answer_key_path: Path | None = None
        self._submissions_folder: Path | None = None
        # Number of items requiring manual review after a grading run.
        self._low_confidence_count: int = 0
        # Imported names from roster spreadsheet, used for quick sanity checks.
        self._roster_names: list[str] = []
        self._accent, self._accent_preset_key = load_saved_accent_palette()

        self._build_actions()
        self._build_ui()
        self.setStyleSheet(build_app_stylesheet(self._accent))
        self.menuBar().hide()

    def _apply_accent_palette(
        self, palette: AccentPalette, preset_key: str, custom_hex: str | None
    ) -> None:
        self._accent = palette
        self._accent_preset_key = preset_key
        self.setStyleSheet(build_app_stylesheet(palette))
        s = QSettings()
        # Save theme settings immediately so a restart restores this look.
        s.setValue("theme/accent_preset", preset_key)
        if custom_hex is not None:
            s.setValue("theme/accent_custom", custom_hex)
        elif preset_key != "custom":
            s.remove("theme/accent_custom")

    def _open_theme_dialog(self) -> None:
        ThemeSettingsDialog(self).exec()

    def _build_actions(self) -> None:
        # Actions are reused by both menu entries and direct UI controls.
        # Keeping wiring here avoids duplicated trigger logic in `_build_ui`.
        self._act_answer_key = QAction("Set answer key (PDF)…", self)
        self._act_answer_key.triggered.connect(self._on_set_answer_key)
        self._act_export = QAction("Export grades…", self)
        self._act_export.triggered.connect(self._on_export_grades)
        self._act_roster = QAction("Import roster (Excel or Calc)…", self)
        self._act_roster.triggered.connect(self._on_import_roster)
        self._act_run_grade = QAction("Run grading (stub)…", self)
        self._act_run_grade.triggered.connect(self._on_run_grading_stub)
        self._act_theme = QAction("Theme & accent color…", self)
        self._act_theme.setStatusTip("Highlight color for borders and controls (presets or custom).")
        self._act_theme.triggered.connect(self._open_theme_dialog)

        self._act_quit = QAction("Quit", self)
        self._act_quit.triggered.connect(self.close)

    def _make_side_nav_button(self, icon: QStyle.StandardPixmap, tip: str, checkable: bool = False) -> QToolButton:
        # Helper for consistent icon-only sidebar buttons.
        btn = QToolButton(self)
        btn.setObjectName("sideNavBtn")
        btn.setIcon(self.style().standardIcon(icon))
        btn.setIconSize(QSize(22, 22))
        btn.setToolTip(tip)
        btn.setCheckable(checkable)
        btn.setAutoRaise(True)
        return btn

    def _build_ui(self) -> None:
        # High-level layout:
        # - Left: icon rail (global shortcuts/menu access)
        # - Center: main working surface (lists + preview)
        # - Right: task controls and status indicators
        central = QWidget(self)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(14)

        # --- Icon sidebar (dashboard style) ---
        side = QFrame(self)
        side.setObjectName("sideBar")
        side_v = QVBoxLayout(side)
        side_v.setContentsMargins(8, 14, 8, 14)
        side_v.setSpacing(10)

        logo = QLabel("HG", self)
        logo.setObjectName("sideLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_side_home = self._make_side_nav_button(
            QStyle.StandardPixmap.SP_DirHomeIcon, "Workspace overview", checkable=True
        )
        self._btn_side_home.setChecked(True)
        self._btn_side_review = self._make_side_nav_button(
            QStyle.StandardPixmap.SP_MessageBoxWarning, "Review queue (placeholder)", checkable=False
        )
        self._btn_side_review.clicked.connect(self._on_review_placeholder)

        self._btn_side_settings = QToolButton(self)
        self._btn_side_settings.setObjectName("sideNavBtn")
        self._btn_side_settings.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))
        self._btn_side_settings.setIconSize(QSize(22, 22))
        self._btn_side_settings.setToolTip("Menu")
        self._btn_side_settings.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(self)
        # Surface the same QAction objects used elsewhere for one source of truth.
        m.addAction(self._act_answer_key)
        m.addAction(self._act_export)
        m.addAction(self._act_roster)
        m.addSeparator()
        m.addAction(self._act_run_grade)
        m.addSeparator()
        m.addAction(self._act_theme)
        m.addSeparator()
        m.addAction(self._act_quit)
        self._btn_side_settings.setMenu(m)

        side_v.addWidget(logo)
        side_v.addWidget(self._btn_side_home)
        side_v.addWidget(self._btn_side_review)
        side_v.addStretch(1)
        side_v.addWidget(self._btn_side_settings)
        outer.addWidget(side)

        # --- Main column: header + body card ---
        main_col = QWidget(self)
        main_v = QVBoxLayout(main_col)
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.setSpacing(12)

        header = QFrame(self)
        header.setObjectName("topHeader")
        header_l = QHBoxLayout(header)
        header_l.setContentsMargins(14, 10, 14, 10)
        header_l.setSpacing(14)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        app_title = QLabel("Homework Grader", self)
        app_title.setObjectName("AppTitle")
        subtitle = QLabel("Canvas-ready PDF workflow", self)
        subtitle.setObjectName("CaptionMuted")
        title_block.addWidget(app_title)
        title_block.addWidget(subtitle)

        self._search_edit = QLineEdit(self)
        self._search_edit.setObjectName("headerSearch")
        self._search_edit.setPlaceholderText("Search submissions…")
        self._search_edit.setClearButtonEnabled(True)
        # Search is client-side: hide non-matching rows in-place as user types.
        self._search_edit.textChanged.connect(self._on_search_changed)

        profile = QLabel("TA", self)
        profile.setObjectName("ProfileBadge")
        profile.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_l.addLayout(title_block, stretch=0)
        header_l.addWidget(self._search_edit, stretch=1)
        header_l.addWidget(profile, stretch=0)

        body = QFrame(self)
        body.setObjectName("bodyCard")
        body_l = QHBoxLayout(body)
        body_l.setContentsMargins(14, 14, 14, 14)
        body_l.setSpacing(14)

        # --- Left: workflow nav (like DEVICES column) ---
        nav = QFrame(self)
        nav.setObjectName("navColumn")
        nav.setMinimumWidth(200)
        nav.setMaximumWidth(280)
        nav_v = QVBoxLayout(nav)
        nav_v.setContentsMargins(12, 12, 12, 12)
        nav_v.setSpacing(10)

        cap_work = QLabel("WORKFLOW", self)
        cap_work.setObjectName("CaptionMuted")

        self._btn_math = QToolButton(self)
        self._btn_math.setObjectName("modeNavBtn")
        self._btn_math.setText("  Math grading")
        self._btn_math.setCheckable(True)
        self._btn_math.setChecked(True)
        self._btn_math.setToolTip("Technical math and notation (fractions, roots, symbols).")
        self._btn_written = QToolButton(self)
        self._btn_written.setObjectName("modeNavBtn")
        self._btn_written.setText("  Written grading")
        self._btn_written.setCheckable(True)
        self._btn_written.setToolTip("Short answers and prose-style responses (PDF).")

        self._btn_mixed = QToolButton(self)
        self._btn_mixed.setObjectName("modeNavBtn")
        self._btn_mixed.setText("  Mixed (per question)")
        self._btn_mixed.setCheckable(True)
        self._btn_mixed.setToolTip(
            "Same assignment uses math-style grading for some questions and written-style for others. "
            "Define which below (stub list until the answer key is linked)."
        )

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        # Exactly one grading mode should be active at a time.
        self._mode_group.addButton(self._btn_math)
        self._mode_group.addButton(self._btn_written)
        self._mode_group.addButton(self._btn_mixed)
        self._mode_group.idClicked.connect(self._on_mode_changed)

        self._mixed_section = QFrame(self)
        self._mixed_section.setObjectName("mixedSection")
        self._mixed_section.setVisible(False)
        self._mixed_section.setMinimumHeight(140)
        mixed_l = QVBoxLayout(self._mixed_section)
        mixed_l.setContentsMargins(10, 10, 10, 10)
        mixed_l.setSpacing(6)
        cap_mix = QLabel("PER-QUESTION TYPES", self)
        cap_mix.setObjectName("CaptionMuted")
        hint_mix = QLabel(
            "Each question can be marked Math or Written. "
            "The grader will use the right model per item.",
            self,
        )
        hint_mix.setObjectName("mixedHint")
        hint_mix.setWordWrap(True)
        self._mixed_question_list = QListWidget(self)
        # Placeholder until rubric/question extraction from answer key is wired.
        self._mixed_question_list.setToolTip(
            "Example layout: final app will read rubric sections from your answer key PDF."
        )
        mixed_l.addWidget(cap_mix)
        mixed_l.addWidget(hint_mix)
        mixed_l.addWidget(self._mixed_question_list, stretch=1)

        self._btn_load_folder = QPushButton("Load submissions folder", self)
        self._btn_load_folder.setObjectName("actionBtn")
        self._btn_load_folder.clicked.connect(self._on_load_submissions_folder)

        self._btn_train = QPushButton("Handwriting training", self)
        self._btn_train.setObjectName("actionBtn")
        self._btn_train.setToolTip(
            "Per-student samples (~100 per symbol). Target ≥80% accuracy; ensemble preferred."
        )
        self._btn_train.clicked.connect(self._on_handwriting_training)

        nav_v.addWidget(cap_work)
        nav_v.addWidget(self._btn_math)
        nav_v.addWidget(self._btn_written)
        nav_v.addWidget(self._btn_mixed)
        nav_v.addWidget(self._mixed_section, stretch=1)
        nav_v.addSpacing(6)
        nav_v.addWidget(self._btn_load_folder)
        nav_v.addWidget(self._btn_train)
        nav_v.addStretch(1)
        body_l.addWidget(nav)

        # --- Center: dual panes in splitter ---
        center = QFrame(self)
        center.setObjectName("centerStack")
        center_v = QVBoxLayout(center)
        center_v.setContentsMargins(0, 0, 0, 0)
        center_v.setSpacing(10)

        cap_pipe = QLabel("SUBMISSIONS & OUTPUTS", self)
        cap_pipe.setObjectName("CaptionMuted")

        self._review_banner = QFrame(self)
        self._review_banner.setObjectName("reviewBanner")
        self._review_banner.setVisible(False)
        bl = QHBoxLayout(self._review_banner)
        bl.setContentsMargins(8, 6, 8, 6)
        self._review_banner_label = QLabel(self)
        self._review_banner_label.setWordWrap(True)
        bl.addWidget(self._review_banner_label)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        # Splitter allows users to bias space toward inputs or outputs as needed.

        sub_card = QFrame(self)
        sub_card.setObjectName("innerListCard")
        sub_l = QVBoxLayout(sub_card)
        sub_l.setContentsMargins(10, 10, 10, 10)
        lh = QLabel("Student submissions", self)
        lh.setObjectName("SectionTitle")
        self._submissions_list = QListWidget(self)
        # Keep selected filename mirrored into the right control panel.
        self._submissions_list.currentItemChanged.connect(self._on_submission_changed)
        sub_l.addWidget(lh)
        sub_l.addWidget(self._submissions_list, stretch=1)

        out_card = QFrame(self)
        out_card.setObjectName("innerListCard")
        out_l = QVBoxLayout(out_card)
        out_l.setContentsMargins(10, 10, 10, 10)
        rh = QLabel("Graded outputs", self)
        rh.setObjectName("SectionTitle")
        self._graded_list = QListWidget(self)
        # Preview panel is text-only placeholder until PDF rendering is integrated.
        self._graded_list.currentItemChanged.connect(self._on_graded_changed)
        self._preview_label = QLabel(
            "Select a graded output to preview.\n\n"
            "Graded PDFs will show score / max points, percentage, and ✓ / ✗ marks.",
            self,
        )
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._preview_label.setWordWrap(True)
        self._preview_label.setMinimumHeight(100)
        self._preview_label.setObjectName("PreviewPane")
        out_l.addWidget(rh)
        out_l.addWidget(self._graded_list, stretch=1)
        out_l.addWidget(self._preview_label, stretch=0)

        splitter.addWidget(sub_card)
        splitter.addWidget(out_card)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 400])

        center_v.addWidget(cap_pipe)
        center_v.addWidget(self._review_banner)
        center_v.addWidget(splitter, stretch=1)
        body_l.addWidget(center, stretch=1)

        # --- Right: quick commands column ---
        cmd = QFrame(self)
        cmd.setObjectName("commandColumn")
        cmd.setMinimumWidth(248)
        cmd.setMaximumWidth(320)
        cmd_v = QVBoxLayout(cmd)
        cmd_v.setContentsMargins(12, 12, 12, 12)
        cmd_v.setSpacing(12)

        cap_cmd = QLabel("QUICK ACTIONS", self)
        cap_cmd.setObjectName("CaptionMuted")

        cap_roster = QLabel("ROSTER", self)
        cap_roster.setObjectName("CaptionMuted")
        cap_expected = QLabel("Expected students", self)
        cap_expected.setObjectName("CaptionMuted")
        self._spin_expected = QSpinBox(self)
        self._spin_expected.setObjectName("rosterSpin")
        self._spin_expected.setRange(1, 500)
        self._spin_expected.setValue(30)
        self._spin_expected.setToolTip("Target headcount for this assignment (for comparison with the imported list).")
        self._spin_expected.valueChanged.connect(lambda _v: self._update_roster_summary())

        self._btn_roster_import = QPushButton("Import names (Excel or Calc)…", self)
        self._btn_roster_import.setObjectName("actionBtn")
        self._btn_roster_import.setToolTip(
            "First column of the first sheet: one name per row. "
            "Use .xlsx / .xlsm (Excel) or .ods (LibreOffice Calc)."
        )
        self._btn_roster_import.clicked.connect(self._on_import_roster)

        self._roster_summary = QLabel(self)
        self._roster_summary.setObjectName("CaptionMuted")
        self._roster_summary.setWordWrap(True)
        self._update_roster_summary()

        cap_file = QLabel("SELECTED FILE", self)
        cap_file.setObjectName("CaptionMuted")
        self._title_edit = QLineEdit(self)
        self._title_edit.setObjectName("titleField")
        self._title_edit.setReadOnly(True)
        self._title_edit.setPlaceholderText("No file selected")

        cap_prog = QLabel("PROGRESS", self)
        cap_prog.setObjectName("CaptionMuted")
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._status = QLabel("Ready.", self)
        self._status.setWordWrap(True)
        self._status.setObjectName("CaptionMuted")
        f = QFont(self._status.font())
        f.setPointSize(max(9, f.pointSize()))
        self._status.setFont(f)

        self._btn_answer = QPushButton("Answer key (PDF)", self)
        self._btn_answer.setObjectName("primaryAccentBtn")
        self._btn_answer.clicked.connect(self._on_set_answer_key)

        self._btn_export = QPushButton("Export grades", self)
        self._btn_export.setObjectName("actionBtn")
        self._btn_export.clicked.connect(self._on_export_grades)

        self._btn_grade = QPushButton("Run grading (stub)", self)
        self._btn_grade.setObjectName("actionBtn")
        self._btn_grade.clicked.connect(self._on_run_grading_stub)

        self._chk_alerts = QCheckBox("Low-confidence alerts", self)
        self._chk_alerts.setChecked(True)
        self._chk_alerts.setToolTip("When on, the banner highlights items needing human review.")
        self._chk_alerts.toggled.connect(lambda _c: self._refresh_review_banner())

        cmd_v.addWidget(cap_cmd)
        cmd_v.addWidget(cap_roster)
        cmd_v.addWidget(cap_expected)
        cmd_v.addWidget(self._spin_expected)
        cmd_v.addWidget(self._btn_roster_import)
        cmd_v.addWidget(self._roster_summary)
        cmd_v.addSpacing(8)
        cmd_v.addWidget(cap_file)
        cmd_v.addWidget(self._title_edit)
        cmd_v.addWidget(cap_prog)
        cmd_v.addWidget(self._progress)
        cmd_v.addWidget(self._status)
        cmd_v.addWidget(self._btn_answer)
        cmd_v.addWidget(self._btn_export)
        cmd_v.addWidget(self._btn_grade)
        cmd_v.addWidget(self._chk_alerts)
        cmd_v.addStretch(1)
        body_l.addWidget(cmd)

        main_v.addWidget(header)
        main_v.addWidget(body, stretch=1)
        outer.addWidget(main_col, stretch=1)

        self.setCentralWidget(central)
        # Initial sync to respect default mode + default alert toggle.
        self._refresh_review_banner()
        self._sync_mixed_section()

    def _on_review_placeholder(self) -> None:
        QMessageBox.information(
            self,
            "Review queue",
            "Low-confidence items will appear here for verification before you export to Excel / Calc.",
        )

    def _refresh_review_banner(self) -> None:
        # Banner is governed by both data state (count) and user preference.
        show = self._low_confidence_count > 0 and self._chk_alerts.isChecked()
        if show:
            self._review_banner.setVisible(True)
            self._review_banner_label.setText(
                f"Low confidence: {self._low_confidence_count} item(s) — review before export."
            )
        else:
            self._review_banner.setVisible(False)

    def _on_search_changed(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self._submissions_list.count()):
            item = self._submissions_list.item(i)
            if not item:
                continue
            name = item.text().lower()
            # Keep placeholder rows visible so empty/error states still read clearly.
            item.setHidden(bool(needle) and needle not in name and not name.startswith("("))

    def _update_roster_summary(self) -> None:
        # Compare imported roster count against expected headcount and present a
        # human-readable mismatch summary for quick data quality checks.
        n = len(self._roster_names)
        exp = self._spin_expected.value()
        if n == 0:
            self._roster_summary.setText(f"No roster file yet · expecting {exp} students.")
            return
        if n == exp:
            self._roster_summary.setText(f"{n} name(s) loaded — matches expected count.")
        elif n < exp:
            self._roster_summary.setText(
                f"{n} name(s) loaded · expecting {exp} ({exp - n} fewer than expected)."
            )
        else:
            self._roster_summary.setText(
                f"{n} name(s) loaded · expecting {exp} ({n - exp} more than expected — check duplicates)."
            )

    def _on_import_roster(self) -> None:
        path_str, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Import student roster",
            str(Path.home()),
            "Excel (*.xlsx *.xlsm);;LibreOffice Calc (*.ods);;All spreadsheets (*.xlsx *.xlsm *.ods)",
        )
        if not path_str:
            return
        roster_path = Path(path_str)
        try:
            # Reader handles .xlsx/.xlsm/.ods and normalization details.
            names = read_student_names(roster_path)
        except ValueError as e:
            QMessageBox.warning(self, "Roster", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "Roster", f"Could not read the spreadsheet:\n{e}")
            return
        if not names:
            QMessageBox.information(
                self,
                "Roster",
                "No names were found in the first column of the first sheet. "
                "Put one student per row in column A.",
            )
            return
        self._roster_names = names
        self._update_roster_summary()
        self._status.setText(f"Roster loaded: {len(names)} student name(s) from “{roster_path.name}”.")

    def _sync_mixed_section(self) -> None:
        mixed = self._btn_mixed.isChecked()
        self._mixed_section.setVisible(mixed)
        if mixed:
            # Seed demo rows once until question extraction from the answer key exists.
            self._ensure_mixed_stub_items()

    def _ensure_mixed_stub_items(self) -> None:
        # Populate once so toggling in/out of mixed mode does not duplicate rows.
        if self._mixed_question_list.count() > 0:
            return
        examples = [
            "Question 1 — Math",
            "Question 2 — Written",
            "Question 3 — Math",
            "Question 4 — Written",
        ]
        for line in examples:
            self._mixed_question_list.addItem(QListWidgetItem(line))

    def _on_mode_changed(self, _id: int) -> None:
        # Keep UI and status text aligned with whichever mode is active.
        self._sync_mixed_section()
        if self._btn_math.isChecked():
            label = "Math (all questions)"
        elif self._btn_written.isChecked():
            label = "Written (all questions)"
        else:
            label = "Mixed — math + written by question"
        self._status.setText(f"Mode: {label}. Load submissions and set an answer key when ready.")

    def _on_load_submissions_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select folder of student submissions",
            str(self._submissions_folder or Path.home()),
        )
        if not path:
            return
        self._submissions_folder = Path(path)
        self._submissions_list.clear()
        # Reset search so all newly loaded items are visible by default.
        self._search_edit.clear()

        # Current grading pipeline expects PDFs; non-PDF files are only reported for now.
        pdfs = sorted(p.name for p in self._submissions_folder.iterdir() if p.suffix.lower() == ".pdf")
        others = [p for p in self._submissions_folder.iterdir() if p.is_file() and p.suffix.lower() != ".pdf"]
        for name in pdfs:
            self._submissions_list.addItem(QListWidgetItem(name))

        if not pdfs:
            self._submissions_list.addItem(QListWidgetItem("(No PDF files in this folder)"))

        extra = ""
        if others:
            extra = (
                f" {len(others)} non-PDF file(s) — in production these go to a review folder."
            )
        self._status.setText(f"Loaded {len(pdfs)} PDF(s) from “{self._submissions_folder.name}”.{extra}")
        self._progress.setValue(0)

    def _on_handwriting_training(self) -> None:
        QMessageBox.information(
            self,
            "Handwriting training",
            "Students submit a PDF with many samples of letters, numbers, fractions, roots, and parentheses "
            "(e.g. ~100 repetitions per symbol).\n\n"
            "Target ≥ 80% accuracy per student; an ensemble model is preferred.\n\n"
            "Placeholder until training is implemented.",
        )

    def _on_set_answer_key(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Select answer key PDF",
            str(self._answer_key_path.parent if self._answer_key_path else Path.home()),
            "PDF files (*.pdf);;All files (*.*)",
        )
        if not path:
            return
        self._answer_key_path = Path(path)
        self._status.setText(f"Answer key: {self._answer_key_path.name}")

    def _on_export_grades(self) -> None:
        QMessageBox.information(
            self,
            "Export grades",
            "Exports to Excel when installed, otherwise LibreOffice Calc when detected.\n\n"
            "Graded PDFs for Canvas will be written to your chosen output folder.",
        )

    def _on_run_grading_stub(self) -> None:
        if self._submissions_list.count() == 0 or (
            self._submissions_list.count() == 1
            and self._submissions_list.item(0).text().startswith("(")
        ):
            QMessageBox.warning(self, "Run grading", "Load a folder that contains student PDFs first.")
            return

        self._progress.setRange(0, 0)
        # Indeterminate progress bar while simulated work is "running".
        self._status.setText("Grading (stub)…")

        def finish_stub() -> None:
            # Simulate outputs so the rest of the UI can be exercised end-to-end.
            self._progress.setRange(0, 100)
            self._progress.setValue(100)
            self._graded_list.clear()
            for i in range(self._submissions_list.count()):
                item = self._submissions_list.item(i)
                text = item.text()
                if text.startswith("("):
                    # Skip informational placeholder rows.
                    continue
                self._graded_list.addItem(QListWidgetItem(f"graded_{text}"))
            # Produce a non-zero review count so banner behavior can be tested.
            self._low_confidence_count = min(3, max(1, self._graded_list.count()))
            self._refresh_review_banner()
            self._status.setText(
                f"Stub run complete. {self._graded_list.count()} output(s). "
                f"{self._low_confidence_count} low-confidence — review before export."
            )

        # Delay mimics asynchronous grading completion.
        QTimer.singleShot(900, finish_stub)

    def _on_submission_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None or current.text().startswith("("):
            self._title_edit.clear()
            return
        self._title_edit.setText(current.text())

    def _on_graded_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self._preview_label.setText(
                "Select a graded output to preview.\n\n"
                "Graded PDFs will show score / max points, percentage, and ✓ / ✗ marks."
            )
            return
        name = current.text()
        self._preview_label.setText(
            f"Preview placeholder: {name}\n\n"
            "Renders PDF with marks, points earned vs possible, and percentage by student name."
        )
