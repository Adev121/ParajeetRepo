import sys
import re
import html as _html
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QTextBrowser, QSizeGrip
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QCursor


def _md_to_html(text: str) -> str:
    """Convert Markdown to styled HTML for QTextBrowser."""

    def render_block(t: str) -> str:
        t = _html.escape(t)
        # Headers (largest first to avoid partial match)
        t = re.sub(r'^### (.+)$', r'<h3>\1</h3>', t, flags=re.MULTILINE)
        t = re.sub(r'^## (.+)$',  r'<h2>\1</h2>', t, flags=re.MULTILINE)
        t = re.sub(r'^# (.+)$',   r'<h1>\1</h1>', t, flags=re.MULTILINE)
        # Bold + italic, bold, italic
        t = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><em>\1</em></b>', t)
        t = re.sub(r'\*\*(.+?)\*\*',     r'<b>\1</b>', t)
        t = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', t)
        # Inline code
        t = re.sub(
            r'`([^`]+)`',
            r'<code style="background:rgba(15,15,28,0.85);color:#e6edf3;'
            r'padding:1px 6px;border-radius:3px;font-family:Consolas,monospace;font-size:13px;">\1</code>',
            t
        )
        # Horizontal rule
        t = re.sub(r'^---+$', '<hr/>', t, flags=re.MULTILINE)
        # Lists
        lines = t.split('\n')
        out, in_ul, in_ol = [], False, False
        for line in lines:
            m_ul = re.match(r'^[-*•] (.+)$', line)
            m_ol = re.match(r'^\d+\. (.+)$', line)
            if m_ul:
                if in_ol: out.append('</ol>'); in_ol = False
                if not in_ul: out.append('<ul>'); in_ul = True
                out.append(f'<li>{m_ul.group(1)}</li>')
            elif m_ol:
                if in_ul: out.append('</ul>'); in_ul = False
                if not in_ol: out.append('<ol>'); in_ol = True
                out.append(f'<li>{m_ol.group(1)}</li>')
            else:
                if in_ul: out.append('</ul>'); in_ul = False
                if in_ol: out.append('</ol>'); in_ol = False
                out.append(line)
        if in_ul: out.append('</ul>')
        if in_ol: out.append('</ol>')
        t = '\n'.join(out)
        # Newlines → <br/> except after block-level tags
        t = re.sub(r'\n(?!<(?:/?(ul|ol|li|h[1-6]|hr|div|pre)))', '<br/>', t)
        return t

    # Split on fenced code blocks  ```lang\ncode```
    parts = re.split(r'```(\w*)\n?(.*?)```', text, flags=re.DOTALL)
    html_out = []
    for i, part in enumerate(parts):
        r = i % 3
        if r == 0:
            html_out.append(render_block(part))
        elif r == 2:
            lang  = parts[i - 1]
            code  = _html.escape(part.rstrip())
            badge = (f'<span style="color:#8b949e;font-size:11px;font-family:\'Segoe UI\';">'
                     f'{lang}</span><br/>' if lang else '')
            html_out.append(
                f'<div style="background:rgba(15,15,28,0.92);border:1px solid rgba(255,255,255,0.18);'
                f'border-radius:6px;padding:10px 14px;margin:6px 0;">'
                f'{badge}'
                f'<pre style="margin:0;color:#e6edf3;white-space:pre-wrap;'
                f'font-family:Consolas,monospace;font-size:13px;">{code}</pre></div>'
            )

    body = ''.join(html_out)
    return (
        "<html><body style=\"color:rgba(255,255,255,0.92);font-family:'Segoe UI';"
        "font-size:15px;margin:0;padding:0;background:transparent;\">"
        "<style>"
        "h1{font-size:18px;color:white;margin:10px 0 4px;}"
        "h2{font-size:16px;color:white;margin:8px 0 3px;}"
        "h3{font-size:15px;color:white;margin:6px 0 2px;}"
        "ul,ol{margin:4px 0;padding-left:20px;}"
        "li{margin:3px 0;}"
        "b{color:white;}"
        "hr{border:0;border-top:1px solid rgba(255,255,255,0.2);margin:8px 0;}"
        "</style>"
        f"{body}</body></html>"
    )

