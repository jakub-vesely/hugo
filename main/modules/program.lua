--[[
    Copyright (c) 2020 jakub-vesely
    This software is published under MIT license. Full text of the licence is available on https://opensource.org/licenses/MIT
--]]


local luvent = require "Luvent"
local build_in_led = require("interfcs.build_in_led_int")
local timer = require("interfcs.timer_int")

local program_started = luvent.newEvent()
local led_state = 1

local function connect()
    program_started:addAction(
        function ()
            print("action")
            build_in_led.change_state(1)
        end
    )
end

connect()
program_started:trigger()

function After_time()
    print("after time")
    if led_state == 0 then
        led_state = 1
    else
        led_state = 0
    end
    build_in_led.change_state(led_state)
    timer.call_after_time(After_time, 0.5)

end

timer.call_after_time(After_time, 3)

--main loop
while true do
    c_task_delay() -- must be in main loop to be called watchdog
end
return 1
