"""Contains the hardware interface and drivers for the FAST Pinball platform
hardware, including the FAST Core and WPC controllers as well as FAST I/O
boards.
"""

import logging
import time
#import sys
#import threading
#import queue
import traceback
import io
from distutils.version import StrictVersion
from copy import deepcopy
from serial.tools import list_ports
import struct

from mpf.core.platform import SwitchPlatform, DriverPlatform
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface
from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from mpf.platforms.interfaces.gi_platform_interface import GIPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.core.rgb_color import RGBColor

try:
    import serial
    serial_imported = True
except ImportError:
    serial_imported = False
    serial = None


class HardwarePlatform(SwitchPlatform, DriverPlatform):
    """Platform class for the FAST hardware controller.

    Args:
        machine: The main ``MachineController`` instance.

    """

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('JR Controler')
        self.log.info("Configuring JR Controller")

        if not serial_imported:
            raise AssertionError('Could not import "pySerial". This is required for '
                                 'the FAST platform interface')

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the FAST hardware can and cannot do.
        self.features['max_pulse'] = 255  # todo
        self.features['hw_rule_coil_delay'] = False  # todo
        self.features['variable_recycle_time'] = False  # todo
        self.features['variable_debounce_time'] = False  # todo
        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

        self.hw_rules = dict()
        self.dmd_connection = None
        self.net_connection = None
        self.rgb_connection = None
        self.fast_nodes = list()
        self.connection_threads = set()
        #self.receive_queue = queue.Queue()
        self.fast_leds = set()
        self.flag_led_tick_registered = False
        self.fast_io_boards = list()
        self.waiting_for_switch_data = False
        self.config = None
        self.watchdog_command = None
        self.machine_type = None
        self.hw_switch_data = {}


        self.ser=None


    def initialize(self):
        self.config = self.machine.config['jr']
        self.machine.config_validator.validate_config("jr", self.config)

        #self.watchdog_command = 'WD:' + str(hex(self.config['watchdog']))[2:]

        print("JR : " + str(self.machine.config['hardware']))

        self._connect_to_hardware()


    def __repr__(self):
        return '<Platform.JR>'

    def process_received_message(self, msg):
        """Sends an incoming message from the FAST controller to the proper
        method for servicing.
        """
        print("process_received_message TODO")
        return

    def _connect_to_hardware(self):
        liste_ports=list_ports.grep("usb")
        for i in liste_ports:
            print(i.serial_number)
            if (i.serial_number=="853323130363516072E1"):
                self.ser=serial.Serial(i.device)
            if (i.serial_number=="854383638383517120C1"):
                self.ser=serial.Serial(i.device)
            if (i.serial_number=="85438303233351D0B121"):
                self.ser=serial.Serial(i.device)
    def write(self,x):
        if self.ser:
            print("serv:"+str(x))
            self.ser.write(x)
        else:
            self._connect_to_hardware()


    def waitInterrupteurs(self):
        res={}
        if not self.ser:
            print("Pas connecte!")
            return res
        def readOnce():
            x=self.ser.read(size=2)
            if(x[:1]==b'P'): # bouton appuyé
                numero=ord(x[1:])
                res[numero]=True
            if(x[:1]==b'R'): # bouton relaché
                numero=ord(x[1:])
                res[numero]=False
            print(repr(x))
            print("RES:"+str(res))
        #readOnce()
        while(self.ser.in_waiting>=2):
            readOnce()
        return res



    def get_hw_switch_states(self):
        new_states=self.waitInterrupteurs()
        for numero, etat in new_states.items():
            self.hw_switch_data[numero].state=etat
        return {x.numero : x.state for x in self.hw_switch_data.values()}

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Set pulse on hit and enable and release and disable rule on driver."""
        pass
    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and enable and relase rule on driver."""
        #TODO
        pass
    
    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver."""
        #TODO
        pass

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Set pulse on hit rule on driver."""
        print("SET PULSE ON HIT" + str(enable_switch) + str(coil))
        drivers=(1<<int(coil.number))
        self.write(b"I")
        self.write(struct.pack("b",int(enable_switch.number)))
        self.write(struct.pack(">i",drivers))
    def stop(self):
        #TODO
        pass

    def receive_id(self, msg):
        pass

    def receive_wx(self, msg):
        pass

    def receive_ni(self, msg):
        pass

    def receive_rx(self, msg):
        pass

    def receive_dx(self, msg):
        pass

    def receive_sx(self, msg):
        pass

    def receive_lx(self, msg):
        pass

    def receive_px(self, msg):
        pass

    def receive_wd(self, msg):
        pass

    def receive_nw_open(self, msg):
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 1))

    def receive_nw_closed(self, msg):
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 1))

    def receive_local_open(self, msg):
        self.machine.switch_controller.process_switch_by_num(state=0,
                                                             num=(msg, 0))

    def receive_local_closed(self, msg):
        self.machine.switch_controller.process_switch_by_num(state=1,
                                                             num=(msg, 0))

    # def receive_sa(self, msg):
    #    print("receive SA")
    #    return 

    def configure_driver(self, config, device_type='coil'):
        print("Configure driver" + str(config))
        return JRDriver(self,config)

    def configure_switch(self, config):
        """Configures the switch object for a FAST Pinball controller.

        """
        print("Configure switch" + str(config) )
        switch=JRSwitch(config)
        self.hw_switch_data[config["number"]]=switch
        return switch 

    def tick(self, dt):
       etats_inter=self.waitInterrupteurs()
       for num, etat in etats_inter.items():
           print("NUM:"+str(num))
           self.machine.switch_controller.process_switch_by_num( str(num),state=etat)
    
    def write_hw_rule(self, switch_obj, sw_activity, driver_obj, driver_action,
                      disable_on_release=True, drive_now=False,
                      **driver_settings_overrides):
        """Used to write (or update) a hardware rule to the FAST controller.

        *Hardware Rules* are used to configure the hardware controller to
        automatically change driver states based on switch changes. These rules
        are completely handled by the hardware (i.e. with no interaction from
        the Python game code). They're used for things that you want to happen
        fast, like firing coils when flipper buttons are pushed, slingshots, pop
        bumpers, etc.

        You can overwrite existing hardware rules at any time to change or
        remove them.

        Args:
            switch_obj: Which switch you're creating this rule for. The
                parameter is a reference to the switch object itself.
            sw_activity: Int which specifies whether this coil should fire when
                the switch becomes active (1) or inactive (0)
            driver_obj: Driver object this rule is being set for.
            driver_action: String 'pulse' or 'hold' which describe what action
                will be applied to this driver
            drive_now: Should the hardware check the state of the switches when
                this rule is first applied, and fire the coils if they should
                be? Typically this is True, especially with flippers because you
                want them to fire if the player is holding in the buttons when
                the machine enables the flippers (which is done via several
                calls to this method.)

        """
        # Si on voulait envoyer plusieurs drivers .. 
        #res=0
        #for drive in self.drivers:
        #   res+=(1<<drive.numero)
        drivers=(1<<int(driver_obj.number))
        self.write(b"I")
        self.write(struct.pack("b",int(switch_obj.number)))
        self.write(struct.pack(">i",drivers))

        print("write_hw_rule"+str(switch_obj.config)+str(driver_obj.config) )
        return

    def clear_hw_rule(self, sw_name):
        """Clears a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
            sw_name: The string name of the switch whose rule you want to clear.

        """
        print("TODO TODO Clear hw_rule"+str(sw_name))  # TODO
        return