class OverlayWindow(QMainWindow):
    toggle_signal        = pyqtSignal()
    click_through_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._drag_pos = QPoint()
        self._dragging = False
        self.btn_screen = None
        self.btn_audio  = None
        self.btn_passthrough = None
        self._visible       = True
        self._click_through = False
        self.initUI()
        self.toggle_signal.connect(self.toggle_visibility)
        self.click_through_signal.connect(self.toggle_click_through)

    def initUI(self):
        # Frameless, always-on-top, no taskbar entry, NO WindowTransparentForInput so buttons work
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        screen = QApplication.primaryScreen().geometry()
        width = 680
        height = 580
        x = (screen.width() - width) // 2
        y = 20
        self.setGeometry(x, y, width, height)

        # Root container — this gets the rounded transparent look
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(10, 7, 10, 7)
        top_bar_layout.setSpacing(6)

        title_lbl = QLabel("⚡ ParakeetAI")
        title_lbl.setObjectName("titleLabel")
        top_bar_layout.addWidget(title_lbl)
        top_bar_layout.addStretch()

        self.btn_screen      = QPushButton("📸  Analyze Screen")
        self.btn_audio       = QPushButton("🎙  Listen Audio")
        self.btn_passthrough = QPushButton("🖱")
        self.btn_toggle      = QPushButton("▼")
        btn_close            = QPushButton("✕")

        for btn in (self.btn_screen, self.btn_audio):
            btn.setFixedHeight(26)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setObjectName("actionBtn")

        for btn in (self.btn_passthrough, self.btn_toggle, btn_close):
            btn.setFixedSize(26, 26)
            btn.setObjectName("closeBtn")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.btn_passthrough.setToolTip("Toggle Click-Through  (Ctrl+Alt+C)")
        self.btn_passthrough.clicked.connect(self.toggle_click_through)
        self.btn_toggle.setToolTip("Hide / Show  (Ctrl+Shift+H)")
        self.btn_toggle.clicked.connect(self.toggle_visibility)
        btn_close.clicked.connect(QApplication.quit)

        top_bar_layout.addWidget(self.btn_screen)
        top_bar_layout.addWidget(self.btn_audio)
        top_bar_layout.addWidget(self.btn_passthrough)
        top_bar_layout.addWidget(self.btn_toggle)
        top_bar_layout.addSpacing(10)
        top_bar_layout.addWidget(btn_close)

        root_layout.addWidget(top_bar)

        # ── Divider ──────────────────────────────────────────────────
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setObjectName("divider")
        root_layout.addWidget(divider)

        # ── Chat response view ───────────────────────────────────────
        self.response_view = QTextBrowser()
        self.response_view.setObjectName("responseView")
        self.response_view.setReadOnly(True)
        self.response_view.setOpenExternalLinks(False)
        self.response_view.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.response_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(self.response_view, 1)

        # ── Resize grip (bottom-right) ───────────────────────────────
        bottom_bar = QWidget()
        bottom_bar.setObjectName("bottomBar")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 4, 4)
        bottom_layout.addStretch()
        grip = QSizeGrip(self)
        grip.setObjectName("sizeGrip")
        bottom_layout.addWidget(grip)
        root_layout.addWidget(bottom_bar)

        # ── Global stylesheet ────────────────────────────────────────
        self.setStyleSheet("""
            QWidget#root {
                background-color: rgba(8, 8, 18, 120);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 35);
            }
            QWidget#topBar {
                background-color: rgba(255, 255, 255, 12);
                border-radius: 11px 11px 0px 0px;
            }
            QLabel#titleLabel {
                color: rgba(255, 255, 255, 220);
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 700;
                background: transparent;
            }
            QPushButton#actionBtn {
                background-color: rgba(255, 255, 255, 18);
                color: rgba(255, 255, 255, 230);
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 5px;
                padding: 2px 10px;
                font-family: "Segoe UI";
                font-size: 16px;
            }
            QPushButton#actionBtn:hover {
                background-color: rgba(255, 255, 255, 38);
                border: 1px solid rgba(255, 255, 255, 80);
            }
            QPushButton#actionBtn:pressed {
                background-color: rgba(255, 255, 255, 60);
            }
            QPushButton#closeBtn {
                background-color: transparent;
                color: rgba(255, 255, 255, 160);
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-family: "Segoe UI";
            }
            QPushButton#closeBtn:hover {
                background-color: rgba(220, 50, 50, 160);
                color: white;
            }
            QWidget#divider {
                background-color: rgba(255, 255, 255, 25);
            }
            QTextBrowser#responseView {
                background: transparent;
                color: rgba(255, 255, 255, 225);
                font-family: "Segoe UI";
                font-size: 15px;
                font-weight: 600;
                border: none;
                padding: 10px 12px;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 8);
                width: 5px;
                border-radius: 3px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 50);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            QWidget#bottomBar {
                background: transparent;
                max-height: 18px;
            }
            QSizeGrip#sizeGrip {
                width: 14px;
                height: 14px;
                background: transparent;
                image: none;
            }
            QSizeGrip#sizeGrip:hover {
                background: rgba(255,255,255,30);
                border-radius: 3px;
            }
        """)

        # Set initial ready message
        self.update_text(
            "Assistant Ready.\n\n"
            "Hotkeys:\n"
            "- **Ctrl+Shift+S** — Analyze Screen\n"
            "- **Ctrl+Shift+A** — Listen Audio\n"
            "- **Ctrl+Shift+H** — Hide / Show window\n"
            "- **Ctrl+Alt+C** — Toggle Click-Through\n\n"
            "Drag the top bar to move. Drag bottom-right corner to resize."
        )

    def update_text(self, text):
        self.response_view.setHtml(_md_to_html(text))

    def toggle_click_through(self):
        """Toggle Windows click-through using WS_EX_TRANSPARENT."""
        self._click_through = not self._click_through
        GWL_EXSTYLE      = -20
        WS_EX_LAYERED    = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        hwnd  = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if self._click_through:
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            )
            self.btn_passthrough.setText("🖱✓")
            self.btn_passthrough.setStyleSheet(
                "background-color: rgba(80,200,120,120) !important;"
                "border-radius:4px;"
            )
        else:
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT
            )
            self.btn_passthrough.setText("🖱")
            self.btn_passthrough.setStyleSheet("")

    def toggle_visibility(self):
        """Hide the response area keeping the top bar visible, or restore fully."""
        self._visible = not self._visible
        for child in self.centralWidget().children():
            if hasattr(child, 'setVisible') and child.objectName() in ('responseView', 'divider'):
                child.setVisible(self._visible)
        self.btn_toggle.setText("▲" if not self._visible else "▼")
        if not self._visible:
            self.setFixedHeight(self.centralWidget().layout().itemAt(0).widget().sizeHint().height() + 16)
        else:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.resize(self.width(), 580)

    # ── Drag to move (top bar acts as title bar) ─────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._dragging = True

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OverlayWindow()
    window.show()
    sys.exit(app.exec())
