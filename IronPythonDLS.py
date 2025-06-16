import sys
import time
import clr
import socket
import json
# Add the path to the Newport DLS Command Interface DLL
sys.path.append(
    r"C:\Windows\Microsoft.NET\assembly\GAC_64\Newport.DLS.CommandInterface\v4.0_1.0.1.0__90ac4f829985d2bf"
)
clr.AddReference("Newport.DLS.CommandInterface.dll")

from CommandInterfaceDLS import *

# Constants
c = 299792458  # Speed of light in m/s
instrument = "COM6"  # Change this to the port the DLS is connected to
# Initialize the DLS
myDLS = DLS()
result = myDLS.OpenInstrument(instrument)

# Redirect stdout and stderr to a log file
log_file = open("debug_log.txt", "w")
sys.stdout = log_file
sys.stderr = log_file

if result != 0:
    sys.stderr.write(f"Failed to open instrument on {instrument}. Error code: {result}\n")
    sys.exit(1)

def Connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 9999))  # Change to your server address and port
    s.close()

def StartUp():
    errorcode = myDLS.TS()[2]
    state = myDLS.TS()[3]
    if errorcode == "00000":
        if state in ["0A", "0B", "0D"]:
            myDLS.IE()  # Initialize
            time.sleep(2)
            myDLS.OR()  # Home
            print("Controller initialized and homed.")
        elif state == "28":
            myDLS.OR()  # Home
            print("Controller homed.")
    else:
        sys.stderr.write(f"Error during startup: {errorcode}\n")

def MoveAbsolute(delay):
    state = myDLS.TS()[3]
    if state in ["46", "47", "48", "49"]:
        position = (delay * 10**-9) * c / 8
        myDLS.PA_Set(position)
        print(f"Moved to absolute position: {position} mm")
    else:
        sys.stderr.write("Controller is not in the correct state to move.\n")

def MoveRelative(delay):
    state = myDLS.TS()[3]
    if state in ["46", "47", "48", "49"]:
        position = (delay * 10**-9) * c / 8
        myDLS.PR_Set(position)
        new_position = myDLS.PA_Get()[1] * 10**9 * 8 / c
        print(f"Moved to relative position: {new_position} ps")
    else:
        sys.stderr.write("Controller is not in the correct state to move.\n")

def MeasurementLoop(delays, scans=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 9999))
    last_item = 0
    reference = myDLS.RF_Get()[1]
    while myDLS.TS()[3] not in ["46", "47", "48", "49"]:
        print("Sleeping for Reference")
        time.sleep(0.05)
    myDLS.PA_Set(reference)
    reference = myDLS.PA_Get()[1] * 10**9 * 8 / c
    print(delays)
    print("Moved to Reference")  # Set position to reference before starting measurements

    # Multiply delays for the number of scans
    repeated_delays = delays * scans

    for delay in repeated_delays:
        pos = delay - last_item
        print(pos, delay, last_item)
        while myDLS.TS()[3] not in ["46", "47", "48", "49"]:
            print("Controller not ready, waiting...")  
            time.sleep(0.05)
        ps_position = myDLS.PR_Set(pos * 10**-9 * c / 8)  # Set relative position in mm
        last_item = delay
        if ps_position is not None:
            # Send data to CPython for calculation
            data = delay
            message = json.dumps(data) + "\n"
            s.sendall(message.encode())

            # Wait for response
            buffer = b""
            while b"\n" not in buffer:
                buffer += s.recv(1024)

                if b"stop" in buffer:
                    print("Stopping measurementloop")
                    s.close()
                    return
            response = json.loads(buffer.decode().strip())
            print(f"Python response for point {delay}: {response}")
        
        else:
            print(f"Skipping point {delay} due to hardware state.")
    s.close()

def DisableReady():
    state = myDLS.TS()[3]
    if state in ["46", "47", "48", "49"]:
        myDLS.MM_Set(0)  # Disable
        print("Controller disabled.")
    elif state in ["50", "51", "52"]:
        myDLS.MM_Set(1)  # Ready
        print("Controller ready.")
    else:
        sys.stderr.write("Controller is not in a valid state to toggle.\n")

