"""
This bluefruit connects to the sipeed MaixSense A010 over UART
and attempts to read the image packets.
NOTES:
- It has been noted that when not much data is available on the 
"image frame" returned by the UART,
it seems to mean there is an object blocking the camera.
- The LCD in the MaixSense A010 recognizes when the "path" in front
  of the camera is blocked or   when it is open. However I couldn't
  find a message type that returns such information.
  Perhaps it's available in the "Other Data" section of the header
  but it's not documented.   As such the bluefruit attempts to find
  if the data is blocked by finding an average.
  Documentation:
  - https://wiki.sipeed.com/hardware/en/maixsense/maixsense-a010/maixsense-a010.html
  - https://wiki.sipeed.com/hardware/en/maixsense/maixsense-a010/at_command_en.html
CONDITIONS IN WHICH THIS MAY WORK:
- The current image is transformed to 25x25 pixels, yielding 625 
  measurements in total.
- The current readsize attempts to read during 1 second 1K bytes,
  which should be "hopefully"   more than 1 full image but less 
  than two.
- The first bytes are going to be dropped because they may be part 
  of a "previous frame".
- The first time the headers are recognized, the "image processing"
  on the side of the bluefruit starts.
- The current values found by talking through the UART are:
  # ISP: Default is on (value 1)
  # uart.write(b"AT+ISP?\r")
  # DISP Set UART display on, default is LCD display on (value 1)
  # uart.write(b"AT+DISP=4\r")
  # BAUDS Default is 115200 (value 2)
  # uart.write(b"AT+BAUD?\r")
  # UNIT Default is auto, (value 0)
  # uart.write(b"AT+UNIT?\r")
  # FPS Default is 15 (value 15)
  # uart.write(b"AT+FPS?\r")
- For Wiring, see the wiring.png image on the repo.
"""

import board
import busio

# import digitalio
import time
from adafruit_circuitplayground import cp

# The TX
uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=1)

# Change from 100x100 pixels to 25x25, this to reduce the load on 
# the bluefruit.
uart.write(b"AT+BINN=4\r")  # Change from 100x100 pixels to 25x25
data = uart.read(32)
print("".join([chr(b) for b in data]), end="")

# Set both lcd and uart display on, TODO: change to 4 for only UART
# when stable.
uart.write(b"AT+DISP=5\r")
# Read the acknowledgement of the operation, should be an "OK"
data = uart.read(32)
print("".join([chr(b) for b in data]), end="")

##### CONSTANTS #####
# Read these many bytes per measuremente.
READ_SIZE = 1024
# By default do not print stuff.
DEBUG = False
# The returned camera measurements are averaged and if the average
# is more than this we set the LEDs in warning state.
AVG_WARNING_THRESHOLD = 152

# Change the timeout to return data as soon as possible:
uart.timeout = 0

while True:
    #15 FPS means we would reach many images, let's read a "batch"
    # of bytes and find one image only. 
    data = uart.read(READ_SIZE)
    if data is None or len(data) == 0:
        continue
    i = 0
    # Find a Header 2 bytes: 0X00, 0XFF in the first half of the READ_SIZE
    while i + 1 < len(data) and data[i] != 0x00 and data[i+1] != 0xff:
        i+=1
    i += 2 # consume the header
    # Packet length 2 bytes: the number of bytes of remaining data 
    # in the current packet
    packet_length = int.from_bytes(data[i:i+2], 'little')
    if DEBUG:
        print("[{}]Packet length: {}, bytes: {}".format(
          i, # The current index in the read bytes.
          packet_length,
          ["0x{0:0>2x}".format(x) for x in data[i:i+2]])
        )
    if packet_length == 0:
        # The sensor is blocked and it returns 0 packet length 
        # chunks it *SEEMS*
        print("Blocked")
        # Turn all the pixels into solid RED
        cp.pixels.fill((50, 0, 0))
        # Play a tone to alert
        cp.play_tone(1024, 0.2)
        # Wait a bit.
        time.sleep(0.2)
        continue
    # consume the packet length (2 bytes) 
    # and "other content" (16 bytes).
    i += 18 
    # Other content 16 bytes: including packet serial number, 
    # packet length, resolution, etc.
    if packet_length + i > len(data):
        # Do not read out of bounds, we may have a packet
        # an image that didn't fit in our read-buffer.
        packet_length = len(data) - i
    # The image payload would be stored here:
    payload = data[i:i+packet_length]
    if packet_length + i < len(data) and data[i+packet_length] != 0xdd:
        # According to the documentation we should find a byte 0xdd here...
        # But in practice it doesn't always include that.
        if DEBUG:
            print("Byte at end of packet not found... ")
    # Prevent division by zero:
    if len(payload) == 0:
        continue
    avg = sum(payload) / len(payload)
    if avg < AVG_WARNING_THRESHOLD:
        cp.pixels.fill((50, 0, 50))
        cp.play_tone(512, 0.2)
    else:
        cp.pixels.fill((0, 0, 0))
    time.sleep(0.2)

