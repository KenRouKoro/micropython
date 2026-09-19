include(boards/mpconfigboard_esp32s3_common.cmake)

# ESP32-S3-WROOM-1U-N16R8 has 16MB flash and 8MB octal SPIRAM.
list(APPEND SDKCONFIG_DEFAULTS
    boards/sdkconfig.240mhz
    boards/sdkconfig.spiram_oct
    boards/sdkconfig.flash_qio_80m
    ${MICROPY_BOARD_DIR}/sdkconfig.board
)

set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
