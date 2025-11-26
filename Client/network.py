import socket
import sys
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from Shared.protocol import encode_message, decode_stream

class NetworkClient(QThread):
    # 信号定义
    message_received = pyqtSignal(dict)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, host, port, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.sock = None
        self._running = False

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self._running = True
            self.connected.emit()
        except OSError as e:
            self.error_occurred.emit(f"无法连接到服务器: {e}")
            self.disconnected.emit()
            return

        buffer = ""
        while self._running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                
                buffer += data.decode("utf-8", errors="ignore")
                msgs, buffer = decode_stream(buffer)
                for msg in msgs:
                    self.message_received.emit(msg)
            except OSError:
                # socket 被关闭或网络错误
                break
            except Exception as e:
                print(f"Receive Error: {e}")
                break

        self._cleanup()

    def send_message(self, obj):
        if not self.sock or not self._running:
            return
        try:
            self.sock.sendall(encode_message(obj))
        except OSError as e:
            print(f"Send Error: {e}")
            self.error_occurred.emit("发送失败，网络连接可能已断开")

    def stop(self):
        """安全停止线程"""
        self._running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass

    def _cleanup(self):
        self._running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.disconnected.emit()