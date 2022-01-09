#  Copyright (c) 2022 Jakub Vesely
#  This software is published under MIT license. Full text of the license is available at https://opensource.org/licenses/MIT

from ___logging import Logging
import machine
import time

class BlockType:
  def __init__(self, type: int, name: str):
    self.id = type
    self.name = name

class BlockBase:
  type_power = BlockType(0x08, "power_block")
  type_rgb = BlockType(0x09, "rgb_block")
  type_motor_driver = BlockType(0x0a, "motor_block")
  type_display = BlockType(0x0b, "disp_block")
  type_sound = BlockType(0x0c, "sound_block")
  type_buttom = BlockType(0x0d, "button_block")
  type_position = BlockType(0x0e, "position_block")
  type_ambient = BlockType(0x0f, "ambient_block")
  # type_id_ir = BlockType(0x10, "ir_block")

  get_module_version_command = 0xf7
  change_i2c_address_command =  0xfe

  i2c_block_type_id_base = 0xFA

  i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=100000)

  def __init__(self, block_type: int, address: int):
    self.type_id = block_type.id
    self.address = address if address else block_type.id #default block i2c address is equal to its block type
    self.logging = Logging(block_type.name)
    self.block_version = self._get_block_version()
    self.block_type_valid = False
    if not self.block_version:
      self.logging.warning("module with address 0x%x is not available", self.address)
    elif self.block_version[0] != self.type_id:
      self.logging.error("unexpected block type. expected: %d, returned: %d", self.type_id, self.block_version[0])
    else:
      self.block_type_valid = True

  def _raw_tiny_write(self, type_id: int, command: int, data=None, silent=False):
    try:
      payload = type_id.to_bytes(1, 'big') + command.to_bytes(1, 'big')

      if data:
        payload += data
      #self.logging.info(("write", payload))
      self.i2c.writeto(self.address, payload)
    except OSError:
      if not silent:
        self.logging.error("tiny-block with address 0x%02X is unavailable for writing", self.address)

  def _check_type(self, type_id):
    return type_id in (self.i2c_block_type_id_base, self.type_id) and (self.i2c_block_type_id_base or self.block_type_valid)

  def __tiny_write_common(self, type_id: int, command: int, data=None):
    """
    writes data to tiny_block via I2C
    @param type_id: block type id
    @param command: one byte command
    @param data: specify input data for entered command
    """
    if self._check_type(type_id):
      self._raw_tiny_write(type_id, command, data)
    else:
      self.logging.error("invalid block type - writing interupted")

  def _tiny_write_base_id(self, command: int, data=None):
    self.__tiny_write_common(self.i2c_block_type_id_base, command, data)

  def _tiny_write(self, command: int, data=None):
    self.__tiny_write_common(self.type_id, command, data)

  def __tiny_read_common(self, type_id: int, command: int, in_data: bytes=None, expected_length: int=0, silent=False):
    """
    reads data form tiny_block via I2C
    @param type_id: block type id
    @param command: one byte command
    @param in_data: specify input data for entered command
    @param expected_length: if defined will be read entered number of bytes. If None is expected length as a first byte
    @return provided bytes. If size is first byte is not included to output data
    """
    if self._check_type(type_id):
      self._raw_tiny_write(type_id, command, in_data, silent)
      try:
        data = self.i2c.readfrom(self.address, expected_length, True)
        #self.logging.info(("read", data))
        return data
      except OSError:
        if not silent:
          self.logging.error("tiny-block with address 0x%02X is unavailable for reading", self.address)
      return None
    else:
      self.logging.error("invalid block type - reading interupted")
      return None

  def _tiny_read_base_id(self, command: int, in_data: bytes=None, expected_length: int=0, silent=False):
    return self.__tiny_read_common(self.i2c_block_type_id_base, command, in_data, expected_length, silent)

  def _tiny_read(self, command: int, in_data: bytes=None, expected_length: int=0):
    return self.__tiny_read_common(self.type_id, command, in_data, expected_length)

  def change_block_address(self, new_address):
    self._tiny_write_base_id(self.change_i2c_address_command, new_address.to_bytes(1, 'big'))
    self.address = new_address
    time.sleep(0.1) #wait to the change is performed and stopped

  def _get_block_version(self):
    """
    returns block_type, pcb version, adjustment_version
    """
    data = self._tiny_read_base_id(self.get_module_version_command, None, 3, silent=True)
    if not data:
      return None
    return (data[0], data[1], data[2])

  def is_available(self):
    return self.block_version is not None