#pragma once
#include <stdint.h>

#define GET_EXT_ADDRESS_COMMAND 0xfa

typedef struct tiny_common_buffer_t{
  uint8_t data[30]; //biggest is sended mesh message
  uint8_t size;
} tiny_common_buffer_t;

tiny_common_buffer_t* tiny_main_base_get_common_buffer();
void tiny_main_base_init();
void tiny_main_base_set_build_in_led(bool state);
bool tiny_main_base_send_i2c_command(uint8_t address, uint8_t block_type_id, uint8_t command, uint8_t expected_response_size);
bool tiny_main_base_send_i2c_message(uint8_t address, uint8_t expected_response_size);
uint8_t tiny_main_base_get_ext_module_address(uint8_t address);

