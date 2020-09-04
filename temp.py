from subprocess import Popen, PIPE, STDOUT
import sys
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

class ArcWrapper():
    def __init__(self,cmd):
        
        cmd = cmd.split()
        self.process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    def write_stdin(self,cmd):
        print(colored("grive: ","blue"),end="")
        print(colored(cmd,"red"))
        cmd = cmd+"\n"
        self.process.stdin.write(cmd.encode())
        self.process.stdin.flush()

    def read_stdout(self, break_flag=None):
        text  = []
        for line in self.process.stdout:
            line = line.decode("utf-8")
            text.append(line)

            if break_flag and line.startswith(break_flag):
                break

        return text        

    def kill(self):
        self.process.kill()

class WorkerSignals(QObject):

    finished = Signal()  # QtCore.Signal
    error = Signal(tuple)
    result = Signal(object)

class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()


    @Slot()  # QtCore.Slot
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn( 
                        *self.args, 
                        **self.kwargs)
                        # status=self.signals.status,
                        # progress=self.signals.progress)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

        else:
            self.signals.result.emit(result)  # Return the result of the processing

        finally:
            self.signals.finished.emit()  # Done
            

class App(QWidget):

    def __init__(self):
        super().__init__()

        vbox = QGridLayout()
        self.btn = QPushButton(self,text="Click")
        self.btn.clicked.connect(self.click)
        vbox.addWidget(self.btn,0,0)
        
        self.setLayout(vbox)
        self.show()

        self.threadpool = QThreadPool()

    def click(self):
        
        print("clicked")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    app.exec_()
    sys.exit()