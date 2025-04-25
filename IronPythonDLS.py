import sys
import time
import clr

sys.path.append(
    #This path should be changed if ran on other devices.
    r"C:\Windows\Microsoft.NET\assembly\GAC_64\Newport.DLS.CommandInterface\v4.0_1.0.1.0__90ac4f829985d2bf")
clr.AddReference("Newport.DLS.CommandInterface.dll")

import System
from CommandInterfaceDLS import *

instrument = "COM6"  # Change this to the port the DLS is connected to.
myDLS = DLS()
result = myDLS.OpenInstrument(instrument)
c = 299792458 # m/s
""" 
    If you need to add a function to the document, you can look at the DL Controller Users Manual
    and look at dir(myDLS) 
"""

"""
This function is run on startup.
It initializes the controller and homes it, putting it in the ready state.
"""
errorcode = myDLS.TS()[2]
state = myDLS.TS()[3]


def StartUp():
    state = myDLS.TS()[3]
    # Check if there is an error; if not, check the state. If it is not initialized --> initialize
    if errorcode == "00000":
        if state == "0A" or state == "0B" or state == "0D":
            myDLS.IE()  # Initializing
            time.sleep(2)
            myDLS.OR()  # Homing
            position = myDLS.PA_Get()
            state = state
            return state
        if state == "28":
            myDLS.OR()
            state = state
            return state
    if errorcode != "00000":
        return Error(errorcode)


def MoveAbsolute(delay):
    state = myDLS.TS()[3]
    if state == "46" or state == "47" or state == "48" or state == "49":
        position = (delay * 10**-6) * c / 8
        myDLS.PA_Set(position)  # Move to absolute position

    else:
        print("The controller is not in the right state to move.")
        state = state
        return print(myDLS.TE())

    print("The position is now:", myDLS.PA_Get()[1], "mm")
    state = state
    return state


def MoveRelative(delay):
    state = myDLS.TS()[3]
    if state == "46" or state == "47" or state == "48" or state == "49":
        position = (delay * 10**-6) * c / 8
        myDLS.PR_Set(position)

    else:
        print("The controller is not in the right state to move.")
        state = state
        return print(myDLS.TE())

    position = myDLS.PA_Get()[1] * 1000000 * 8 / c
    print(position)
    state = state
    return state, position


"""
This function puts the controller in the disable state if in ready state and vice versa.
"""


def DisableReady():
    state = myDLS.TS()[3]
    if state == "46" or state == "47" or state == "48" or state == "49":
        myDLS.MM_Set(0)  # Disable the machine
        print("The machine is now disabled.")
    if state == "50" or state == "51" or state == "52":
        myDLS.MM_Set(1)  # Ready the machine
        print("The machine is now ready.")

    if errorcode != "00000":
        return Error(errorcode)
    state = state
    return state

def SetReference():
    state = myDLS.TS()[3]
    position = myDLS.PA_Get()[1]
    myDLS.RF_Set(position) # Set the reference position
    state = state
    return state

def GetReference():
    reference = myDLS.RF_Get()[1] * 1000000 * 8 / c
    print(reference)
    return reference

def GoToReference():
    state = myDLS.TS()[3]
    reference = myDLS.RF_Get()[1]
    myDLS.PA_Set(reference)  # Move to reference position
    position = myDLS.PA_Get()[1] * 1000000 * 8 / c
    print(position)
    state = state
    return state, position

def GetPosition():
    state = myDLS.TS()[3]
    position = myDLS.PA_Get()[1] * 1000000 * 8 / c
    print(position)
    state = state
    return state, position

""" 
Both SetAcceleration and SetVelocity functions work for the same states.
The difference between the states is that if the value is set while in configuration mode, 
the value is saved in the controller. If the value is set while in disabled or ready state,
the saved value is only saved until the controller is turned off.
"""

def SetAcceleration(acceleration):
    if state == "14":  # configuration mode
        myDLS.AC_Set(acceleration)  # Set acceleration
        print("The acceleration is now:", myDLS.AC_Get())

    possible_states = ["46", "47", "48", "49", "50", "51", "52"]
    if state in possible_states:  # disabled or ready state
        myDLS.AC_Set(acceleration)
        print("The acceleration is now:", myDLS.AC_Get())


def SetVelocity(velocity):
    if state == "14":  # configuration mode
        myDLS.VA_Set(velocity)  # Set velocity
        print("The velocity is now:", myDLS.VA_Get())

    possible_states = ["46", "47", "48", "49", "50", "51", "52"]
    if state in possible_states:  # disabled or ready state
        myDLS.VA_Set(velocity)
        print("The velocity is now:", myDLS.VA_Get())


"""
Put the controller in configuration mode or get it out of configuration mode
"""


def ConfigMode():
    possible_states = ["0A", "0B", "0C", "0D", "0E", "0F", "10", "11", "12", "13"]
    if state in possible_states:
        myDLS.PW(1)  # Set the controller in configuration mode
        print("The controller is now in configuration mode.")
        state = state
        return state
    if state == "14":
        myDLS.PW(0)
        print("The controller is now in not initialized state")
        state = state
        return state
    if state not in possible_states:
        print(
            "The controller is not in the not initialized state. Cannot enter configuration mode."
        )
        errorcode = myDLS.TS()[2]
        return Error(errorcode)


"""
This function tells the error code 
and translates the corresponding code to human language.
"""


def Error(errorCode):
    if errorCode == "00001":
        print("Bit end of run negative: Move carriage away from end/check cables")
    elif errorCode == "00002":
        print("Bit end of run positive: Move carriage away from end/check cables")
    elif errorCode == "00004":
        print(
            "The current set by the <<QIL>> has been exceeded: Check carriage freedom"
        )
    elif errorCode == "00008":
        print(
            "The current set by the <<QIR>> has been exceeded: Check carriage freedom"
        )
    elif errorCode == "00010":
        print(
            "Controller internal fuse (CMS) broken or glitch power supply: Cycle Power ON/OFF/ON"
        )
    elif errorCode == "00020":
        print(
            "Close loop (PID) or load (FMP (weight)) parameters not optimized; something interfers with the displacement: Check payload weight. Check carriage freedom. Restore Factory Settings."
        )
    elif errorCode == "00040":
        print(
            "Home search sequence time exceed time defined with <<OT>> parameter: Check that Acceleration (AC) is not too low. Restore Factory Settings."
        )

    return


if myDLS.TS()[2] != "00000":
    code = myDLS.TS()[2]
    Error(code)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "Initialize":
            StartUp()
        elif command == "MovePositive":
            MoveRelative(0.1)  # Adjust value if needed
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
        else:
            print(f"Unknown command: {command}")
    else:
        print("No command provided.")

# This shuts down the controller
myDLS.CloseInstrument()
