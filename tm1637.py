import math
import RPi.GPIO as IO
import threading
from time import sleep, localtime
# from tqdm import tqdm

# IO.setwarnings(False)
IO.setmode(IO.BCM)

HexDigits = [0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d,
             0x07, 0x7f, 0x6f, 0x77, 0x7c, 0x39, 0x5e, 0x79, 0x71]

ADDR_AUTO = 0x40
ADDR_FIXED = 0x44
STARTADDR = 0xC0
# DEBUG = False


class TM1637:
    __doublePoint = False
    __Clkpin = 0
    __Datapin = 0
    __brightness = 1.0  # default to max brightness
    __currentData = [0, 0, 0, 0, 0, 0]

    def __init__(self, CLK, DIO, brightness):
        self.__Clkpin = CLK
        self.__Datapin = DIO
        self.__brightness = brightness
        IO.setup(self.__Clkpin, IO.OUT)
        IO.setup(self.__Datapin, IO.OUT)

    def cleanup(self):
        """Stop updating clock, turn off display, and cleanup GPIO"""
        self.StopClock()
        self.Clear()
        IO.cleanup()

    def Clear(self):
        b = self.__brightness
        point = self.__doublePoint
        self.__brightness = 0
        self.__doublePoint = False
        data = [0x7F, 0x7F, 0x7F, 0x7F, 0x7F, 0x7F]
        self.Show(data)
        # Restore previous settings:
        self.__brightness = b
        self.__doublePoint = point

    def ShowInt(self, i):
        s = str(i)
        self.Clear()
        for i in range(0, len(s)):
            self.Show1(i, int(s[i]))

    def Show(self, data):
        for i in range(0, 6):
            self.__currentData[i] = data[i]
       
        self.start()
        self.writeByte(ADDR_AUTO)
        self.br()
        self.writeByte(STARTADDR)
        #for i in range(0, 4):
        # here we correct for weird digit order of [2][1][0][5][4][3]
        for i in [2,1,0,5,4,3]
            self.writeByte(self.coding(data[i]))
        self.br()
        self.writeByte(0x88 + int(self.__brightness))
        self.stop()

    def Show1(self, DigitNumber, data):
        """show one Digit (number 0...5)"""
        if(DigitNumber < 0 or DigitNumber > 5):
            return  # error

        self.__currentData[DigitNumber] = data

        self.start()
        self.writeByte(ADDR_FIXED)
        self.br()
        self.writeByte(STARTADDR | DigitNumber)
        self.writeByte(self.coding(data))
        self.br()
        self.writeByte(0x88 + int(self.__brightness))
        self.stop()
    
    # Scrolls any integer n (can be more than 4 digits) from right to left display.
    def ShowScroll(self, n):
        n_str = str(n)
        k = len(n_str)

        for i in range(0, k + 6):
            if (i < k):
                self.Show([int(n_str[i-5]) if i-5 >= 0 else None, int(n_str[i-2]) if i-2 >= 0 else None, int(n_str[i-1]) if i-1 >= 0 else None, int(n_str[i]) if i >= 0 else None])
            elif (i >= k):
                self.Show([int(n_str[i-5]) if (i-5 < k and i-5 >= 0) else None, int(n_str[i-4]) if (i-4 < k and i-4 >= 0) else None, int(n_str[i-1]) if (i-1 < k and i-1 >= 0) else None, None])
            sleep(1)

    def SetBrightness(self, percent):
        """Accepts percent brightness from 0 - 1"""
        max_brightness = 7.0
        brightness = math.ceil(max_brightness * percent)
        if (brightness < 0):
            brightness = 0
        if(self.__brightness != brightness):
            self.__brightness = brightness
            self.Show(self.__currentData)

    def ShowDoublepoint(self, on):
        """Show or hide double point divider"""
        if(self.__doublePoint != on):
            self.__doublePoint = on
            self.Show(self.__currentData)

    def writeByte(self, data):
        for i in range(0, 8):
            IO.output(self.__Clkpin, IO.LOW)
            if(data & 0x01):
                IO.output(self.__Datapin, IO.HIGH)
            else:
                IO.output(self.__Datapin, IO.LOW)
            data = data >> 1
            IO.output(self.__Clkpin, IO.HIGH)

        # wait for ACK
        IO.output(self.__Clkpin, IO.LOW)
        IO.output(self.__Datapin, IO.HIGH)
        IO.output(self.__Clkpin, IO.HIGH)
        IO.setup(self.__Datapin, IO.IN)

        while(IO.input(self.__Datapin)):
            sleep(0.001)
            if(IO.input(self.__Datapin)):
                IO.setup(self.__Datapin, IO.OUT)
                IO.output(self.__Datapin, IO.LOW)
                IO.setup(self.__Datapin, IO.IN)
        IO.setup(self.__Datapin, IO.OUT)

    def start(self):
        """send start signal to TM1637"""
        IO.output(self.__Clkpin, IO.HIGH)
        IO.output(self.__Datapin, IO.HIGH)
        IO.output(self.__Datapin, IO.LOW)
        IO.output(self.__Clkpin, IO.LOW)

    def stop(self):
        IO.output(self.__Clkpin, IO.LOW)
        IO.output(self.__Datapin, IO.LOW)
        IO.output(self.__Clkpin, IO.HIGH)
        IO.output(self.__Datapin, IO.HIGH)

    def br(self):
        """terse break"""
        self.stop()
        self.start()

    def coding(self, data):
        if(self.__doublePoint):
            pointData = 0x80
        else:
            pointData = 0

        if(data == 0x7F or data is None):
            data = 0
        else:
            data = HexDigits[data] + pointData
        return data

    def clock(self, military_time):
        """Clock script modified from:
            https://github.com/johnlr/raspberrypi-tm1637"""
        self.ShowDoublepoint(True)
        while (not self.__stop_event.is_set()):
            t = localtime()
            hour = t.tm_hour
            if not military_time:
                hour = 12 if (t.tm_hour % 12) == 0 else t.tm_hour % 12
            d0 = hour // 10 if hour // 10 else 0
            d1 = hour % 10
            d2 = t.tm_min // 10
            d3 = t.tm_min % 10
            d4 = t.tm_sec // 10
            d5 = t.tm_sec % 10
            digits = [d0, d1, d2, d3, d4, d5]
            self.Show(digits)
            # # Optional visual feedback of running alarm:
            # print digits
            # for i in tqdm(range(60 - t.tm_sec)):
            for i in range(60 - t.tm_sec):
                if (not self.__stop_event.is_set()):
                    sleep(1)

    def StartClock(self, military_time=True):
        # Stop event based on: http://stackoverflow.com/a/6524542/3219667
        self.__stop_event = threading.Event()
        self.__clock_thread = threading.Thread(
            target=self.clock, args=(military_time,))
        self.__clock_thread.start()

    def StopClock(self):
        try:
            print 'Attempting to stop live clock'
            self.__stop_event.set()
        except:
            print 'No clock to close'
