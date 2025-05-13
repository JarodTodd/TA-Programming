import sys
import time
import clr
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
if result != 0:
    sys.stderr.write(f"Failed to open instrument on {instrument}. Error code: {result}\n")
    sys.exit(1)

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
        position = (delay * 10**-6) * c / 8
        myDLS.PA_Set(position)
        print(f"Moved to absolute position: {myDLS.PA_Get()[1]} mm")
    else:
        sys.stderr.write("Controller is not in the correct state to move.\n")

def MoveRelative(delay):
    state = myDLS.TS()[3]
    if state in ["46", "47", "48", "49"]:
        position = (delay * 10**-6) * c / 8
        myDLS.PR_Set(position)
        new_position = myDLS.PA_Get()[1] * 1000000 * 8 / c
        print(f"Moved to relative position: {new_position} ps")
    else:
        sys.stderr.write("Controller is not in the correct state to move.\n")

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
    reference = myDLS.RF_Get()[1] * 1000000 * 8 / c
    print(f"Reference position: {reference} ps")
    return reference

def GoToReference():
    reference = myDLS.RF_Get()[1]
    myDLS.PA_Set(reference)
    position = myDLS.PA_Get()[1] * 1000000 * 8 / c
    print(f"Moved to reference position: {position} ps")

def GetPosition():
    position = myDLS.PA_Get()[1] * 1000000 * 8 / c
    print(f"Current position: {position} ps")
    return position

def StartGUI(): 
    position = myDLS.PA_Get()[1] * 1000000 * 8 / c
    reference = myDLS.RF_Get()[1] * 1000000 * 8 / c
    print(f"Starting GUI with position: {position} ps and reference: {reference} ps")
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
                MoveRelative(0.1)  # Adjust value if needed
                print("Moved to positive position.")
            elif command == "MoveNegative":
                MoveRelative(-0.1)
            elif command == "Disable":
                DisableReady()
            elif command.startswith("MoveRelative"):
                value = float(command.split()[1])
                MoveRelative(value)
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
            else:
                sys.stderr.write(f"Unknown command: {command}\n")
        except Exception as e:
            sys.stderr.write(f"Error executing command '{command}': {str(e)}\n")
    else:
        sys.stderr.write("No command provided.\n")

# Close the instrument
myDLS.CloseInstrument()