def SetReference():
    position = myDLS.PA_Get()[1]
    myDLS.RF_Set(position)
    print(f"Reference position set to: {position} mm")

def GetReference():
    reference = myDLS.RF_Get()[1] * 10**9 * 8 / c
    print(f"Reference position: {reference} ps")
    return reference

def GoToReference():
    reference = myDLS.RF_Get()[1]
    myDLS.PA_Set(reference)
    position = myDLS.PA_Get()[1] * 10**9 * 8 / c
    print(f"Moved to reference position: {position} ps")

def GetPosition():
    position = myDLS.PA_Get()[1] * 10**9 * 8 / c
    print(f"Current position: {position} ps")
    return position

def StartGUI():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print("Attempting to connect to the server...")
        for _ in range(5):  # Retry up to 5 times
            try:
                s.connect(('localhost', 9999))  # Connect to the server
                break
            except ConnectionRefusedError:
                print("Server not ready, retrying...")
                time.sleep(1)
        else:
            raise ConnectionRefusedError("Server not ready after multiple attempts.")

        print("Connected to the server.")
        

        # Gather data
        position = myDLS.PA_Get()[1] * 10**9 * 8 / c
        reference = myDLS.RF_Get()[1] * 10**9 * 8 / c
        print(f"Position: {position}, Reference: {reference}")

        # Prepare and send data
        data = {
            "position": position,
            "reference": reference,
        }
        message = json.dumps(data) + "\n"
        s.sendall(message.encode())
    except Exception as e:
        print(f"Error in StartGUI: {e}")
        raise  # Re-raise the exception for debugging
    finally:
        s.close()  # Ensure the socket is closed
    return position, reference

def Error(errorCode):
    error_messages = {
        "00001": "Bit end of run negative: Move carriage away from end/check cables",
        "00002": "Bit end of run positive: Move carriage away from end/check cables",
        "00004": "Current exceeded: Check carriage freedom",
        "00008": "Current exceeded: Check carriage freedom",
        "00010": "Controller internal fuse broken: Cycle power ON/OFF/ON",
        "00020": "PID/load parameters not optimized: Check payload weight",
        "00040": "Home search sequence time exceeded: Check acceleration settings",
    }
    message = error_messages.get(errorCode, "Unknown error.")
    sys.stderr.write(f"Error: {message}\n")

# Main logic
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        try:
            if command == "Initialize":
                StartUp()
            elif command == "MovePositive":
                MoveRelative(100)  # Adjust value if needed
                print("Moved to positive position.")
            elif command == "MoveNegative":
                MoveRelative(-100)
            elif command == "Disable":
                DisableReady()
            elif command.startswith("MoveRelative"):
                value = float(command.split()[1])
                MoveRelative(value)
            elif command.startswith("MoveAbsolute"):
                value = float(command.split()[1])
                MoveAbsolute(value)
            elif command.startswith("MeasurementLoop"):
                # Parse command: expected format "MeasurementLoop [delays] scans"
                args = command[len("MeasurementLoop"):].strip()
                if "]" in args:
                    delays_part, scans_part = args.split("]", 1)
                    delays_str = delays_part.strip().lstrip("[")
                    delays = [float(value.strip()) for value in delays_str.split(",") if value.strip()]
                    scans = int(scans_part.strip())
                else:
                    delays = []
                    scans = 1
                MeasurementLoop(delays, scans)
            elif command == "SetReference":
                SetReference()
            elif command == "GoToReference":
                GoToReference()
            elif command == "GetPosition":
                GetPosition()
            elif command == "GetReference":
                GetReference()
            elif command == "StartGUI":
                StartGUI()
            elif command == "Connect":
                Connect()
            else:
                sys.stderr.write(f"Unknown command: {command}\n")
        except Exception as e:
            sys.stderr.write(f"Error executing command '{command}': {str(e)}\n")
    else:
        sys.stderr.write("No command provided.\n")

# Close the instrument
myDLS.CloseInstrument()
import atexit

@atexit.register
def cleanup():
    log_file.close()

print(GetPosition())