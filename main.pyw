from posixpath import basename
from typing import Text
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from modules import tess_api
from modules import simbad_api
from subprocess import Popen, PIPE, STDOUT
from time import perf_counter, sleep, time
import os, re, glob
from pathlib import Path
from pprint import pprint

from astropy.io import fits

import traceback
import sys

import serial
import serial.tools.list_ports
from time import sleep
import pynmea2

from datetime import datetime
from arcwrapper import ArcWrapper
from hashlib import sha256

from modules import fits_utilities
import json

if sys.platform == "linux" or sys.platform == "linux2":
    pass

elif sys.platform == "win32":
    import ctypes
    myappid = u'mycompany.myproduct.subproduct.version'  # arbitrary string
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
    progress = Signal(str)


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
            # Return the result of the processing
            self.signals.result.emit(result)

        finally:
            self.signals.finished.emit()  # Done


class PARI(QWidget):

    def __init__(self):
        super().__init__()

        self.EXP_TIMES = {
        "Dark"        :   "100",
        "Dark+Tung"   :   "600",
        "Tung+Dark"   :   "400",
        "UAr+UAr"     :   "400",
        "Dark+UAr"    :   "600",
        "ThAr+ThAr"   :   "400",
        "Dark+ThAr"   :   "1200",
        "Star+UAr"    :   "1800",
        "Star+ThAr"   :   "1800",
        "Star+Dark"   :   "1800"}


        self.setMinimumWidth(846)
        # ===============================================================================
        #   Dummy Widgets for filling space
        # ===============================================================================
        self.dummy_txt = QTextEdit(self)
        self.dummy_txt.setStyleSheet("border: 0px;")
        self.dummy_txt.setDisabled(True)

        self.dummy_line = QLineEdit(self)
        self.dummy_line.setStyleSheet("border: 0px; background:transparent")
        self.dummy_line.setDisabled(True)
        # ===============================================================================

        self.setWindowTitle("PARI (Paras Aquisition and Readout Initiation)")
        self.setGeometry(300, 200, 500, 350)
        self.setIcon()
        self.creategui()

        self.main_layout = QGridLayout()

        self.left_pane = QVBoxLayout()
        self.left_pane.setSpacing(10)
        self.left_pane.setMargin(5)

        self.middle_pane = QVBoxLayout()
        self.middle_pane.setSpacing(15)

        self.right_pane = QVBoxLayout()
        self.right_pane.setSpacing(15)

        self.main_layout.addLayout(self.left_pane, 0, 0)
        self.main_layout.addLayout(self.middle_pane, 0, 1)
        self.main_layout.addLayout(self.right_pane, 0, 2)

        self.main_layout.setColumnStretch(2, 1)

        self.left_pane.addWidget(self.grp_box_actns)
        self.left_pane.addWidget(self.grp_box_exp)
        self.left_pane.addWidget(self.grp_box_img_file_ops)
        self.left_pane.addWidget(self.grp_box_source)
        self.left_pane.addStretch()

        self.middle_pane.addWidget(self.grp_box_observation)

        # self.right_pane.addWidget(self.grp_box_status)
        self.right_pane.addWidget(self.grp_box_logger)

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" %
              self.threadpool.maxThreadCount())

        self.setLayout(self.main_layout)
        # self.logger_window()
        self.show()

        self.shutter_thread_flag = True
        self.gps_flag = True
        self.readout_time_flag = False
        self.readout_starttime = None
        self.exp_delay_flag = False
        # self.spawn_thread(self.shutter_status_thread, None, None)
        # self.spawn_thread(self.gps_thread, None, None)
        self.exp_start_time = None

        self.arc = ArcWrapper()

    def closeEvent(self, event):
        self.save_settings()
        self.ds9_kill()
        try:
            self.arc.kill()
            print("ARCAPI: closed!")
        except:
            print("ARCAPI: error closing!")

        self.shutter_thread_flag = False
        self.gps_flag = False
        self.threadpool.clear()
        print("closing PARI...")

    def setIcon(self):
        appIcon = QIcon()
        appIcon.addFile("resources/icons/prl2.png")
        self.setWindowIcon(appIcon)

        # system tray icon
        # self.tray = QSystemTrayIcon()
        # self.tray.setIcon(appIcon)
        # self.tray.setVisible(True)

    def spawn_thread(self, fn_name, fn_progress, fn_result_handler):

        if fn_name.__name__ == "get_src_info":
            self.source_info.clear()
            self.source_info.insertHtml("Getting details ....")

        worker = Worker(fn_name)

        if fn_progress:
            worker.signals.progress.connect(fn_progress)
        if fn_result_handler:
            worker.signals.result.connect(fn_result_handler)

        self.threadpool.start(worker)

    def log(self, msg, color="black", end="<br>"):
        self.txt_logger.textCursor().insertHtml("<font color='{}'>{}</font>{}".format(color,msg,end))

    # ==============================================================
    #   ARC API functions
    # ==============================================================

    #  Exposure Functions
    # -----------------------------------------------------------

    def expose_handler(self):
        try:
            os.remove("exposure.dat")
        except:
            pass

        self.btn_expose.setDisabled(True)
        self.btn_abort.setEnabled(True)
        self.progressbar_exp.reset()    #The progress bar “rewinds” and shows no progress
        self.spawn_thread(self.expose_thread, self.expose_progress, None)
        self.exp_start_time = datetime.utcnow().strftime("%H:%M:%S")

    def expose_thread(self, progress_callback):

        exp_time = exp_time = float(self.input_exp_time.text())
        
        shutter = 1 if self.chk_btn_open_shutter.checkState() else 0
        
        for i in range(int(self.input_exp_multi.text())):

            self.handle_fits_filename()
            fits_file_name = self.input_img_dir.text().strip()+"/"+self.lbl_img_fn_val.text().strip()

            if self.chk_btn_exp_delay.checkState():
                delay = int(self.input_exp_delay.text().strip())
                
                self.exp_delay_flag = True
                start = time() 

                while self.exp_delay_flag:
                    current = int(time()-start)
                    if  current >= delay:
                        self.exp_delay_flag = False
                    else:
                        self.lbl_readout_time.setText("Waiting: {} secs".format(current+1))

            # start exposure here
            print(exp_time, fits_file_name, shutter)
            self.arc.take_exposure(exp_time, shutter, fits_file_name)

            # for i in range(int(exp_time),0,-1):
            #     self.progressbar_exp_label.setText("Waiting: "+str(i))
            #     sleep(1)
            # self.progressbar_exp_label.setText("")

            for line in self.arc.process.stdout:
                line = line.decode("utf-8").strip()

                progress_callback.emit(line)

                if line.startswith("Enter any key to"):
                    self.arc.write_stdin("")
                    self.expose_done()
                    break
            # progress_callback.emit(self.arc.read_stdout())

    def expose_progress(self, line):
        # print(line)

        if line.startswith("Err") or line.startswith("( CArcDevice"):

            if "Expose Aborted!" in line:
                self.log("<b>Exposure Aborted !</b>","red")
                self.log("<b>It is advised to Clear Camera Array.</b>", "blue")
            else:
                self.log("Exposure Error: ",end=" ")
                self.log("failed!","red")

        elif line.startswith("Elapsed Time"):
            self.lbl_readout_time.setText("Elapsed Time: {}".format(line[line.find(":")+2:]))

        elif line.startswith("Pixel Count:"):

            if not self.readout_time_flag:
                self.readout_time_flag = True
                self.readout_starttime = time()
            
            self.lbl_readout_time.setText("Readout Time: {}".format(round(time()-self.readout_starttime,2)))

            count = int(line[line.find(":")+2:])
            self.progressbar_exp.setValue(int(count/43400000*100))

    def expose_done(self):
        image_path = self.input_img_dir.text()+"/"+self.lbl_img_fn_val.text().strip()
        
        # source_name = self.source_name.text().strip().lower()
        # if source_name.startswith("toi"):
            # source_name = tess_api.tic_from_toi(source_name)
        # source_details = tess_api.get_obj_details(source_name)
        observers  = self.input_observers_name.toPlainText().strip().replace("\n","")

        data = fits.getdata(image_path)
        hdu = fits.PrimaryHDU(data)
        header = hdu.header

        header["OBS_DATE"] = datetime.utcnow().strftime("%Y-%m-%d")  , "Observation date"
        # header["OBS AIRM"] = round(source_details["airmass"],2)      , "Airmass"            
        header["OBS_HANG"] = "hh:mm:ss.ss"                          , "Hour angle"
        header["TRG_EPOC"] = "2000"                                 , "Epoch of object coordinates"
        header["OBS_TSYS"] = "UTC"                                  , "Default time system"
        header["OBS_TIME"] = self.exp_start_time                    , "Observation start time" 
        header["OBS_PPL "] = observers                              , "Observers"
        header["OBS_FILE"] = ""         # => needs to be updated by pipeline
        header["OBS_MJD "] = ""                                     , "Mid-Observation MJD"
        header["OBS_TYPE"] = self.exp_type_name.currentText().strip().lower() , "Observation type"                                
        header["INS_LAMP"] = "UAr"                                  , "Calibration lamp"
        header["OBSERVAT"] = "Gurushikhar Mt.Abu"                   , "Observatory Location"                                                                                           
        header["TELESCOP"] = "2.5M"                                 , "Telescope"
        header["INSTRUME"] = "PARAS2"                               , "Instrument"
        header["FILTER1"]  = "None"                                 , "Filter 1"
        header["FILTER2"]  = "None"                                 , "Filter 2"
        header["OBS_ELEV"] = 1765                                   , "Observatory Altitude (meters)"
        header["OBS_LAT "] = 24.6531                                , "Observatory Latitude (degrees)"
        header["OBS_LONG"] = 72.7794                                , "Observatory Longitude (hours)"
        header["TRG_NAME"] = self.target_name.text().strip()        ,  "Target name"
        # header["TRG ALPH"] = source_details["ra"]                   , "Target RA (hours)"
        # header["TRG DELT"] = source_details["dec"]                  , "Target DEC (degrees)"
        header["TRG_PMRA"] = ""                                     , "Target Proper Motion in RA (mas/yr)"
        header["TRG_PMDE"] = ""                                     , "Target Proper Motion in DEC (mas/yr)"
        header["TRG_TYPE"] = ""                                     , "Target Stellar Type"
        header["CCD_EXPT"] = self.input_exp_time.text().strip()     , "Exposure time in seconds"
        header["CCD_GAIN"] = 2                                      , "Gain in electrons/adu"
        header["CCD_RDNS"] = 4.50000                                , "Read-out Noise"
        
        hdu.writeto( image_path, overwrite=1 )

        self.open_image(image_path)
        self.readout_time_flag = False
        print("owl thread completed!")
        self.progressbar_exp.setValue(100)
        self.btn_expose.setEnabled(True)
        self.btn_abort.setDisabled(True)
        self.exp_start_time = None

    # -----------------------------------------------------------

    def power_off_controller(self):
        self.log("Power Off Controller: ",end=" ")
        if self.arc.poweroff():
            self.log("Error!","red")
        else:
            self.log("Done!","green")

    def power_on_controller(self):
        self.log("Power On Controller: ",end=" ")
        if self.arc.poweron():
            self.log("Error!","red")
        else:
            self.log("Done!","green")

    def open_shutter(self):
        self.log("Opening Shutter: ",end=" ")
        if self.arc.open_shutter():
            self.log("Error!","red")
        else:
            self.log("Done!","green")

    def close_shutter(self):
        self.log("Closing Shutter: ",end=" ")
        if self.arc.close_shutter():
            self.log("Error!","red")
        else:
            self.log("Done!","green")
        
    def setup_dialog(self):

        def get_tim_location():
            dialog = QFileDialog()
            path = dialog.getOpenFileName(self, "Select File", "./api")[0]
            # print("\npath: ",path)
            return path

        passwd, ok    = QInputDialog.getText(self,"Authorized","Enter Password")
        passwd        = passwd.strip()
        passwd_digest = sha256(passwd.encode()).digest()
 
        if not ok:
            return

        if passwd_digest == sha256("".encode()).digest():

            window = QWidget()
            window.setWindowTitle("Setup Controller")
            layout = QGridLayout() 


            chk_btn_rst = QCheckBox("Reset Controller")
            chk_btn_pwr = QCheckBox("Power On")
            layout.addWidget(chk_btn_rst,0,0)
            layout.addWidget(chk_btn_pwr,0,1)
            

            chk_btn_tim        = QCheckBox("Tim Download")
            input_tim_location = QLineEdit()
            btn_tim_location   = QPushButton()
            btn_tim_location.setIcon(QIcon("resources/icons/folder.gif"))
            layout.addWidget(chk_btn_tim,1,0)
            layout.addWidget(input_tim_location,1,1,1,3)
            layout.addWidget(btn_tim_location,1,4)
            btn_tim_location.clicked.connect(lambda: input_tim_location.setText(get_tim_location()))
            chk_btn_tim.clicked.connect(lambda: input_tim_location.setEnabled(chk_btn_tim.isChecked()))


            chk_btn_img = QCheckBox("Image Size")
            lbl_rows    = QLabel(text="rows")
            input_rows  = QLineEdit("6200")
            lbl_cols    = QLabel(text="cols")
            input_cols  = QLineEdit("7000")
            layout.addWidget(chk_btn_img,2,0)
            layout.addWidget(lbl_rows,2,1, Qt.AlignRight)
            layout.addWidget(input_rows,2,2)
            layout.addWidget(lbl_cols,2,3,Qt.AlignRight)
            layout.addWidget(input_cols,2,4)
            chk_btn_img.clicked.connect(lambda : 
                                            input_rows.setEnabled(chk_btn_img.isChecked()) or
                                            input_cols.setEnabled(chk_btn_img.isChecked())
                                        )


            lbl_readout_spd = QLabel(text="Readout Speed")
            rd_btn_slw      = QRadioButton("SLOW")
            rd_btn_med      = QRadioButton("MED")
            rd_btn_fst      = QRadioButton("FAST")
            layout.addWidget(lbl_readout_spd,3,0)
            layout.addWidget(rd_btn_slw,3,1)
            layout.addWidget(rd_btn_med,3,2)
            layout.addWidget(rd_btn_fst,3,3)
            btn_grp_readout_spd = QButtonGroup()
            btn_grp_readout_spd.addButton(rd_btn_slw,0)
            btn_grp_readout_spd.addButton(rd_btn_med,1)
            btn_grp_readout_spd.addButton(rd_btn_fst,2)


            lbl_sos = QLabel(text="Quad Readout")
            rd_btn_amp0 = QRadioButton()
            rd_btn_amp1 = QRadioButton()
            rd_btn_amp2 = QRadioButton()
            rd_btn_amp3 = QRadioButton()
            rd_btn_amp0.setIcon(QIcon("resources/icons/AMP_0.gif"))
            rd_btn_amp1.setIcon(QIcon("resources/icons/AMP_1.gif"))
            rd_btn_amp2.setIcon(QIcon("resources/icons/AMP_2.gif"))
            rd_btn_amp3.setIcon(QIcon("resources/icons/AMP_3.gif"))
            rd_btn_amp0.setIconSize(QSize(64,64))
            rd_btn_amp1.setIconSize(QSize(64,64))
            rd_btn_amp2.setIconSize(QSize(64,64))
            rd_btn_amp3.setIconSize(QSize(64,64))
            btn_grp_sos = QButtonGroup()
            btn_grp_sos.addButton(rd_btn_amp0,0)
            btn_grp_sos.addButton(rd_btn_amp1,1)
            btn_grp_sos.addButton(rd_btn_amp2,2)
            btn_grp_sos.addButton(rd_btn_amp3,3)
            layout.addWidget(lbl_sos,4,0)
            layout.addWidget(rd_btn_amp0,4,1)
            layout.addWidget(rd_btn_amp1,4,2)
            layout.addWidget(rd_btn_amp2,4,3)
            layout.addWidget(rd_btn_amp3,4,4)
            lbl_amp0 = QLabel("0")
            lbl_amp1 = QLabel("1")
            lbl_amp2 = QLabel("2")
            lbl_amp3 = QLabel("3")
            layout.addWidget(lbl_amp0,5,1, Qt.AlignCenter)
            layout.addWidget(lbl_amp1,5,2, Qt.AlignCenter)
            layout.addWidget(lbl_amp2,5,3, Qt.AlignCenter)
            layout.addWidget(lbl_amp3,5,4, Qt.AlignCenter)

            btn_apply = QPushButton("Apply")
            btn_apply.setStyleSheet("color: red; font: bold")
            layout.addWidget(btn_apply,6,1,1,2)
            btn_apply.clicked.connect(lambda: self.setup({
                                "CTRL_RST" : True if chk_btn_rst.isChecked() else False,
                                "PWR_ON"   : True if chk_btn_pwr.isChecked() else False,
                                "TIM"      : ( True if chk_btn_tim.isChecked() else False , input_tim_location.text() ),
                                "IMG_SIZE" : ( True if chk_btn_img.isChecked() else False , int(input_rows.text()),int(input_cols.text())),
                                "READ_SPD" : btn_grp_readout_spd.checkedId(),
                                "QUAD"     : btn_grp_sos.checkedId()
                            }))

            try:
                with open("setup.ini","r") as f:
                    settings_dict = json.loads(f.read())

                    # pprint(settings_dict)

                    chk_btn_rst.setChecked(True) if settings_dict["CTRL_RST"] else None
                    chk_btn_pwr.setChecked(True) if settings_dict["PWR_ON"] else None
                    
                    
                    chk_btn_tim.setChecked(True) if settings_dict["TIM"][0] else None
                    input_tim_location.setText(settings_dict["TIM"][1])
                    input_tim_location.setEnabled(False) if not settings_dict["TIM"][0] else None

                    chk_btn_img.setChecked(True) if settings_dict["IMG_SIZE"][0] else None
                    input_rows.setText(str(settings_dict["IMG_SIZE"][1]))
                    input_cols.setText(str(settings_dict["IMG_SIZE"][2]))
                    input_rows.setEnabled(False) if not settings_dict["IMG_SIZE"][0] else None
                    input_cols.setEnabled(False) if not settings_dict["IMG_SIZE"][0] else None

                    # { 0:"SLOW", 1:"MED", 2:"FAST"}
                    if settings_dict["READ_SPD"] == 0:
                        rd_btn_slw.setChecked(True)
                    elif settings_dict["READ_SPD"] == 1:
                        rd_btn_med.setChecked(True)
                    elif settings_dict["READ_SPD"] == 2:
                        rd_btn_fst.setChecked(True)

                    if settings_dict["QUAD"] == 0:
                        rd_btn_amp0.setChecked(True)
                    elif settings_dict["QUAD"] == 1:
                        rd_btn_amp1.setChecked(True)
                    elif settings_dict["QUAD"] == 2:
                        rd_btn_amp2.setChecked(True)
                    elif settings_dict["QUAD"] == 3:
                        rd_btn_amp3.setChecked(True)
                    
            except Exception as e:
                print(e)
                self.log("Setup Controller: ",end="")
                self.log("no previous settings found!","red")
                self.log("Setup Controller: Using Default Settings!",)
                # chk_btn_rst.setChecked(True)
                # chk_btn_pwr.setChecked(True)
                # chk_btn_tim.setChecked(True)
                # chk_btn_img.setChecked(True)
                # rd_btn_med.setChecked(True)
                # rd_btn_amp3.setChecked(True)
                # input_tim_location.setText(os.getcwd().replace("\\","/")+"/api/tim.lod")

            window.setLayout(layout)
            window.show()

            window.exec_()
        
        else:
            self.log("Setup Controller:",end=" ")
            self.log("Incorrect Password!","red")


    def setup(self, settings_dict):
        
        with open("setup.ini","w") as f:          # saving setup contoller settings
            f.write(json.dumps(settings_dict))

        msgBox = QMessageBox()
        msgBox.setWindowTitle(" ")
        msgBox.setText("Setup Controller ?")
        # msgBox.setInformativeText("Proceed?")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        # msgBox.setDefaultButton(QMessageBox.Cancel)
        ret = msgBox.exec_()    
        
        if ret == QMessageBox.Ok:
            self.log("Controller Setup: ",end=" ")
            if self.arc.apply_setup(settings_dict):
                self.log("Error!","red")
            else:
                self.log("Done!","green")

    def clear_array(self):
        self.log("Clear Camera Array: ",end=" ")
        if self.arc.clear_camera_array():
            self.log("Error!","red")
        else:
            self.log("Done!","green")

    def reset_controller(self):
        self.log("Resetting Controller: ",end=" ")
        if self.arc.reset_controller():
            self.log("Error!","red")
        else:
            self.log("Done!","green")
            
    def abort_exposure(self):
        self.btn_abort.setDisabled(True)
        self.btn_expose.setEnabled(True)

        with open("exposure.dat","w") as f:
            f.write("1")
            f.flush()

        # self.arc.abort_exposure()
    # ==============================================================

    # ==============================================================
    #           DS9 Functions
    # ==============================================================
    def open_image(self, path):
        path = path.replace("\\","/")
        Popen(["./DS9/xpaset.exe", "-p", "ds9", "file", path], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        Popen(["./DS9/xpaset.exe", "-p", "ds9", "zoom","to fit"], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        Popen(["./DS9/xpaset.exe", "-p", "ds9", "zscale"], stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    def ds9_process(self):
        self.xpans = Popen("./DS9/xpans.exe", stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        self.ds9 = Popen("./DS9/ds9.exe", stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    def ds9_kill(self):
        try:
            self.xpans.kill()
            self.ds9.kill()
        except:
            print("DS9 not open.")
    # ==============================================================

    # ==============================================================
    #                   FITS Header Updation
    # ==============================================================
    def update_fits_header(self, filename):
        data, header = fits.getdata(filename, header=True)
        # header[""] = ""
        fits.append(filename, data, header, overwrite=True, verify=False)

    # ==============================================================
    #   Source API functions
    # ==============================================================

    def get_src_info(self, progress_callback):
        name = self.source_name.text()
        name = name.replace(" ", "")
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
        self.target_name.setText(self.source_name.text())
        self.radec_name.setText(info[0][1]+"\n"+info[0][2])
    # ==============================================================

    def shutter_status_thread(self, progress_callback):

        ports = serial.tools.list_ports.comports()

        target_port = None

        for port, desc, hwid in sorted(ports):
            # print("{}: {} [{}]".format(port, desc, hwid))
            if "CH340" in desc:
                target_port = port

        while True and self.shutter_thread_flag:
            try:
                if target_port:
                    ser = serial.Serial(target_port, 115200)
                    status = ser.readline().decode()
                    # print(status)
                    status = status.strip()

                    if status == "open":
                        self.lbl_shutter_status.setText("Open")
                        self.lbl_shutter_status.setStyleSheet(
                            "color: green; font: bold")
                    else:
                        self.lbl_shutter_status.setText("Closed")
                        self.lbl_shutter_status.setStyleSheet(
                            "color: red; font: bold")
                    ser.close()
            except:
                ports = serial.tools.list_ports.comports()
                for port, desc, hwid in sorted(ports):
                    # print("{}: {} [{}]".format(port, desc, hwid))
                    if "CH340" in desc:
                        target_port = port
                self.lbl_shutter_status.setText("Unkown")
                self.lbl_shutter_status.setStyleSheet(
                    "color: blue; font: bold")

    def gps_thread(self, progress_callback):
        ports = serial.tools.list_ports.comports()
        target_port = None

        for port, desc, hwid in sorted(ports):
            # print("{}: {} [{}]".format(port, desc, hwid))
            if "PID=067B:2303" in hwid:
                print(port)
                target_port = port

        gps_details = None

        if target_port:
            ser = serial.Serial(target_port, 9600)
            while True and self.gps_flag:
                try:
                    line = ser.readline().decode()
                    # print(line,end="")
                    if line.startswith("$GNRMC"):
                        gps_details = pynmea2.parse(line)
                        # print(line,end="")

                        self.lbl_gps_status.setText(("UTC Time : "+gps_details.datetime.strftime("%d-%m-%Y %H:%M")+"\n"+\
                                                    "Longitude: {}\nLatitude  : {}".format(gps_details.longitude, gps_details.latitude)))
                except Exception as e:
                    print(str(e))
                    continue

    def img_file_options(self):
        # fname = QFileDialog.getExistingDirectory(self, "Select Direcotry", str(Path.home())+"\\Pictures")
        path = self.input_img_dir.text().strip()

        file_dialog = QFileDialog()

        if path:
            fname = file_dialog.getExistingDirectory(self, "Select Direcotry", path)
        else:
            fname = file_dialog.getExistingDirectory(self, "Select Direcotry")

        self.input_img_dir.setText(fname)

    def creategui(self):

        # ===========================================================
        #                       Quick Actions
        # ===========================================================
        self.grp_box_actns = QGroupBox("Quick Actions")
        # self.actns_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.actns_layout = QGridLayout()

        # self.actns_layout.setAlignment(AlignTop)

        # self.btn_ctrl_setup = QPushButton(self)
        # self.btn_ctrl_setup.setIcon(QIcon("resources/icons/setup.png"))
        # self.btn_ctrl_setup.setIconSize(QSize(40, 40))
        # self.actns_layout.addWidget(self.btn_ctrl_setup,0,0)
        # self.btn_ctrl_setup.clicked.connect(self.setup_dialog)
        # self.btn_ctrl_setup.setToolTip("Loads tim.lod file")

        self.btn_ctrl_setup = QPushButton(self)
        self.btn_ctrl_setup.setIcon(QIcon("resources/icons/setup.png"))
        self.btn_ctrl_setup.setIconSize(QSize(40, 40))
        self.actns_layout.addWidget(self.btn_ctrl_setup,0,0)
        self.btn_ctrl_setup.clicked.connect(self.setup_dialog)
        self.btn_ctrl_setup.setToolTip("Loads tim.lod file")

        self.btn_ctrl_rst = QPushButton(self)
        self.btn_ctrl_rst.setIcon(QIcon("resources/icons/ResetCtlr.gif"))
        self.btn_ctrl_rst.setIconSize(QSize(40, 40))
        self.actns_layout.addWidget(self.btn_ctrl_rst,0,1)
        self.btn_ctrl_rst.clicked.connect(self.reset_controller)
        self.btn_ctrl_rst.setToolTip("Resets Controller")

        self.btn_poweron = QPushButton(self)
        self.btn_poweron.setIcon(QIcon("resources/icons/PowerOn.gif"))
        self.btn_poweron.setIconSize(QSize(40, 40))
        self.actns_layout.addWidget(self.btn_poweron,0,2)
        self.btn_poweron.clicked.connect(self.power_on_controller)
        self.btn_poweron.setToolTip("Power On")

        self.btn_poweroff = QPushButton(self)
        self.btn_poweroff.setIcon(QIcon("resources/icons/PowerOff.gif"))
        self.btn_poweroff.setIconSize(QSize(40, 40))
        self.actns_layout.addWidget(self.btn_poweroff,0,3)
        self.btn_poweroff.clicked.connect(self.power_off_controller)
        self.btn_poweroff.setToolTip("Power Off")

        self.btn_ds9 = QPushButton(self)
        self.btn_ds9.setIcon(QIcon("resources/icons/ds9.png"))
        self.btn_ds9.setIconSize(QSize(40, 40))
        # self.btn_ds9.clicked.connect(lambda: self.spawn_thread(
        #     self.ds9_process, None, None))
        self.btn_ds9.clicked.connect(self.ds9_process)
        self.actns_layout.addWidget(self.btn_ds9,1,0)
        self.btn_ds9.setToolTip("Opens DS9")

        self.btn_clr_array = QPushButton(self)
        self.btn_clr_array.setIcon(QIcon("resources/icons/ClearArray.gif"))
        self.btn_clr_array.setIconSize(QSize(40, 40))
        self.actns_layout.addWidget(self.btn_clr_array,1,1)
        self.btn_clr_array.clicked.connect(self.clear_array)
        self.btn_clr_array.setToolTip("Clear Camera Array")

        self.btn_openshutter = QPushButton(self)
        self.btn_openshutter.setIcon(QIcon("resources/icons/OpenShutter.gif"))
        self.btn_openshutter.setIconSize(QSize(40, 40))
        self.actns_layout.addWidget(self.btn_openshutter,1,2)
        self.btn_openshutter.clicked.connect(self.open_shutter)
        self.btn_openshutter.setToolTip("Open Camera Shutter")

        self.btn_closeshutter = QPushButton(self)
        self.btn_closeshutter.setIcon(QIcon("resources/icons/CloseShutter.gif"))
        self.btn_closeshutter.setIconSize(QSize(40, 40))
        self.actns_layout.addWidget(self.btn_closeshutter,1,3)
        self.btn_closeshutter.clicked.connect(self.close_shutter)
        self.btn_closeshutter.setToolTip("Open Camera Shutter")

        # self.actns_layout.set

        # self.actns_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.grp_box_actns.setLayout(self.actns_layout)

        # ===========================================================
        #                     Exposure Options
        # ===========================================================
        self.grp_box_exp = QGroupBox("Exposure Options")
        self.gridLayout_exp = QGridLayout()

        self.chk_btn_exp_time = QCheckBox("Exp. Time", self)
        self.input_exp_time = QLineEdit(self)
        self.input_exp_time.setDisabled(True)
        self.chk_btn_exp_time.clicked.connect(
            lambda: self.input_exp_time.setDisabled(not self.chk_btn_exp_time.isChecked()))
        self.gridLayout_exp.addWidget(self.chk_btn_exp_time, 0, 0)
        self.gridLayout_exp.addWidget(self.input_exp_time, 0, 1)
        self.input_exp_time.setValidator(QDoubleValidator())

        self.chk_btn_exp_delay = QCheckBox("Delay Exposure(sec)", self)
        self.input_exp_delay = QLineEdit(self)
        self.input_exp_delay.setDisabled(True)
        self.chk_btn_exp_delay.clicked.connect(
            lambda: self.input_exp_delay.setDisabled(not self.chk_btn_exp_delay.isChecked()))
        self.gridLayout_exp.addWidget(self.chk_btn_exp_delay, 1, 0)
        self.gridLayout_exp.addWidget(self.input_exp_delay, 1, 1)
        self.input_exp_delay.setValidator(QIntValidator())

        self.chk_btn_exp_multi = QCheckBox("Multiple Exposure", self)
        self.input_exp_multi = QLineEdit(self,text="1")
        self.input_exp_multi.setDisabled(True)
        self.chk_btn_exp_multi.clicked.connect(
            lambda: self.input_exp_multi.setDisabled(not self.chk_btn_exp_multi.isChecked()))
        self.gridLayout_exp.addWidget(self.chk_btn_exp_multi, 2, 0)
        self.gridLayout_exp.addWidget(self.input_exp_multi, 2, 1)
        self.input_exp_multi.setValidator(QIntValidator())

        self.chk_btn_open_shutter = QCheckBox("Open Shutter", self)
        self.gridLayout_exp.addWidget(self.chk_btn_open_shutter, 3, 0)

        self.lbl_readout_time = QLabel("Readout Time: ",self)
        self.lbl_readout_time.setStyleSheet("color: #F92672; font: bold; font-size: 10pt")
        self.gridLayout_exp.addWidget(self.lbl_readout_time,4,0,1,2)

        self.btn_abort = QPushButton(self, text="ABORT")
        self.btn_abort.setStyleSheet("color: red; font: bold")
        self.gridLayout_exp.addWidget(self.btn_abort, 5, 0)
        self.btn_abort.clicked.connect(self.abort_exposure)
        self.btn_abort.setEnabled(False)

        self.btn_expose = QPushButton(self, text="EXPOSE")
        self.btn_expose.setStyleSheet("color: blue; font: bold")
        self.gridLayout_exp.addWidget(self.btn_expose, 5, 1)
        self.btn_expose.clicked.connect(self.expose_handler)

        self.progressbar_exp = QProgressBar()
        self.progressbar_exp.setMinimum(0)
        self.progressbar_exp.setMaximum(100)
        self.progressbar_exp.setValue(0)
        self.gridLayout_exp.addWidget(self.progressbar_exp, 6, 0, 1, 2)

        self.progressbar_exp_label = QLabel("", self)
        self.gridLayout_exp.addWidget(self.progressbar_exp_label, 6, 0, 1, 2, Qt.AlignCenter)

        # self.gridLayout_exp.setSizeConstraint(QLayout.SetFixedSize)
        self.grp_box_exp.setLayout(self.gridLayout_exp)

        # ===========================================================
        #                     Image File otions
        # ===========================================================
        self.grp_box_img_file_ops = QGroupBox("Image File Options")
        self.gridLayout_img_file_ops = QGridLayout()

        self.lbl_img_dir = QLabel(self, text="Dir:")
        self.gridLayout_img_file_ops.addWidget(self.lbl_img_dir, 0, 0)

        self.input_img_dir = QLineEdit(
            self, text=str(Path.home())+"\\Pictures")
        self.input_img_dir.setReadOnly(True)
        self.gridLayout_img_file_ops.addWidget(self.input_img_dir, 0, 1,1,2)

        self.btn_img_dir = QPushButton(self)
        self.btn_img_dir.setIcon(QIcon("resources/icons/folder.gif"))
        self.btn_img_dir.clicked.connect(self.img_file_options)
        self.gridLayout_img_file_ops.addWidget(self.btn_img_dir, 0, 3)

        self.lbl_img_file_name = QLabel(self, text="Filename:")
        self.gridLayout_img_file_ops.addWidget(self.lbl_img_file_name, 1, 0)

        self.lbl_img_fn_val = QLabel(self)
        self.gridLayout_img_file_ops.addWidget(self.lbl_img_fn_val, 1, 1, 1, 3)
        self.lbl_img_fn_val.setStyleSheet("color: blue;")

        self.lbl_img_prefix = QLabel(self, text="Prefix")
        self.gridLayout_img_file_ops.addWidget(self.lbl_img_prefix, 2, 0, Qt.AlignRight)
        self.input_img_prefix = QLineEdit(self, text="a")
        self.gridLayout_img_file_ops.addWidget(self.input_img_prefix, 2, 1)
        self.input_img_prefix.setValidator(QRegExpValidator(QRegExp("\w*")))
        self.input_img_prefix.setFixedWidth(60)

        self.lbl_img_suffix = QLabel(self, text="Sufix")
        self.gridLayout_img_file_ops.addWidget(self.lbl_img_suffix, 2, 2,Qt.AlignRight)
        self.input_img_suffix = QLineEdit(self,text="0000")
        self.gridLayout_img_file_ops.addWidget(self.input_img_suffix, 2, 3)
        self.input_img_suffix.setValidator(QIntValidator())
        self.input_img_suffix.setFixedWidth(60)

        self.lbl_img_fn_val.setText(self.input_img_prefix.text().strip()+\
                                    self.input_img_suffix.text().strip()+".fits")

        self.input_img_prefix.textEdited.connect(self.update_img_filename)
        self.input_img_suffix.textEdited.connect(self.update_img_filename)

        # self.gridLayout_img_file_ops.setSizeConstraint(QLayout.SetFixedSize)
        self.grp_box_img_file_ops.setLayout(self.gridLayout_img_file_ops)
        # ===========================================================

        # ===========================================================
        #                     Source Details
        # ===========================================================
        self.grp_box_source = QGroupBox("Source Details")
        self.gridLayout_source = QGridLayout()

        self.source_lbl = QLabel(self, text="Source Name:")
        self.gridLayout_source.addWidget(self.source_lbl, 0, 0)

        self.source_name = QLineEdit(self)
        self.gridLayout_source.addWidget(self.source_name, 0, 1)

        self.source_btn = QPushButton(self, text="submit")
        self.source_btn.setFixedWidth(120)
        self.gridLayout_source.addWidget(self.source_btn, 1, 0, 1, 2,Qt.AlignRight)
        self.source_btn.clicked.connect(lambda: self.spawn_thread(
            self.get_src_info, None, self.set_src_info))

        self.source_info = QTextEdit(self)
        self.source_info.setReadOnly(True)
        self.gridLayout_source.addWidget(self.source_info, 2, 0, 1, 2)

        # self.gridLayout_source.addWidget(self.dummy,3,0,1,2)

        # self.gridLayout_source.setSizeConstraint(QLayout.SetFixedSize)
        self.grp_box_source.setLayout(self.gridLayout_source)
        # ===========================================================

        # ===========================================================
        #                 Observation Details
        # ===========================================================
        self.grp_box_observation = QGroupBox("Observation Details")
        self.gridLayout_observation = QGridLayout()
        self.grp_box_observation.setMaximumWidth(240)

        self.target_lbl = QLabel(self, text="Source Name:")
        self.target_name = QLineEdit(self)
        self.gridLayout_observation.addWidget(self.target_lbl, 0, 0)
        self.gridLayout_observation.addWidget(self.target_name, 0, 1)

        self.exp_type_lbl = QLabel(self, text="Exposure Type:")
        self.exp_type_name = QComboBox(self)
        self.exp_type_name.addItems(["Dark","Dark+Tung","Tung+Dark","UAr+UAr","Dark+UAr","ThAr+ThAr","Dark+ThAr","Star+UAr","Star+ThAr","Star+Dark"])
        # self.exp_type_name.currentTextChanged.connect(lambda: self.input_exp_time.setText(self.EXP_TIMES[self.exp_type_name.currentText()]))
        self.input_exp_time.setText(self.EXP_TIMES[self.exp_type_name.currentText()])
        self.gridLayout_observation.addWidget(self.exp_type_lbl, 1, 0)
        self.gridLayout_observation.addWidget(self.exp_type_name, 1, 1)

        self.radec_lbl = QLabel(self, text="RA/DEC:")
        self.radec_name = QTextEdit(self)
        self.radec_name.setFixedHeight(40)
        self.gridLayout_observation.addWidget(self.radec_lbl, 2, 0)
        self.gridLayout_observation.addWidget(self.radec_name, 2, 1)

        self.lbl_observers_name = QLabel(self, text="Observers:")
        self.lbl_observers_name.setAlignment(Qt.AlignTop)
        self.input_observers_name = QTextEdit(self)
        self.input_observers_name.setFixedHeight(50)
        self.gridLayout_observation.addWidget(self.lbl_observers_name, 3, 0)
        self.gridLayout_observation.addWidget(self.input_observers_name, 3, 1)

        self.comment_lbl = QLabel(self, text="Comments")
        self.comment_lbl.setAlignment(Qt.AlignTop)
        self.comment_name = QTextEdit(self)
        self.comment_name.setFixedHeight(40)
        self.gridLayout_observation.addWidget(self.comment_lbl, 4, 0)
        self.gridLayout_observation.addWidget(self.comment_name, 4, 1)

        self.lbl_prl_logo = QLabel(self)
        self.prl_logo = QPixmap("resources/icons/prl_back.png")
        self.lbl_prl_logo.setPixmap(self.prl_logo)
        self.gridLayout_observation.addWidget(self.lbl_prl_logo, 5,0,1,2)

        self.btn_about = QPushButton("About")
        self.btn_about.setIcon(QIcon("resources/icons/about.png"))
        self.gridLayout_observation.addWidget(self.btn_about, 6,1, Qt.AlignRight)
        self.btn_about.clicked.connect(self.about_dialog)

        # self.gridLayout_observation.addWidget(self.dummy_txt,6,0,1,2)

        self.grp_box_observation.setLayout(self.gridLayout_observation)
        # ===========================================================


        # ===========================================================
        #                     Logger
        # ===========================================================
        self.grp_box_logger = QGroupBox("Logger")
        self.gridLayout_logger = QGridLayout()

        self.txt_logger = QTextEdit(self)
        self.txt_logger.setReadOnly(True)
        self.gridLayout_logger.addWidget(self.txt_logger)

        self.grp_box_logger.setLayout(self.gridLayout_logger)
        # ===========================================================

        # ===========================================================
        #                    Status
        # ===========================================================
        self.grp_box_status = QGroupBox("Status")
        self.gridLayout_status = QGridLayout()

        self.lbl_shutter = QLabel(self, text="Shutter:")
        self.lbl_shutter.setStyleSheet("font: bold")
        self.gridLayout_status.addWidget(self.lbl_shutter, 0, 0)

        self.lbl_shutter_status = QLabel(self, text="Unkown")
        self.lbl_shutter_status.setStyleSheet("color: blue; font: bold")
        self.gridLayout_status.addWidget(self.lbl_shutter_status, 0, 1)

        self.gridLayout_status.addWidget(self.dummy_line, 0, 2, 1, 1)

        self.lbl_gps = QLabel(self,text="GPS Details")
        self.lbl_gps.setStyleSheet("color: black; font: bold")
        self.gridLayout_status.addWidget(self.lbl_gps,1,0)
        self.lbl_gps_status = QLabel(self)
        self.gridLayout_status.addWidget(self.lbl_gps_status,2,0,1,3)
        self.grp_box_status.setLayout(self.gridLayout_status)
        # ===========================================================
        self.load_settings()

    def logger_window(self):
        self.logger = QMainWindow()
        self.logger.show()

    def save_settings(self):
        try:
            with open("settings.ini","w") as settings_file:
                settings_file.writelines([self.input_img_dir.text(),    "\n", 
                                          self.input_img_prefix.text(), "\n",
                                          self.input_img_suffix.text(), "\n",
                                          ])
        except Exception as e :
            print("save_settings(): ", e)

    def load_settings(self):
        try:
            with open("settings.ini","r")  as settings_file:
                dir, prefix, suffix = [ x.strip() for x in  settings_file.readlines()]

                self.input_img_prefix.setText(prefix)
                self.input_img_suffix.setText(suffix)
                self.lbl_img_fn_val.setText(prefix+suffix+".fits")
                self.input_img_dir.setText(dir.strip())
        except Exception as e:
            print("load_settings(): ",e)

    # def get_max_filename(self, fn_pattern):
    #     print("get_max_filename(): ",fn_pattern)
    #     try:
    #         files = [ os.path.basename(full_fn) for full_fn in glob.glob(fn_pattern)]
    #         files = sorted(files)
    #         print("get_max_filename(): ",files)
    #         # max_num = re.findall("\d+",files[-1])[-1]

    #         max_num = list(re.finditer("\d+",files[-1]))
    #         if max_num:
    #             max_num = max_num[0]
    #         else:
    #             return "single file"

    #     except Exception as e:
    #         print("get_max_filename(): ",e)
    #         return "not found"
        
    #     # return max_num
    #     return (max_num.span(), max_num[0])   # index tuple, match

    def about_dialog(self):
        msg = """PARI (Paras Aquisition and Readout Initiation)
is developed by Mr. Dishendra under the supervision
of Prof. Abhijit and Mr. Neelam JSSV Prasad using the
API provided by Astronomical Research Cameras, Inc."""

        msg_box = QMessageBox()
        msg_box.setText(msg)
        msg_box.setWindowTitle("About")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def update_img_filename(self):
        self.lbl_img_fn_val.setText( self.input_img_prefix.text().strip()+\
                                     self.input_img_suffix.text().strip()+".fits")

    def handle_fits_filename(self):
        # ================================================================================
        #                       Handling existing fits filenames
        # ================================================================================
        prefix = self.input_img_prefix.text().strip()
        suffix = self.input_img_suffix.text().strip()
        directory = self.input_img_dir.text().strip().replace("\\","/")+"/"
        
        old_filename = prefix+str(suffix).zfill(len(suffix))+".fits"
        filename = old_filename

        suffix = suffix if suffix else ""

        i = int(suffix)
        flag = False

        while os.path.exists(directory+filename):
            i += 1
            filename = prefix+str(i).zfill(len(suffix))+".fits"
            flag = True

        if flag:
            self.input_img_suffix.setText(str(i).zfill(len(suffix)))
            self.log("Exposure: ",end="")
            self.log(f'Using filename <span style="color:green">{filename}</span> \
                    since <span style="color:red">{old_filename}</span> already exits!')
            self.lbl_img_fn_val.setText(filename)
        # ================================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # style realted settings
    app.setStyle('Fusion')
    app.setStyleSheet(open("resources/styles/style.qss").read())
    app.setWindowIcon(QIcon("resources/icons/prl.png"))
    
    window = PARI()
    window.show()
    app.exec_()
    sys.exit()
