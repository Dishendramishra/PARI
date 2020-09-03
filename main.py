from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import tess_api 
import simbad_api

import traceback, sys

if sys.platform == "linux" or sys.platform == "linux2":
    pass

elif sys.platform == "win32":
    import ctypes
    myappid = u'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

elif sys.platform == "darwin":
    pass


class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data
    
    error
        `tuple` (exctype, value, traceback.format_exc() )
    
    result
        `object` data returned from processing, anything

    '''
    finished = Signal()  # QtCore.Signal
    error = Signal(tuple)
    result = Signal(object)

class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

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
            
class POC(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("POC")
        self.setGeometry(300,200,500,350)
        self.setIcon()
        self.creategui()
        vbox = QGridLayout()
        vbox.addWidget(self.grp_box_actns,0,0)
        vbox.addWidget(self.grp_box_exp,1,0)
        vbox.addWidget(self.grp_box_logger,0,1,3,1)
        vbox.addWidget(self.grp_box_source,2,0)
        vbox.setColumnStretch(1,1)
        
        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.setLayout(vbox)
        # self.logger_window()
        self.show()

    def setIcon(self):
        appIcon = QIcon()
        appIcon.addFile("icons/prl.png")
        self.setWindowIcon(appIcon)

        # system tray icon
        # self.tray = QSystemTrayIcon()
        # self.tray.setIcon(appIcon)
        # self.tray.setVisible(True)

    def spawn_thread(self,fn_name,fn_result_handler):
        worker = Worker(fn_name)
        worker.signals.result.connect(fn_result_handler)
        self.threadpool.start(worker)


    def get_src_info(self):
        name = self.source_name.text()
        name = name.replace(" ","")
        name = name.lower()

        info = "None"
        if name[:3] == "toi":
            info = tess_api.get_planet_data([name])
        elif name[:2] == "hd":
            info = simbad_api.get_planet_data([name])
        else:
            return None

        print(info)
        return info

    def set_src_info(self, info):
        if info == None:
            self.source_info.clear()
            self.source_info.textCursor().insertHtml("Invalid Source Name! <br>")
            return None
        self.source_info.clear()
        self.source_info.textCursor().insertHtml("RA: "+info[0][1]+"<br>")
        self.source_info.textCursor().insertHtml("Dec: "+info[0][2]+"<br>")

    def creategui(self):

        # ===========================================================
        #                       Quick Actions
        # ===========================================================
        self.grp_box_actns = QGroupBox("Quick Actions")
        self.actns_layout = QBoxLayout(QBoxLayout.LeftToRight)

        # self.actns_layout.setAlignment(AlignTop)
        self.btn_ctrl_rst = QPushButton( self)
        self.btn_ctrl_rst.setIcon(QIcon("icons/ResetCtlr.gif"))
        self.btn_ctrl_rst.setIconSize(QSize(40,40))
        self.actns_layout.addWidget(self.btn_ctrl_rst)
        
        self.btn_poweron = QPushButton(self)
        self.btn_poweron.setIcon(QIcon("icons/PowerOn.gif"))
        self.btn_poweron.setIconSize(QSize(40,40))
        self.actns_layout.addWidget(self.btn_poweron)

        self.btn_poweroff = QPushButton(self)
        self.btn_poweroff.setIcon(QIcon("icons/PowerOff.gif"))
        self.btn_poweroff.setIconSize(QSize(40,40))
        self.actns_layout.addWidget(self.btn_poweroff)

        self.btn_ds9 = QPushButton(self)
        self.btn_ds9.setIcon(QIcon("icons/ds9.png"))
        self.btn_ds9.setIconSize(QSize(40,40))
        self.actns_layout.addWidget(self.btn_ds9)

        # self.actns_layout.addStretch(0)
        self.grp_box_actns.setLayout(self.actns_layout)

        # ===========================================================
        #                     Exposure Options
        # ===========================================================
        self.grp_box_exp = QGroupBox("Exposure Options")
        self.gridLayout_exp = QGridLayout()

        self.chk_btn_exp_time = QCheckBox("Exp. Time",self)
        self.input_exp_time = QLineEdit(self)
        self.input_exp_time.setDisabled(True)
        self.gridLayout_exp.addWidget(self.chk_btn_exp_time,0,0)
        self.gridLayout_exp.addWidget(self.input_exp_time,0,1)

        self.chk_btn_exp_delay = QCheckBox("Delay Exposure(sec)",self)
        self.input_exp_delay = QLineEdit(self)
        self.input_exp_delay.setDisabled(True)
        self.gridLayout_exp.addWidget(self.chk_btn_exp_delay,1,0)
        self.gridLayout_exp.addWidget(self.input_exp_delay,1,1)

        self.chk_btn_exp_multi = QCheckBox("Multiple Exposure",self)
        self.input_exp_multi = QLineEdit(self)
        self.input_exp_multi.setDisabled(True)
        self.gridLayout_exp.addWidget(self.chk_btn_exp_multi,2,0)
        self.gridLayout_exp.addWidget(self.input_exp_multi,2,1)

        self.grp_box_exp.setLayout(self.gridLayout_exp)


        # ===========================================================
        #                     Logger
        # ===========================================================
        self.grp_box_logger = QGroupBox("Logger")
        self.gridLayout_logger = QGridLayout()

        self.txt_logger = QTextEdit(self)
        self.gridLayout_logger.addWidget(self.txt_logger)

        self.grp_box_logger.setLayout(self.gridLayout_logger)

        # ===========================================================
        #                     Source Details
        # ===========================================================
        self.grp_box_source = QGroupBox("Source Details")
        self.gridLayout_source = QGridLayout()

        self.source_lbl = QLabel(self,text="Source Name:")
        self.gridLayout_source.addWidget(self.source_lbl,0,0)
        
        self.source_name = QLineEdit(self)
        self.gridLayout_source.addWidget(self.source_name,0,1)
        
        self.source_btn = QPushButton(self,text="submit")
        self.gridLayout_source.addWidget(self.source_btn,1,0,1,2)
        self.source_btn.clicked.connect(lambda: self.spawn_thread(self.get_src_info, self.set_src_info))

        self.source_info = QTextEdit(self)
        self.source_info.setReadOnly(True)
        self.gridLayout_source.addWidget(self.source_info,2,0,1,2)

        self.grp_box_source.setLayout(self.gridLayout_source)
    
    def logger_window(self):
        self.logger = QMainWindow()
        self.logger.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = POC()
    app.setWindowIcon(QIcon("icons/prl.png"))
    app.exec_()
    sys.exit()