class JRSwitch(object):

    def __init__(self, config):
        self.numero=int(config["number"])
        self.number=int(config["number"])

        self.state=False

class JRDriver(DriverPlatformInterface):
    """Base class for drivers connected to a FAST Controller.

    """

    def __init__(self, platform, config):
        """
        """
        self.config=config
        self.numero=int(config["number"])
        self.platform=platform
        self.driver_settings={"pulse_ms":3,'pwm1' :'ff','pwm2':'ff','recycle_ms':'00'}
        self.number=int(config["number"])

    def reset(self):
        """

        Resets a driver

        """
        print("RESET")


    def disable(self):
        """Disables (turns off) this driver. """
        print("DISABLE" + str(self.config))
        platform.write(b"E")
        res=0
        res+=1<<self.config["numero"]
        platform.write(struct.pack(">i",res))
        return

    def enable(self):
        """Enables (turns on) this driver. """
        print("ENABLE" + str(self.config))
        platform.write(b"A")
        res=0
        res+=1<<self.config["numero"]
        platform.write(struct.pack(">i",res))
        return
    def pulse(self, milliseconds=None):
        """Pulses this driver. """
        print("PULSE" + str(self.config))
        self.platform.write(b"P")
        res=0
        res+=1<<int(self.config["number"])
        self.platform.write(struct.pack(">i",res))
        return 3
    def get_board_name(self):
        """Return the name of the board of this driver."""
        return "une seule carte"


