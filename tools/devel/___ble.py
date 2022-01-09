#  Copyright (c) 2022 Jakub Vesely
#  This software is published under MIT license. Full text of the license is available at https://opensource.org/licenses/MIT

from micropython import const
import bluetooth
import struct
from ___logging import Logging, LoggerBase
from ___planner import Planner
from ___power_mgmt import PowerMgmt, PowerPlan
from ___active_variable import ActiveVariable
import time

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_APPEARANCE = const(0x19)

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_MTU_EXCHANGED = const(21)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

_BMS_MTU = const(256)

_SHELL_COMMAND_CHAR = (
    bluetooth.UUID("48754770-0000-1000-8000-00805F9B34FB"),
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE | _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
)

_LOG_CHAR = (
    bluetooth.UUID("48754771-0000-1000-8000-00805F9B34FB"),
    _FLAG_NOTIFY | _FLAG_INDICATE
)

_KEYBOARD_CHAR = (
    bluetooth.UUID("48754772-0000-1000-8000-00805F9B34FB"),
    _FLAG_WRITE
)

_PROPERTY_CHAR = (
    bluetooth.UUID("48754773-0000-1000-8000-00805F9B34FB"),
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_INDICATE | _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
)

_HUGO_SERVICE = (
    bluetooth.UUID("4875476F-0000-1000-8000-00805F9B34FB"),
    (_SHELL_COMMAND_CHAR, _LOG_CHAR, _KEYBOARD_CHAR),
)

#FIXME
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)

class BleLogger(LoggerBase):
  def __init__(cls):
    super().__init__()

  def _log_to_ble(cls, message):
    Ble.notify_log(message)

  def log(cls, message):
    Planner.plan(cls._log_to_ble, message)

class Ble():
  _ble = None
  _shell = None
  _keyboard = None
  _shell_command_handle = None
  _log_handle = None
  _keyboard_handle = None
  _initial_time_up = None
  _running_time_up = None
  _time_down = None
  _time_to_power_save = None

  @classmethod
  def init(cls) -> None:
    PowerMgmt.register_management_change_callback(cls._set_power_save_timeouts)
    cls._set_power_save_timeouts(PowerMgmt.get_plan()) # to be set defaults
    Planner.plan(cls._check_time_to_power_save, True)

    Logging.add_logger(BleLogger())

  @classmethod
  def _set_power_save_timeouts(cls, power_plan:PowerPlan):
    cls._initial_time_up = power_plan.ble_plan.initial_time_up
    cls._running_time_up = power_plan.ble_plan.running_time_up
    cls._time_down = power_plan.ble_plan.time_down
    if cls._time_to_power_save != 0: #if ble connection is not established already
      cls._time_to_power_save = cls._initial_time_up

  @classmethod
  def _check_time_to_power_save(cls, wake_up):
    go_to_power_save = False
    if wake_up:
      PowerMgmt.block_power_save()
      if not cls._time_to_power_save: #can be reset from constructor
        cls._time_to_power_save = cls._running_time_up
      cls._start_ble()
      print("BLE power-save blocked")
    else:
      if cls._time_to_power_save: #if time was not reset externally (e.g. ble connection)
        cls._time_to_power_save -= 1
        if cls._time_to_power_save == 0: #if time has been reset by decreasing
          go_to_power_save = True
          # ble is disabled automatically when power save is activated and is enabled again when the program runs again
          # but it is not reliable (advertisement si not started) - lets do it manually
          cls._stop_ble()
          PowerMgmt.unblock_power_save()
          print("BLE power-save allowed")

    delay = cls._time_down if go_to_power_save else 1
    Planner.postpone(delay, cls._check_time_to_power_save, go_to_power_save)

  @classmethod
  def _start_ble(cls):
    cls._ble = bluetooth.BLE()
    cls._ble.active(True)
    cls._ble.config(rxbuf=_BMS_MTU)
    cls._ble.irq(cls._irq)

    #cls._ble.config(mtu=_BMS_MTU)
    ((cls._shell_command_handle, cls._log_handle, cls._keyboard_handle), ) = cls._ble.gatts_register_services((_HUGO_SERVICE,))
    cls._connections = set()
    cls._payload = cls.advertising_payload(
        name="HuGo", services=[_HUGO_SERVICE], appearance=_ADV_APPEARANCE_GENERIC_THERMOMETER
    )

    cls._advertise()

  @classmethod
  def _stop_ble(cls):
    cls.disconnect()
    cls._ble.active(False)

  @classmethod
  def get_shell(cls):
    if not cls._shell:
      from ___shell import Shell
      cls._shell = Shell()
    return cls._shell

  @classmethod
  def get_keyboard(cls):
    if not cls._keyboard:
      from ___virtual_keyboard import VirtualKeyboard
      cls._keyboard = VirtualKeyboard()
    return cls._keyboard

  @classmethod
  def _irq(cls, event, data):
    # Track connections so we can send notifications.
    if event == _IRQ_CENTRAL_CONNECT:
      cls._time_to_power_save = 0 # disable power save while a connection is active
      conn_handle, _, _ = data
      #NOTE: use when mtu is necessary to change
      connected = False
      for _ in range(3): #sometimes attempts to exchange mtu fails
        try:
          cls._ble.gattc_exchange_mtu(conn_handle)
          connected =True
          break
        except IOError:
          print("Error: gattc_exchange_mtu failed")
      if connected:
        cls._connections.add(conn_handle)
        print("BLE new connection: " + str(conn_handle))
      else:
        cls._ble.gap_disconnect(conn_handle)

    elif event == _IRQ_CENTRAL_DISCONNECT:
      conn_handle, _, _ = data
      cls._connections.remove(conn_handle)
      if not cls._connections:
        cls._time_to_power_save = cls._running_time_up # disable power save while a connection is active
      print("BLE disconnected " + str(conn_handle))
      # Start advertising again to allow a new connection.
      cls._advertise()
    elif event == _IRQ_GATTS_INDICATE_DONE:
      conn_handle, value_handle, status = data

    elif event == _IRQ_GATTS_WRITE:
      conn_handle, value_handle = data
      value = cls._ble.gatts_read(value_handle)
      if value_handle == cls._shell_command_handle:
        shell = cls.get_shell()
        ret_data = shell.command_request(value)
        if ret_data is not None:
          cls._ble.gatts_notify(conn_handle, value_handle, ret_data)

      if value_handle == cls._keyboard_handle:
          keyboard = cls.get_keyboard()
          keyboard.process_input(value)
    elif event == _IRQ_MTU_EXCHANGED:
      pass
    else:
      print("unhandled event: " + str(event))

  @classmethod
  def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack("BB", len(value) + 1, adv_type) + value

    _append(
        _ADV_TYPE_FLAGS,
        struct.pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)),
    )

    if name:
        _append(_ADV_TYPE_NAME, name)

    if services:
       _append(_ADV_TYPE_UUID16_COMPLETE, b"HuGo")

    # See org.bluetooth.characteristic.gap.appearance.xml
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))

    return payload

  @classmethod
  def _advertise(cls, interval_us=100000):
    cls._ble.gap_advertise(interval_us, adv_data=cls._payload)

  @classmethod
  def disconnect(cls):
    for connection in cls._connections:
      cls._ble.gap_disconnect(connection)

  @classmethod
  def notify_log(cls, message):
    for connection in cls._connections:
      cls._ble.gatts_notify(connection, cls._log_handle, message)
