from ___basal.___active_variable import ActiveVariable
from ___remote_control.___remote_key import RemoteKey
class RemoteCollector:
  def __init__(self):
    self.value = ActiveVariable(RemoteKey.get_default())

  def add_remote_active_varable(self, variable:ActiveVariable):
    variable.updated(True, self._update_value, variable)

  def _update_value(self, active_variable:ActiveVariable):
    self.value.set(active_variable.get())