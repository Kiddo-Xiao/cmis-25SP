import serial
from collections import deque
import numpy as np
import pickle
import time
import keras
import socket
import threading

# You might need to change this (you can find it by looking at the port in the Arduino IDE)
ARDUINO_PORT_1 = '/dev/cu.usbmodem11101' # Mac-style port
# ARDUINO_PORT_2 = '/dev/cu.usbmodem11301' # Mac-style port
# ARDUINO_PORT = 'COM7' # Windows-style port

# Open the serial port
ser_1 = serial.Serial(ARDUINO_PORT_1, 9600)
# ser_2 = serial.Serial(ARDUINO_PORT_2, 9600)

#### You probably don't want to change this ####
UDP_IP = "127.0.0.1"
UDP_PORT_1 = 5005
# UDP_PORT_2 = 5006
# create a UDP socket
sock_1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock_2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
####

window_size = 50
buffer1 = deque(maxlen=window_size)
# buffer2 = deque(maxlen=window_size)
# fill buffer with 0s
for _ in range(buffer1.maxlen):
    buffer1.append(np.zeros(6))
# for _ in range(buffer2.maxlen):
#     buffer2.append(np.zeros(6))

# change to your model path
model_path = 'models/model_Hybrid_bonus.keras'
label_encoder_path = 'models/label_encoder_Hybrid_bonus.pkl'

### FREEDOM = 9 | (l, r, u, b, x, c, e, f, o) -> (L, R, A, D, W, S, +, -) ###
prediction_to_key_1 = {
    'l': 'A',     # Move left
    'r': 'D',     # Move right
    'u': 'W',     # Move up
    'b': 'S',      # Move down
    # 'x': 'L',     # Rotate counterclockwise
    # 'c': 'R',     # Rotate clockwise 
    # 'e': '+',     # Increase size
    # 'f': '-'      # Decrease size
}
### FREEDOM = 5 | (l, r, u, b, o) -> (L, R, A, D, W, S, +, -) ###
# prediction_to_key_1 = {
#     'l': 'A',     # Move left
#     'r': 'D',     # Move right
#     'u': 'W',     # Move up
#     'b': 'S',      # Move down
# }

print("loading model and label encoder")
# load model
with open(model_path, 'rb') as f:
    model = pickle.load(f)
with open(label_encoder_path, 'rb') as f:
    label_encoder = pickle.load(f)

print("loaded everything")
def handle_serial(ser, buffer, sock, udp_port, prediction_map):
    count = 0
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            values = np.array(line.split(',')).astype(np.float32)
            # values[:3] = values[:3] / 8
            values[:3] = values[:3] / 4
            values[3:] = values[3:] / 4000
            buffer.append(list(values))
            count += 1

            # predict with the rf model
            if count % 10 == 0:
                raw_prediction = np.argmax(model.predict(np.array(buffer, dtype=np.float32).reshape(1, window_size * 6), verbose=0))
                prediction = label_encoder.inverse_transform([raw_prediction])
                # time.sleep(1500 / 1000 / 100)
                if prediction[0] == 'o':
                    continue
                else:
                    # print(f"Prediction: {prediction[0]}")
                    # convert to key
                    key = prediction_map[prediction[0]]
                    print(f"Key: {key}")

                    # send key over udp
                    sock.sendto(key.encode("utf-8"), (UDP_IP, udp_port))
        except Exception as e:
            print(e)

ser1 = serial.Serial(ARDUINO_PORT_1, 9600)
# ser2 = serial.Serial(ARDUINO_PORT_2, 9600)

handle_serial(ser1, buffer1, sock_1, UDP_PORT_1, prediction_to_key_1)
# handle_serial(ser2, buffer2, sock_2, UDP_PORT_2, prediction_to_key_2)
