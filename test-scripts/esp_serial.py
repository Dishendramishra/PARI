import serial
import serial.tools.list_ports
from time import sleep

ports = serial.tools.list_ports.comports()

target_port = None

for port, desc, hwid in sorted(ports):
    # print("{}: {} [{}]".format(port, desc, hwid))
    if "CH340" in desc:
        target_port = port

print(target_port)

while True:
        if target_port:
                ser = serial.Serial(target_port, 115200)
                # ser.write(b"status")
                # ser.flush()
                print(ser.readline().decode())
                ser.close()

