from subprocess import Popen, PIPE, STDOUT
import os
from time import sleep


class ArcWrapper():

    def __init__(self):
        self.process = Popen("./api/ArcAPI35Ex_1.exe", stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    def write_stdin(self, cmd, delimiter="\n"):
        cmd = str(cmd)+delimiter
        self.process.stdin.write(cmd.encode())
        self.process.stdin.flush()

    def read_stdout(self, end_string="Enter any key"):
      error = False
      
      for line in self.process.stdout:
        line = line.decode("utf-8").strip()
        print(line)
        
        if line.startswith("Error") or line.startswith("( CArcPCIe"):
          error = True
        elif line.startswith(end_string):
          break
      
      return error

    def kill(self):
      self.write_stdin("0")
      self.read_stdout()
      self.process.kill()

    def apply_setup(self):
        self.write_stdin("1")
        error = self.read_stdout()
        self.write_stdin("")
        return error

    def take_exposure(self, exp_time, shutter_cfg, fits_filename):
        self.write_stdin("2", " ")
        self.write_stdin(exp_time," ")
        self.write_stdin(shutter_cfg," ")
        self.write_stdin(fits_filename)
        # self.read_stdout()
        # self.write_stdin("")

    def open_shutter(self):
        self.write_stdin("3")
        error = self.read_stdout()
        self.write_stdin("")
        return error

    def close_shutter(self):
        self.write_stdin("4")
        error = self.read_stdout()
        self.write_stdin("")
        return error
    
    def poweron(self):
        self.write_stdin("5")
        error = self.read_stdout()
        self.write_stdin("")
        return error
    
    def poweroff(self):
        self.write_stdin("6")
        error = self.read_stdout()
        self.write_stdin("")
        return error

    def reset_controller(self):
        self.write_stdin("9")
        error = self.read_stdout()
        self.write_stdin("")
        return error


    def clear_camera_array(self):
        self.write_stdin("7")
        error = self.read_stdout()
        self.write_stdin("")
        return error

    def is_open(self):
        self.write_stdin("8")
        error = self.read_stdout()
        self.write_stdin("")
        return error

# if __name__ == "__main__":
#   arc = ArcWrapper()
#   arc.apply_setup()
#   arc.poweron()
#   arc.poweroff()
#   arc.open_shutter()
#   arc.close_shutter()
#   arc.clear_camera_array()
#   arc.take_exposure(0.01,0,"test.fits")
#   arc.poweroff()
#   arc.kill()
#   input("DONE")