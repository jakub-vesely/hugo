#  Copyright (c) 2022 Jakub Vesely
#  This software is published under MIT license. Full text of the license is available at https://opensource.org/licenses/MIT

from ___block_types import BlockTypes
from ___block_base import BlockBase
from ___active_variable import ActiveVariable
from micropython import const

_is_pressed_command = const(0x01)

class ButtonBlock(BlockBase):

  def __init__(self, address=None, measurement_period: float=0.1):
    super().__init__(BlockTypes.buttom, address)
    self.is_pressed = ActiveVariable(False, measurement_period, self._is_pressed)

  def _is_pressed(self):
    data =  self._tiny_read(_is_pressed_command, None, 1)
    return False if data[0] else True #negative logic