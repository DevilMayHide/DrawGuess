from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QPixmap, QColor
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

class DrawWidget(QWidget):
    local_draw = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        
        # 初始画布
        self._pixmap = QPixmap(800, 600)
        self._draw_grid() # 初始化时画网格
        
        self._last_pos = None
        self.pen_color = QColor("#000000")
        self.pen_width = 3
        
        self._interactive = False
        self.setAttribute(Qt.WA_StaticContents)

    def _draw_grid(self):
        """画出米黄色网格背景"""
        # 1. 填充米黄色背景 (Warm Beige)
        self._pixmap.fill(QColor("#fcf6e5")) 
        
        painter = QPainter(self._pixmap)
        
        # 2. 设置网格线颜色 (Faint Gray)
        grid_pen = QPen(QColor("#e0dcd0"))
        grid_pen.setWidth(1)
        grid_pen.setStyle(Qt.SolidLine)
        painter.setPen(grid_pen)

        # 3. 画线 (间隔 20 像素)
        step = 20
        w = self._pixmap.width()
        h = self._pixmap.height()

        # 竖线
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        # 横线
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

        painter.end()
        self.update()

    def clear_canvas(self):
        """清空画布 = 重画网格"""
        self._draw_grid()

    def set_interactive(self, enabled):
        self._interactive = enabled
        if not enabled:
            self._last_pos = None

    def set_pen_color(self, color_str):
        self.pen_color = QColor(color_str)

    def set_pen_width(self, width):
        self.pen_width = int(width)

    def resizeEvent(self, event):
        if event.size().width() > self._pixmap.width() or \
           event.size().height() > self._pixmap.height():
            new_w = max(event.size().width(), self._pixmap.width())
            new_h = max(event.size().height(), self._pixmap.height())
            new_pix = QPixmap(new_w, new_h)
            
            # 扩展时先填白色防黑底，然后把旧图画上去
            new_pix.fill(Qt.white) 
            p = QPainter(new_pix)
            p.drawPixmap(0, 0, self._pixmap)
            p.end()
            
            self._pixmap = new_pix
            # 注意：resize 后新区域暂时是白的，直到下次 clear_canvas
            # 也可以在这里调用 _draw_grid 重新铺满，但会清空当前画作
            # 简单起见，保持原样即可，通常窗口不会频繁拉太大
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
            self._draw_line_on_pixmap(self._last_pos, curr_pos, self.pen_color, self.pen_width)
            self.update()
            
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