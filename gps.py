# %%
import pynmea2
import serial
import serial.tools.list_ports
from time import sleep

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
    while True:
        try:
            line = ser.readline().decode()
            # print(line,end="")
            if line.startswith("$GNRMC"):
                gps_details = pynmea2.parse(line)
                # print(line,end="")
                print("UTC Time: ",gps_details.datetime.strftime("%d-%m-%Y %H:%M"))
                print("Longitude: {}\nLatitude: {}".format(gps_details.longitude, gps_details.latitude))
                print()
        except Exception as e:
            print(str(e))
            continue
