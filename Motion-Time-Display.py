import time
import datetime
import board
import adafruit_dht
import PySimpleGUI as sg
from subprocess import run
import RPi.GPIO as GPIO
from threading import Thread, Event, Lock

sg.theme('Dark')
sg.set_options(element_padding=(0, 0))

font = ("Helvetica", 40)
fontB = ("Helvetica", 80)
fontS = ("Helvetica", 20)
fontDeBug = ("Helvetica", 15)
cLightB = "LightSkyBlue1"
cGray = "Gray"

layout = [[sg.Text(font=font, key='-OUTPUT-')],
          [sg.Text(font=font, key='-DAYTX-'),
          sg.Text(font=font, key='-DATETX-')],
          [sg.Text(font=fontB, text_color=cLightB, key='-TIMETX-'),
          sg.Text(font=fontS, text_color=cLightB, key='-AMPMTX-')],
          [sg.Button('Temperature', font=fontS, pad=(10, 10)),
          sg.Button('Display', font=fontS, pad=(10, 10)),
          sg.Button('Exit', font=("Helvetica", 20), pad=(10, 10))],
          [sg.Text('Temperature', font=fontDeBug,
           text_color=cGray, key='-MesTemTX-'),
          sg.Push(),
          sg.Text('Display On', font=fontDeBug,
           text_color=cGray, key='-MesDyTX-'),
          sg.Push(),
          sg.Text('Counter Motion', font=fontDeBug,
           text_color=cGray, key='-MesMotTX-')]
          ]

window = sg.Window(
    'Motion-Time-Display', layout, size=(1290, 400), element_justification="center",
    finalize=True)
window.Maximize()

# Motion Sensor
pirPin = 17
GPIO.setup(pirPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
DisplayWait = 15

# Mutex lock for shared resources
lock = Lock()

stop_event = Event()

# Global flag to indicate if the program is exiting
exiting = False

def get_temperature():
    txt = ""
    try:
        dhtDevice = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dhtDevice.humidity
        txt = f"Temp: {temperature_f:.1f} F / {temperature_c:.1f} C    Humidity: {humidity}%"
        print(txt)
        dt = datetime.datetime.now()
        lastTemReadTxt = f"Got Temperature at: {dt.strftime('%X')}"
        window['-MesTemTX-'].update(lastTemReadTxt)
    except RuntimeError as error:
        print(f"Error - {error.args[0]}")
        window.write_event_value('-MesTemTX-', "Could not get Temperature")
    return txt


def get_motion(pirPin):
    if GPIO.input(pirPin):
        global motionSensorOnOff, counter
        if exiting:
            return
        with lock:
            counter += 1
            counterTxt = "Counter Motion: {} ".format(counter)
        print(counterTxt)
        window['-MesMotTX-'].update(counterTxt)
        if motionSensorOnOff:
            # On display & wait for 15 sec
            run('vcgencmd display_power 1', shell=True)
            time.sleep(DisplayWait)
            if motionSensorOnOff:
                # off display 
                run('vcgencmd display_power 0', shell=True)
        else:
            # On display 
            run('vcgencmd display_power 1', shell=True)


def set_display_power():
    global motionSensorOnOff
    if motionSensorOnOff:
        motionSensorOnOff = False
        window['-MesDyTX-'].update("Display On")
    else:
        motionSensorOnOff = True
        window['-MesDyTX-'].update("Display Off")


def get_date_time():
    dt = datetime.datetime.now()
    timeTx = dt.strftime("%-I:%M:%S")
    ampmTx = dt.strftime(" %p ")
    dateTx = dt.strftime("%-d %b %Y")
    dayTx = dt.strftime("%a ")
    window['-TIMETX-'].update(timeTx)
    window['-AMPMTX-'].update(ampmTx)
    window['-DAYTX-'].update(dayTx)
    window['-DATETX-'].update(dateTx)


def clock(stop_event):
    while not stop_event.is_set():
        print(datetime.datetime.now().strftime("%H:%M:%S"), end="\r")
        get_date_time()
        time.sleep(1)


def cleanup():    
    print("Cleaning up GPIO event detection...")
    time.sleep(DisplayWait)
    GPIO.remove_event_detect(pirPin)
    GPIO.cleanup()  # Cleanup all GPIO channels
    print("Cleanup complete.")

time.sleep(1) # Before launch delay  
GPIO.add_event_detect(pirPin, GPIO.BOTH, callback=get_motion)
counter = 0
motionSensorOnOff = False
window['-OUTPUT-'].update(get_temperature())
get_date_time()
if __name__ == '__main__':
    thread = Thread(target=clock, args=(stop_event,))
    thread.start()
while True:
    event, values = window.read()
    print(event, values)
    if event in (None, 'Exit'):
        motionSensorOnOff = False
        exiting = True
        run('vcgencmd display_power 1', shell=True)     
        stop_event.set()
        cleanup()
        thread.join()
        break
    if event == 'Temperature':
        # Update the "output" text element
        window['-OUTPUT-'].update(get_temperature())
    if event == 'Display':
        # On / off display by motion sensor
        set_display_power()

window.close()