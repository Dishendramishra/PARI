from subprocess import Popen, PIPE, STDOUT
import sys
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from time import sleep
import traceback, sys


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

    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(str)

class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        self.kwargs['progress_callback'] = self.signals.progress


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

        self.threadpool = QThreadPool()
        vbox = QGridLayout()
        
        self.btn = QPushButton(self,text="Click")
        # self.btn.clicked.connect(lambda: self.spawn_thread(self.test, self.test_progress, self.test_done))
        self.btn.clicked.connect(lambda: self.spawn_thread(self.owl, self.owl_progress, self.owl_done))
        self.progressbar = QProgressBar()
        self.progressbar.setMinimum(0)
        self.progressbar.setMaximum(100)
        self.progressbar.setValue(0)

        vbox.addWidget(self.btn,0,0)
        vbox.addWidget(self.progressbar,1,0)

        self.setLayout(vbox)
        self.show()

    def spawn_thread(self, fn_name, fn_progress, fn_result_handler):
        worker = Worker(fn_name)

        if fn_result_handler:
            worker.signals.result.connect(fn_result_handler)
        if fn_progress:
            worker.signals.progress.connect(fn_progress)
        
        self.threadpool.start(worker)

    # ==============================================================
    #   Simple Counter Function
    # ==============================================================
    def test(self,progress_callback):
        self.btn.setDisabled(True)
        for i in range(1,11):
            sleep(0.3)
            progress_callback.emit(i*10)

    def test_progress(self,n):
        self.progressbar.setValue(n)

    def test_done(self):
        print("thread done!")
        self.btn.setDisabled(False)
    # ==============================================================


    # ==============================================================
    #   ARC API functions 
    # ==============================================================
    def owl(self, progress_callback):
        self.arc = ArcWrapper("C:\\Users\\ryzen5\\Desktop\\POC\\api\\arcapi.exe PCIe")

        for line in self.arc.process.stdout:
            line = line.decode("utf-8")
            if line.startswith("Error") or line.startswith("( CArcPCIe"):
                progress_callback.emit(line)
                break
            progress_callback.emit(line)

        # progress_callback.emit(self.arc.read_stdout())

    def owl_progress(self,n):
        print(n)

    def owl_done(self):
        print("exposure thread completed!")
    # ==============================================================
    
            


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    app.exec_()
    sys.exit()