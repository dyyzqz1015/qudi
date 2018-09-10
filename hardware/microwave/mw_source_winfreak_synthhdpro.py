# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the Windfreak SynthHDPro microwave source.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import visa
from core.module import Base, ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge
import time


class MicrowaveSynthHDPro(Base, MicrowaveInterface):
    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'MicrowaveSynthHDPro'
    _modtype = 'mwsource'

    _serial_port = ConfigOption('serial_port', missing='error')
    _serial_timeout = ConfigOption('serial_timeout', 10, missing='warn')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        self._conn = self.rm.open_resource(
            self._serial_port,
            timeout=self._serial_timeout)

        self.mod_fw = self._conn.query('v0')
        self.mod_hw = self._conn.query('v1')
        self.model = self._conn.query('+')
        self.sernr = self._conn.query('-')
        self.log.info('Found {0} {1} hw: {2} fw: {3}'.format(
            self.model, self.sernr, self.mod_hw, self.mod_fw))
        tmp = float(self._conn.query('z?'))
        self.log.info('MW synth temperature: {0}°C'.format(tmp))
        self._off()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def get_limits(self):
        """SynthHD Pro limits"""
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.SWEEP)  # MicrowaveMode.LIST)

        limits.min_frequency = 53e6
        limits.max_frequency = 14e9

        limits.min_power = -60
        limits.max_power = 20

        limits.list_minstep = 0.01
        limits.list_maxstep = 14e9
        limits.list_maxentries = 100

        limits.sweep_minstep = 0.01
        limits.sweep_maxstep = 14e9
        limits.sweep_maxentries = 100
        return limits

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        mode = ''
        active = False
        if self.current_output_mode == MicrowaveMode.CW:
            mode = 'cw'
        elif self.current_output_mode == MicrowaveMode.LIST:
            mode = 'list'
            active = int(self._conn.query('g?')) == 1
        elif self.current_output_mode == MicrowaveMode.SWEEP:
            mode = 'sweep'
            active = int(self._conn.query('g?')) == 1
        return mode, active

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self._off()
        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        if self.current_output_mode == MicrowaveMode.CW:
            mw_cw_power = float(self._conn.query('W?'))
            return mw_cw_power
        else:

            return self.mw_sweep_power

    def get_frequency(self):
        """
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list if the device is in either list or sweep mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        if self.current_output_mode == MicrowaveMode.CW:
            mw_cw_frequency = float(self._conn.query('f?'))
            return mw_cw_frequency
        elif self.current_output_mode == MicrowaveMode.LIST:
            return self.mw_frequency_list
        elif self.current_output_mode == MicrowaveMode.SWEEP:
            mw_start_freq = float(self._conn.query('l?'))
            mw_stop_freq = float(self._conn.query('u?'))
            mw_step_freq = float(self._conn.query('s?'))
            return mw_start_freq, mw_stop_freq, mw_step_freq

    def cw_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.CW
        time.sleep(0.5)
        self.output_active = True
        self.log.info('MicrowaveDummy>CW output on')
        return 0

    def set_cw(self, frequency=None, power=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return float, float, str: current frequency in Hz, current power in dBm, current mode

        Interleave option is used for arbitrary waveform generator devices.
        """
        self.log.debug('MicrowaveDummy>set_cw, frequency: {0:f}, power {0:f}:'.format(frequency,
                                                                                      power))
        self.output_active = False
        self.current_output_mode = MicrowaveMode.CW
        if frequency is not None:
            self.mw_cw_frequency = frequency
        if power is not None:
            self.mw_cw_power = power
        return self.mw_cw_frequency, self.mw_cw_power, 'cw'

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.LIST
        time.sleep(1)
        self.output_active = True
        self.log.info('MicrowaveDummy>List mode output on')
        return 0

    def set_list(self, frequency=None, power=None):
        """
        Configures the device for list-mode and optionally sets frequencies and/or power

        @param list frequency: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return list, float, str: current frequencies in Hz, current power in dBm, current mode
        """
        self.log.debug('MicrowaveDummy>set_list, frequency_list: {0}, power: {1:f}'
                       ''.format(frequency, power))
        self.output_active = False
        self.current_output_mode = MicrowaveMode.LIST
        if frequency is not None:
            self.mw_frequency_list = frequency
        if power is not None:
            self.mw_cw_power = power
        return self.mw_frequency_list, self.mw_cw_power, 'list'

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        self._conn.write('g1')
        return 0

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.SWEEP
        self._conn.write('g1')
        mode = int(self._conn.query('g?'))
        self._on()
        return 0

    def set_sweep(self, start=None, stop=None, step=None, power=None):
        """
        Configures the device for sweep-mode and optionally sets frequency start/stop/step
        and/or power

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        self.current_output_mode = MicrowaveMode.SWEEP
        if (start is not None) and (stop is not None) and (step is not None):
            # sweep mode: linear sweep, non-continuous
            self._conn.write('X0')
            self.conn.write('c0')

            # trigger mode: single step
            self._conn.write('w2')

            # sweep direction
            if stop >= start:
                self._conn.write('^1')
            else:
                self._conn.write('^0')

            # sweep frequency and steps
            self._conn.write('l{0:5.7f}'.format(start))
            self._conn.write('u{0:5.7f}'.format(stop))
            self._conn.write('s{0:5.7f}'.format(step))

        # sweep power
        if power is not None:
            self._conn.write('W{0:2.3f}'.format(power))
            self._conn.write('[{0:2.3f}'.format(power))
            self._conn.write(']{0:2-3f}'.format(power))

        mw_start_freq = float(self._conn.query('l?'))
        mw_stop_freq = float(self._conn.query('u?'))
        mw_step_freq = float(self._conn.query('s?'))
        mw_power = float(self._conn.query('W?'))
        mw_sweep_power_start = float(self._conn.query('[?'))
        mw_sweep_power_stop = float(self._conn.query(']?'))

        return (
            mw_start_freq,
            mw_stop_freq,
            mw_step_freq,
            mw_sweep_power_start,
            'sweep'
        )

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        self._conn.write('g1')
        return 0

    def set_ext_trigger(self, pol):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)

        @return object: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING]
        """
        return TriggerEdge.FALLING

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """
        return

    def _off(self):
        self.conn.query('E0r0h0')

    def _on(self):
        self.conn.query('E1r1h1')

