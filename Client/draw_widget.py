from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QPixmap, QColor, QCursor, QBitmap, QImage
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

class DrawWidget(QWidget):
    local_draw = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        
        # === 颜色定义 ===
        self.bg_color = QColor("#fcf6e5")  # 米黄背景
        self.grid_color = QColor("#e0dcd0") # 网格线颜色
        
        # === 图层系统 (关键修改) ===
        # 1. 网格层：只存背景和网格，永远不变
        self._grid_layer = QPixmap(800, 600)
        # 2. 绘画层：背景透明，只存笔迹
        self._drawing_layer = QPixmap(800, 600)
        
        # 初始化图层
        self._init_layers()
        
        # === 绘图状态 ===
        self._last_pos = None
        self.pen_color = QColor("#000000")
        self.pen_width = 3
        
        # 历史记录
        self.history = []
        self.current_stroke = []
        self.remote_stroke_buffer = []
        
        self._interactive = False
        self.setAttribute(Qt.WA_StaticContents)
        self.setMouseTracking(True) # 开启鼠标追踪以便更新光标

        # === 初始化光标 ===
        self._init_cursors()
        self.set_pen_cursor() # 默认光标

    def _init_layers(self):
        """初始化两个图层"""
        # 1. 绘制网格层 (实色背景)
        self._grid_layer.fill(self.bg_color)
        painter = QPainter(self._grid_layer)
        grid_pen = QPen(self.grid_color)
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        
        step = 20
        w = self._grid_layer.width()
        h = self._grid_layer.height()
        for x in range(0, w, step): painter.drawLine(x, 0, x, h)
        for y in range(0, h, step): painter.drawLine(0, y, w, y)
        painter.end()

        # 2. 绘制绘画层 (全透明)
        self._drawing_layer.fill(Qt.transparent)

    def _init_cursors(self):
        """在内存中动态绘制光标图标，无需外部图片文件"""
        
        # --- 1. 制作画笔光标 (Pen Cursor) ---
        pen_pix = QPixmap(32, 32)
        pen_pix.fill(Qt.transparent)
        p = QPainter(pen_pix)
        p.setRenderHint(QPainter.Antialiasing)
        
        # 画笔杆
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#45475a")) # 深灰笔杆
        # 坐标点模拟一个倾斜的笔
        p.drawPolygon(QPoint(4, 28), QPoint(18, 14), QPoint(24, 20), QPoint(10, 32))
        # 画笔尖
        p.setBrush(QColor("#f5c2e7")) # 粉色笔头
        p.drawPolygon(QPoint(0, 32), QPoint(4, 28), QPoint(10, 32))
        p.end()
        # 热点设在左下角 (0, 32)
        self.cursor_pen = QCursor(pen_pix, 0, 31)

        # --- 2. 制作橡皮光标 (Eraser Cursor) ---
        eraser_pix = QPixmap(32, 32)
        eraser_pix.fill(Qt.transparent)
        p = QPainter(eraser_pix)
        p.setRenderHint(QPainter.Antialiasing)
        
        # 画一个方块橡皮
        p.setPen(QPen(QColor("#1e1e2e"), 2))
        p.setBrush(QColor("#ffffff"))
        p.drawRect(6, 6, 20, 20)
        # 橡皮擦蓝套
        p.setBrush(QColor("#89b4fa"))
        p.drawRect(6, 18, 20, 8)
        p.end()
        # 热点设在中心
        self.cursor_eraser = QCursor(eraser_pix, 16, 16)

    # === 光标切换 ===
    def set_pen_cursor(self):
        if self._interactive:
            self.setCursor(self.cursor_pen)
        else:
            self.setCursor(Qt.ArrowCursor)

    def set_eraser_cursor(self):
        if self._interactive:
            self.setCursor(self.cursor_eraser)
        else:
            self.setCursor(Qt.ArrowCursor)

    # === 重写绘图事件 (关键：叠加图层) ===
    def paintEvent(self, event):
        painter = QPainter(self)
        # 1. 先画网格层 (底)
        painter.drawPixmap(0, 0, self._grid_layer)
        # 2. 再画笔迹层 (顶)
        painter.drawPixmap(0, 0, self._drawing_layer)

    def resizeEvent(self, event):
        """窗口大小改变时，扩展图层"""
        new_size = event.size()
        if new_size.width() > self._grid_layer.width() or \
           new_size.height() > self._grid_layer.height():
            
            new_w = max(new_size.width(), self._grid_layer.width())
            new_h = max(new_size.height(), self._grid_layer.height())
            
            # 扩展网格层
            new_grid = QPixmap(new_w, new_h)
            new_grid.fill(self.bg_color)
            p = QPainter(new_grid)
            p.drawPixmap(0, 0, self._grid_layer)
            # 补画新增区域的网格 (为了简单，这里直接重画整个网格最省事)
            # 实际生产中应只画新增部分，这里偷懒重置一下
            p.end()
            self._grid_layer = new_grid
            self._init_layers() # 重新铺满网格

            # 扩展绘画层
            new_draw = QPixmap(new_w, new_h)
            new_draw.fill(Qt.transparent)
            p = QPainter(new_draw)
            p.drawPixmap(0, 0, self._drawing_layer)
            p.end()
            self._drawing_layer = new_draw

        super().resizeEvent(event)

    # === 核心画线逻辑 ===
    def _draw_line_on_pixmap(self, data):
        """在绘画层上画线"""
        start = QPoint(data.get("x1"), data.get("y1"))
        end = QPoint(data.get("x2"), data.get("y2"))
        color_str = data.get("color", "#000000")
        width = data.get("width", 3)

        painter = QPainter(self._drawing_layer) # 注意：只画在顶层
        painter.setRenderHint(QPainter.Antialiasing)

        # === 核心：橡皮擦逻辑判断 ===
        # 如果颜色等于背景色，说明是橡皮擦模式
        # 此时我们要把 CompositionMode 设为 Clear (变透明)
        is_eraser = (QColor(color_str) == self.bg_color)

        if is_eraser:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            # 橡皮擦实际上是在画“透明线”
            # 注意：setPen 的颜色不重要，重要的是 Alpha 通道，但为了保险依然用透明
            pen = QPen(Qt.transparent, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor(color_str), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()

    def _redraw_from_history(self):
        """重绘历史：先清空绘画层，再重放"""
        self._drawing_layer.fill(Qt.transparent) # 只清空顶层，网格层不动
        
        for stroke in self.history:
            for seg in stroke:
                self._draw_line_on_pixmap(seg)
        self.update()

    # === 接口 ===
    def set_interactive(self, enabled):
        self._interactive = enabled
        if not enabled:
            self._last_pos = None
            self.setCursor(Qt.ArrowCursor)
        else:
            # 恢复当前工具的光标
            if self.pen_color == self.bg_color:
                self.set_eraser_cursor()
            else:
                self.set_pen_cursor()

    def set_pen_color(self, color_str):
        self.pen_color = QColor(color_str)
        self.set_pen_cursor() # 切换回画笔光标

    def set_pen_width(self, width):
        self.pen_width = int(width)

    def set_eraser_mode(self):
        """切换到橡皮擦模式"""
        # 逻辑上，橡皮擦依然是画“背景色”的线，
        # 但在 _draw_line_on_pixmap 里会被识别并转换为“透明模式”
        self.pen_color = self.bg_color 
        self.pen_width = 20
        self.set_eraser_cursor() # 切换光标

    def undo(self):
        if self.history:
            self.history.pop()
            self._redraw_from_history()
            self.local_draw.emit({"action": "undo"})

    def clear_all(self):
        self.history.clear()
        self._drawing_layer.fill(Qt.transparent) # 清空顶层
        self.update()
        self.local_draw.emit({"action": "clear"})

    # === 鼠标事件 ===
    def mousePressEvent(self, event):
        if not self._interactive: return
        if event.button() == Qt.LeftButton:
            self._last_pos = event.pos()
            self.current_stroke = []

    def mouseMoveEvent(self, event):
        if not self._interactive: return
        if (event.buttons() & Qt.LeftButton) and self._last_pos:
            curr_pos = event.pos()
            segment = {
                "action": "move",
                "x1": self._last_pos.x(), "y1": self._last_pos.y(),
                "x2": curr_pos.x(), "y2": curr_pos.y(),
                "color": self.pen_color.name(),
                "width": self.pen_width
            }
            self._draw_line_on_pixmap(segment)
            self.current_stroke.append(segment)
            self.update() # 触发 paintEvent 合成图层
            self.local_draw.emit(segment)
            self._last_pos = curr_pos

    def mouseReleaseEvent(self, event):
        if not self._interactive: return
        if event.button() == Qt.LeftButton:
            if self.current_stroke:
                self.history.append(self.current_stroke)
                self.current_stroke = []
                self.local_draw.emit({"action": "end"})
            self._last_pos = None

    # === 远程绘图处理 ===
    def draw_remote_line(self, data):
        action = data.get("action")
        if action == "move":
            self._draw_line_on_pixmap(data)
            self.update()
            self.remote_stroke_buffer.append(data)
        elif action == "end":
            if self.remote_stroke_buffer:
                self.history.append(self.remote_stroke_buffer)
                self.remote_stroke_buffer = []
        elif action == "undo":
            if self.history:
                self.history.pop()
                self._redraw_from_history()
        elif action == "clear":
            self.clear_all_local_only()

    def clear_all_local_only(self):
        self.history.clear()
        self._drawing_layer.fill(Qt.transparent)
        self.update()