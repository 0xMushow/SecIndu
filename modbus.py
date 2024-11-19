from pyModbusTCP.client import ModbusClient
from time import sleep
from flask import Flask, render_template, request, redirect, url_for
import threading

slaveAddress = '192.168.56.1'
slavePort = 502

# Conveyors
startConveyor = 8
endConveyor = 9
blueConveyor = 10
greenConveyor = 11

# Sensors
blueSensor = 0
greenSensor = 1

# Pushers
bluePusher = 0
greenPusher = 1

# Registers
greenScaleRegister = 0
blueScaleRegister = 1
grayScaleRegister = 2

# Scale Actuators
blueScaleForward = 3
grayScaleForward = 4
greenScaleForward = 5

# Factory Run
factoryRun = 14

app = Flask(__name__)

factory_running = False

def start_or_stop_factory_elements(client, value):
    factory_elements = [
        factoryRun,
        startConveyor,
        endConveyor,
        blueConveyor,
        greenConveyor
    ]
    
    state = 1 if value else 0
    
    for element in factory_elements:
        client.write_single_coil(element, state)

def check_and_push(client, sensor, pusher):
    sensorStatus = client.read_discrete_inputs(sensor, 1)

    if bool(sensorStatus[0]):
        client.write_single_coil(pusher, 1)
    else:
        client.write_single_coil(pusher, 0)

def check_weight_sensors(client):
    blueWeight = client.read_input_registers(blueScaleRegister, 1)
    greenWeight = client.read_input_registers(greenScaleRegister, 1)
    grayWeight = client.read_input_registers(grayScaleRegister, 1)

    print(f"Blue: {blueWeight[0]}, Green: {greenWeight[0]}, Gray: {grayWeight[0]}")

    if blueWeight[0] > 180:
        client.write_single_coil(blueScaleForward, 1)
    else:
        client.write_single_coil(blueScaleForward, 0)

    if greenWeight[0] > 180:
        client.write_single_coil(greenScaleForward, 1)
    else:
        client.write_single_coil(greenScaleForward, 0)

    if grayWeight[0] > 210:
        client.write_single_coil(grayScaleForward, 1)
    else:
        client.write_single_coil(grayScaleForward, 0)

def run_factory(client):
    global factory_running
    factory_running = True

    start_or_stop_factory_elements(client, True)

    while factory_running:
        check_and_push(client, blueSensor, bluePusher)
        check_and_push(client, greenSensor, greenPusher)
        check_weight_sensors(client)

def stop_factory(client):
    global factory_running
    factory_running = False
    start_or_stop_factory_elements(client, False)

def start_factory_in_thread(client):
    thread = threading.Thread(target=run_factory, args=(client,))
    thread.daemon = True
    thread.start()

def establishModbusConnection(action):
    try:
        client = ModbusClient(slaveAddress, port=slavePort, unit_id=1)
        client.open()

        if not client.is_open:
            raise Exception("Failed to connect to Modbus client")

        if action == "run":
            start_factory_in_thread(client)
        elif action == "stop":
            stop_factory(client)

    except Exception as e:
        print(f"Error: {e}")
        return f"Internal server error: {e}", 500
    finally:
        client.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        establishModbusConnection("run")
        return render_template('successful.html')
    return render_template('index.html')

@app.route('/stop', methods=['POST'])
def stop():
    establishModbusConnection("stop")
    return redirect(url_for('index'))

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
