#!/usr/bin/env python
import asyncio
import sys

#from terminal import Terminal
from argument_processor import ArgumentProcessor
from ble import Ble
from terminal import Terminal
from hugo_logger import HugoLogger

class HugoTerminal():

  async def async_main(self, app, ble):
    try:
      await asyncio.gather(app.async_run("asyncio"), ble.async_monitor())
    except KeyboardInterrupt:
        ble.terminate()

  def main(self):
    args = ArgumentProcessor.process_cmd_arguments()
    if not args:
      return False

    logger = HugoLogger(args.verbose)
    ble = Ble(args.remote_control, args.mac_addr, logger)
    terminal = Terminal(ble, args.verbose, args.source_dir, logger)

    app = None
    if args.gui:
      from gui import Gui #arguments must be processed first. Are processed by Kivy otherwise
      app = Gui(terminal, logger)
      return asyncio.run(self.async_main(app, ble))
    else:
      logger.add_colorlog()

    terminal.run(args)

if __name__ == "__main__":
  if not HugoTerminal().main():
    sys.exit(1)


