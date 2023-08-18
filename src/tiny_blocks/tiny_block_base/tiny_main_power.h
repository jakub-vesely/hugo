#pragma once
#include <stdint.h>

typedef struct charging_state_t {
  bool is_charging: 1;
  bool is_usb_connected: 1;
}charging_state_t;

void tiny_main_power_init();
charging_state_t tiny_main_power_get_charging_state();
int32_t tiny_main_power_get_bat_voltage_mV();
int32_t tiny_main_power_get_bat_current_uA();
