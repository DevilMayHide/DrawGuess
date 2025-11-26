import sys
from PyQt5.QtWidgets import QApplication
from ui_main import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 默认连接本地，实际使用可修改 IP
    host = "127.0.0.1"
    port = 9000
    
    win = MainWindow(host, port)
    win.show()
    
    sys.exit(app.exec_())
