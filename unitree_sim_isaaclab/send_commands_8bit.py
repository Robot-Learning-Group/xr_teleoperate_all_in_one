#!/usr/bin/env python3
"""
publish reset category command to rt/reset_pose/cmd
"""

import time
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_

import threading
import math
import numpy as np
import time
from evdev import InputDevice, categorize, ecodes, list_devices

# *********
# Left stick up/down controls robot forward/backward movement
# Left stick left/right controls robot left/right movement
# Right stick up/down controls robot crouch
# Right stick left/right controls robot rotation
# *********

class LowPassFilter:
    def __init__(self, alpha=0.15):
        self.alpha = alpha
        self._value = 0.0
        self._last_value = 0.0

    def update(self, new_value, max_accel=1.5):
        delta = new_value - self._last_value
        delta = np.clip(delta, -max_accel, max_accel)
        filtered = self.alpha * (self._last_value + delta) + (1 - self.alpha) * self._value
        self._last_value = filtered
        self._value = filtered
        return self._value


class GamepadController:
    def __init__(self):
        self.control_params = {
            'x_vel': 0.0,
            'y_vel': 0.0,
            'yaw_vel': 0.0,
            'height': 0.0
        }
        self.axis_state = {
            ecodes.ABS_X: 0,
            ecodes.ABS_Y: 0,
            ecodes.ABS_RX: 0,
            ecodes.ABS_RY: 0
        }
        self.param_lock = threading.Lock()

        self._filters = {
            'x_vel': LowPassFilter(alpha=0.15),
            'y_vel': LowPassFilter(alpha=0.15),
            'yaw_vel': LowPassFilter(alpha=0.15),
            'height': LowPassFilter(alpha=0.15)
        }

        self._last_active_time = {
            'x_vel': time.time(),
            'y_vel': time.time(),
            'yaw_vel': time.time(),
            'height': time.time()
        }

        self._default_values = {
            'x_vel': 0.0,
            'y_vel': 0.0,
            'yaw_vel': 0.0,
            'height': 0.0
        }

        self._timeout_secs = 0.3
        self._debug_count = 0

        self._button_states = {}  # BTN_A: True/False

        # Start threads
        self._listener_thread = threading.Thread(target=self._gamepad_listener)
        self._listener_thread.daemon = True
        self._listener_thread.start()

        self._recovery_thread = threading.Thread(target=self._recover_inactive_axes)
        self._recovery_thread.daemon = True
        self._recovery_thread.start()
        
        for name, code in ecodes.ecodes.items():
            print(f"{name}: {code}")
        gamepad = None
        devices = [InputDevice(path) for path in list_devices()]
        for dev in devices:
            if "8BitDo" in dev.name:  # 
                gamepad = dev
                break
        for code in gamepad.capabilities().get(ecodes.EV_ABS, []):
            axis_name = ecodes.ABS[code[0]]
            abs_info = gamepad.absinfo(code[0])
            print(f"{axis_name}: min={abs_info.min}, max={abs_info.max}, fuzz={abs_info.fuzz}, flat={abs_info.flat}, resolution={abs_info.resolution}")
    
    def _map_axis_with_deadzone(self, value, deadzone=0.05, output_min=-1.0, output_max=1.0):
        """
        Map the joystick axis value to the specified range, considering the dead zone
        
        Args:
            value: original axis value (-32768 to 32767)
            deadzone: dead zone ratio (0.0 to 1.0)
            output_min: output minimum value
            output_max: output maximum value
            
        Returns:
            mapped value
        """
    
        normalized = value / 32768.0
        
        # apply dead zone
        if abs(normalized) < deadzone:
            return 0.0
        
        # remap the value outside the dead zone
        if normalized > 0:
            # positive value: map from deadzone to 1, then linearly map to [0, output_max]
            t = (normalized - deadzone) / (1.0 - deadzone)
            smooth = 6*t**5 - 15*t**4 + 10*t**3  # smooth curve
            return output_max * smooth
        else:
            # negative value: map from -deadzone to -1, then linearly map to [output_min, 0]
            t = (-normalized - deadzone) / (1.0 - deadzone)
            smooth = 6*t**5 - 15*t**4 + 10*t**3  # smooth curve
            return output_min * smooth

    def _map_forward_velocity(self, value):
        """map forward velocity: [-0.6, 1.0], push the joystick forward (negative value) to positive forward velocity"""
        # normalize to [-1, 1]
        normalized = value / 32768.0
        
        # dead zone handling
        deadzone = 0.05
        if abs(normalized) < deadzone:
            return 0.0
        
        # push the joystick forward (negative value) -> positive forward velocity [0, 1.0]
        # pull the joystick backward (positive value) -> negative forward velocity [-0.6, 0]
        if normalized < 0:
            # negative value: map from -deadzone to -1, then map to [0, 1.0]
            t = (-normalized - deadzone) / (1.0 - deadzone)
            smooth = 6*t**5 - 15*t**4 + 10*t**3
            return 1.0 * smooth
        else:
            # positive value: map from deadzone to 1, then map to [-0.6, 0]
            t = (normalized - deadzone) / (1.0 - deadzone)
            smooth = 6*t**5 - 15*t**4 + 10*t**3
            return -0.6 * smooth
    
    def _map_lateral_velocity(self, value):
        """map lateral velocity: [-0.5, 0.5]"""
        # normalize to [-1, 1]
        normalized = value / 32768.0
        
        # dead zone handling
        deadzone = 0.05
        if abs(normalized) < deadzone:
            return 0.0
        
        # map to [-0.5, 0.5]
        if normalized < 0:
            # negative value map to [-0.5, 0]
            t = (-normalized - deadzone) / (1.0 - deadzone)
            smooth = 6*t**5 - 15*t**4 + 10*t**3
            return -0.5 * smooth
        else:
            # positive value map to [0, 0.5]
            t = (normalized - deadzone) / (1.0 - deadzone)
            smooth = 6*t**5 - 15*t**4 + 10*t**3
            return 0.5 * smooth
    
    def _map_yaw_velocity(self, value):
        """map yaw velocity: [-1.57, 1.57]"""
        # normalize to [-1, 1]
        normalized = value / 32768.0
        
        # dead zone handling
        deadzone = 0.05
        if abs(normalized) < deadzone:
            return 0.0
        
        # map to [-1.57, 1.57]
        if normalized < 0:
            # negative value map to [-1.57, 0]
            t = (-normalized - deadzone) / (1.0 - deadzone)
            smooth = 6*t**5 - 15*t**4 + 10*t**3
            return -1.57 * smooth
        else:
            # positive value map to [0, 1.57]
            t = (normalized - deadzone) / (1.0 - deadzone)
            smooth = 6*t**5 - 15*t**4 + 10*t**3
            return 1.57 * smooth
    
    def _map_height(self, value):
        """map height: [-0.5, 0], when not pressed, return 0, when pressed, map to [-0.5, 0]"""
        # normalize to [-1, 1]
        normalized = value / 32768.0
        
        # dead zone handling - when not pressed, return 0
        deadzone = 0.05
        if abs(normalized) < deadzone:
            return 0.0
        
        # when pressed, map to [-0.5, 0]
        # calculate the intensity of the press (0 to 1)
        intensity = (abs(normalized) - deadzone) / (1.0 - deadzone)
        
        # ensure intensity is in [0, 1]
        intensity = max(0.0, min(1.0, intensity))
        
        # apply smooth curve
        smooth = 6*intensity**5 - 15*intensity**4 + 10*intensity**3
        
        # ensure smooth is in [0, 1]
        smooth = max(0.0, min(1.0, smooth))
        
        # map to [-0.5, 0], the heavier the press, the closer to -0.5
        result = -0.7 * smooth
        
        # extra protection: ensure the result is never positive
        return min(0.0, result)

    def _init_gamepad(self):
        devices = [InputDevice(path) for path in list_devices()]
        for dev in devices:
            if "8BitDo" in dev.name:
                print(f"find device: {dev.name}")
                return InputDevice(dev.path)
        raise Exception("no compatible gamepad device found")

    def _gamepad_listener(self):
        device = self._init_gamepad()
        try:
            for event in device.read_loop():
                if event.type == ecodes.EV_ABS:
                    self._handle_axis_event(event)
                elif event.type == ecodes.EV_KEY:
                    self._handle_button_event(event)
        except Exception as e:
            print(f"gamepad connection exception: {str(e)}")

    def _handle_axis_event(self, event):
        code = event.code
        value = event.value
        self.axis_state[code] = value
        with self.param_lock:
            if code == ecodes.ABS_Y:
                # ABS_Y control forward velocity [-0.6, 1.0]
                raw = self._map_forward_velocity(value)
                filtered_value = self._filters['x_vel'].update(raw, max_accel=0.2)
                self.control_params['x_vel'] = filtered_value
                self._last_active_time['x_vel'] = time.time()
                # print(f"[ABS_Y] original value: {value:6d}, mapped value: {raw:6.3f}, filtered value: {filtered_value:6.3f}")
                
            elif code == ecodes.ABS_X:
                # ABS_X control lateral velocity [-0.5, 0.5]
                raw = self._map_lateral_velocity(value)
                filtered_value = self._filters['y_vel'].update(raw, max_accel=0.2)
                self.control_params['y_vel'] = filtered_value
                self._last_active_time['y_vel'] = time.time()
                # print(f"[ABS_X] original value: {value:6d}, mapped value: {raw:6.3f}, filtered value: {filtered_value:6.3f}")
                
            elif code == ecodes.ABS_RX:
                # ABS_RX control yaw velocity [-1.57, 1.57]
                raw = self._map_yaw_velocity(value)
                filtered_value = self._filters['yaw_vel'].update(raw, max_accel=0.5)
                self.control_params['yaw_vel'] = filtered_value
                self._last_active_time['yaw_vel'] = time.time()
                # print(f"[ABS_RX] original value: {value:6d}, mapped value: {raw:6.3f}, filtered value: {filtered_value:6.3f}")
                
            elif code == ecodes.ABS_RY:
                # ABS_RY control height [-0.5, 0] (can only be 0 or negative)
                raw = self._map_height(value)
                filtered_value = self._filters['height'].update(raw, max_accel=0.02)
                self.control_params['height'] = filtered_value
                self._last_active_time['height'] = time.time()
                # print(f"[ABS_RY] original value: {value:6d}, mapped value: {raw:6.3f}, filtered value: {filtered_value:6.3f}")

            # self._debug_count += 1
            # if self._debug_count % 50 == 0:
            #     print(f"[SUMMARY] x_vel: {self.control_params['x_vel']:.3f}, "
            #           f"y_vel: {self.control_params['y_vel']:.3f}, "
            #           f"yaw_vel: {self.control_params['yaw_vel']:.3f}, "
            #           f"height: {self.control_params['height']:.3f}")
            #     print("-" * 60)

    def _handle_button_event(self, event):
        key_event = categorize(event)
        key_code = key_event.keycode[0] if isinstance(key_event.keycode, list) else key_event.keycode
        is_pressed = event.value == 1

        with self.param_lock:
            self._button_states[key_code] = is_pressed
        # print(f"[BUTTON] {key_code}: {'Pressed' if is_pressed else 'Released'}")

    def _recover_inactive_axes(self):
        while True:
            now = time.time()
            with self.param_lock:
                for key in self.control_params:
                    # check if the current axis value is in the dead zone
                    current_axis_in_deadzone = self._is_axis_in_deadzone(key)
                    
                    # only when the axis value is in the dead zone and exceeds the timeout time, restore the default value
                    if current_axis_in_deadzone and now - self._last_active_time[key] > self._timeout_secs:
                        if self.control_params[key] != self._default_values[key]:
                            self.control_params[key] = self._default_values[key]
            time.sleep(0.1)
    
    def _is_axis_in_deadzone(self, param_key):
        """check if the corresponding axis is in the dead zone"""
        deadzone = 0.05
        
        # check the corresponding axis according to the parameter type
        if param_key == 'x_vel':  # ABS_Y control forward
            axis_value = self.axis_state.get(ecodes.ABS_Y, 0)
        elif param_key == 'y_vel':  # ABS_X control lateral
            axis_value = self.axis_state.get(ecodes.ABS_X, 0)
        elif param_key == 'yaw_vel':  # ABS_RX control yaw
            axis_value = self.axis_state.get(ecodes.ABS_RX, 0)
        elif param_key == 'height':  # ABS_RY control height
            axis_value = self.axis_state.get(ecodes.ABS_RY, 0)
        else:
            return True  # unknown parameter, default in dead zone
        
        # normalize and check if it is in the dead zone
        normalized = axis_value / 32768.0
        return abs(normalized) < deadzone

    # === external interface ===

    def get_control_params(self):
        with self.param_lock:
            return self.control_params.copy()

    def get_button_state(self, button_name):
        with self.param_lock:
            return self._button_states.get(button_name, False)

    def get_all_button_states(self):
        with self.param_lock:
            return self._button_states.copy()



def publish_reset_category(category: int,publisher):
    # construct message
    msg = String_(data=str(category))  # pass data parameter directly during initialization

    # create publisher

    # publish message
    publisher.Write(msg)
    # print(f"published reset category: {category}")

if __name__ == "__main__":
    # initialize DDS
    ChannelFactoryInitialize(1)
    publisher = ChannelPublisher("rt/run_command/cmd", String_)
    publisher.Init()
    gamepad_controller = GamepadController()
    default_higet=0.8
    while True:
        time.sleep(0.01)
        commands = gamepad_controller.get_control_params()
        commands['height']=default_higet+commands['height']
        
        # convert to list format string [x_vel, y_vel, yaw_vel, height]
        commands_list = [float(commands['x_vel']), -float(commands['y_vel']), -float(commands['yaw_vel']), float(commands['height'])]
        commands_str = str(commands_list)
        print(f"commands: {commands_str}")
        publish_reset_category(commands_str,publisher)

    print("test publish completed")