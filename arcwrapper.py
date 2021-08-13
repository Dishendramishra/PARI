from subprocess import Popen, PIPE, STDOUT
import os
from time import sleep


class ArcWrapper():

    def __init__(self):
        os.chdir("api")
        self.process = Popen("ArcAPI35Ex_1.exe", stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    def write_stdin(self, cmd):
        cmd = str(cmd)+"\n"
        self.process.stdin.write(cmd.encode())
        self.process.stdin.flush()

    def read_stdout(self):
      for line in self.process.stdout:
        line = line.decode("utf-8")
        print(line)

        if line.startswith("   Enter any key to"):
          break

    def kill(self):
      self.write_stdin("0")
      self.process.kill()

    def apply_setup(self):
        self.write_stdin("1")
        self.read_stdout()
        self.write_stdin("")

    def take_exposure(self, exp_time, fits_filename, shutter_cfg):
        self.write_stdin("2")
        self.write_stdin(exp_time)
        self.write_stdin(fits_filename)
        self.write_stdin(shutter_cfg)

        # self.read_stdout()
        # self.write_stdin("")

    def open_shutter(self):
        self.write_stdin("3")
        self.write_stdin("")

    def close_shutter(self):
        self.write_stdin("4")
        self.write_stdin("")
    
    def poweroff(self):
        self.write_stdin("5")
        self.write_stdin("")
    
    def poweron(self):
        self.write_stdin("6")
        self.write_stdin("")

    def clear_camera_array(self):
        self.write_stdin("7")
        self.write_stdin("")

    def is_open(self):
        self.write_stdin("8")
        self.write_stdin("")

# if __name__ == "__main__":
#   arc = ArcWrapper()
#   arc.apply_setup()
# #   sleep(1)
#   arc.take_exposure(0,"test.fits",0)
# #   arc.open_shutter()
# #   arc.close_shutter()
#   sleep(0.5)
# #   arc.kill()
# #   sleep(1)