from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QPixmap, QColor
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

class DrawWidget(QWidget):
    local_draw = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        
        self._pixmap = QPixmap(800, 600)
        self._pixmap.fill(Qt.white)
        
        self._last_pos = None
        self.pen_color = QColor("#000000")
        self.pen_width = 3
        
        # 是否允许用户绘画（只有画手为True）
        self._interactive = False
        
        self.setAttribute(Qt.WA_StaticContents)

    def set_interactive(self, enabled):
        self._interactive = enabled
        if not enabled:
            self._last_pos = None

    def set_pen_color(self, color_str):
        self.pen_color = QColor(color_str)

    def set_pen_width(self, width):
        self.pen_width = int(width)

    def clear_canvas(self):
        self._pixmap.fill(Qt.white)
        self.update()

    def resizeEvent(self, event):
        # 动态调整画布大小，保留原内容
        if event.size().width() > self._pixmap.width() or \
           event.size().height() > self._pixmap.height():
            new_w = max(event.size().width(), self._pixmap.width())
            new_h = max(event.size().height(), self._pixmap.height())
            new_pix = QPixmap(new_w, new_h)
            new_pix.fill(Qt.white)
            p = QPainter(new_pix)
            p.drawPixmap(0, 0, self._pixmap)
            p.end()
            self._pixmap = new_pix
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._pixmap)

    def mousePressEvent(self, event):
        if not self._interactive: return
        if event.button() == Qt.LeftButton:
            self._last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if not self._interactive: return
        if (event.buttons() & Qt.LeftButton) and self._last_pos:
            curr_pos = event.pos()
            # 1. 本地画
            self._draw_line_on_pixmap(self._last_pos, curr_pos, self.pen_color, self.pen_width)
            self.update()
            # 2. 发送信号
            self.local_draw.emit({
                "x1": self._last_pos.x(), "y1": self._last_pos.y(),
                "x2": curr_pos.x(), "y2": curr_pos.y(),
                "color": self.pen_color.name(),
                "width": self.pen_width
            })
            self._last_pos = curr_pos

    def mouseReleaseEvent(self, event):
        if not self._interactive: return
        if event.button() == Qt.LeftButton:
            self._last_pos = None

    def draw_remote_line(self, data):
        """绘制来自网络的线段"""
        start = QPoint(data.get("x1"), data.get("y1"))
        end = QPoint(data.get("x2"), data.get("y2"))
        color = QColor(data.get("color", "#000000"))
        width = data.get("width", 3)
        
        self._draw_line_on_pixmap(start, end, color, width)
        self.update()

    def _draw_line_on_pixmap(self, start, end, color, width):
        p = QPainter(self._pixmap)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.drawLine(start, end)
        p.end()