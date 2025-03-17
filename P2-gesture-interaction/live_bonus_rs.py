import serial
import socket

SERIAL_PORT = '/dev/cu.usbmodem11301' 
UDP_IP = '127.0.0.1'
UDP_PORT = 5006

ser = serial.Serial(SERIAL_PORT, 9600)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    line = ser.readline().decode('utf-8').strip()
    if line in ['L', 'R', '+', '-']:
        print(f"Gesture-Pos from {SERIAL_PORT}: {line}")
        sock.sendto(line.encode(), (UDP_IP, UDP_PORT))
