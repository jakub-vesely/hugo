
/*
 * Copyright (c) 2020 jakub-vesely
 * This software is published under MIT license. Full text of the licence is available at https://opensource.org/licenses/MIT
 *
 * This component is based on https://github.com/yanbe/ssd1306-esp-idf-i2c
 */

#include "ssd1306.h"
#include <event_loop.h>
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <i2c.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>


#define TAG "ssd_1306"
#define COLUMNS 128
#define PAGES 8
#define PAGE_SIZE  8 //8 bits
#define BUFFER_SIZE (COLUMNS * PAGES)

#define OLED_I2C_ADDRESS   0x3C // SLA (0x3C) + WRITE_MODE (0x00) =  0x78 (0b01111000)
#define OLED_CONTROL_BYTE_CMD_SINGLE    0x80
#define OLED_CONTROL_BYTE_CMD_STREAM    0x00
#define OLED_CONTROL_BYTE_DATA_STREAM   0x40
#define OLED_CMD_SET_CHARGE_PUMP        0x8D    // follow with 0x14
#define OLED_CMD_SET_SEGMENT_REMAP      0xA1
#define OLED_CMD_SET_COM_SCAN_MODE      0xC8
#define OLED_CMD_DISPLAY_ON             0xAF

static uint8_t _buffer[BUFFER_SIZE];
static bool _invert = false;

static display_adapter_t _display_adapter;

static int s_init_event_id = -1;
static int s_flush_event_id = -1;

static void _init_ssd1306_event_action(event_data_t _data, int _data_size) {
    uint8_t init_sequence[] = {
        0x00, // normal orinvert
        OLED_CMD_SET_CHARGE_PUMP, 0x14, //0x14 VCC generated by internal DC/DC circuit
        OLED_CMD_SET_SEGMENT_REMAP,
        OLED_CMD_SET_COM_SCAN_MODE,
        0x21, 0x00,
        0x7f,
        OLED_CMD_DISPLAY_ON
    };
    init_sequence[0] = _invert ? 0xA7 : 0xA6;
    hugo_i2c_write_command_with_data(OLED_I2C_ADDRESS, OLED_CONTROL_BYTE_CMD_STREAM, init_sequence, sizeof(init_sequence));
}

void _flush_event_action(event_data_t _data, int _data_size) {
    for (uint8_t row = 0; row < 8; ++row) {
        uint8_t select_block = 0xB0 | row;
        hugo_i2c_write_command_with_data(OLED_I2C_ADDRESS, OLED_CONTROL_BYTE_CMD_SINGLE, &select_block, 1);
        hugo_i2c_write_command_with_data(OLED_I2C_ADDRESS, OLED_CONTROL_BYTE_DATA_STREAM, _buffer + row * 128, 128);
    }
}

void _clean_buffer() {
    memset(_buffer, _invert ? 0xff : 0, BUFFER_SIZE);
}

static int _get_buff_pos(int x, int y) {
    return (y / PAGE_SIZE) * COLUMNS + x;
}

bool _get_point(int x, int y) {
    return _buffer[_get_buff_pos(x, y)];
}

bool _set_point(int x, int y, bool color) {
    if (x < 0 || x >= COLUMNS || y < 0 || y >= PAGES * PAGE_SIZE) {
        return false;
    }
    int buf_pos = _get_buff_pos(x, y);

    int value = 1 << (y % PAGE_SIZE);
    if (color != _invert) {
        _buffer[buf_pos] |= value;
    }
    else {
        _buffer[buf_pos] &= ~value;
    }
    return true;
}

static void _showtime() {
    hugo_raise_event(EVENT_LOOP_TYPE_PERIPHERAL, s_flush_event_id, NULL, 0);
}

static void _register_events() {
    s_init_event_id = hugo_get_new_event_id(EVENT_LOOP_TYPE_PERIPHERAL);
    hugo_add_event_action(EVENT_LOOP_TYPE_PERIPHERAL, s_init_event_id, _init_ssd1306_event_action);

    s_flush_event_id = hugo_get_new_event_id(EVENT_LOOP_TYPE_PERIPHERAL);
    hugo_add_event_action(EVENT_LOOP_TYPE_PERIPHERAL, s_flush_event_id, _flush_event_action);
}

display_adapter_t *hugo_ssd1306_init(bool invert) {
    _invert = invert;
    _clean_buffer();
    _showtime();

    _display_adapter.width = COLUMNS;
    _display_adapter.height = PAGE_SIZE * PAGES;
    _display_adapter.get_point = _get_point;
    _display_adapter.set_point = _set_point;
    _display_adapter.clean = _clean_buffer;
    _display_adapter.showtime = _showtime;

    _register_events();
    hugo_raise_event(EVENT_LOOP_TYPE_PERIPHERAL, s_init_event_id, NULL, 0);

    return &_display_adapter;
}
