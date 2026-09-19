#!/bin/bash
# 此脚本用于加载 ESP-IDF 环境变量
# 注意：请使用 source 或 . 命令执行此脚本，以便环境变量在当前终端生效
# 用法: source load_esp_idf.sh

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "警告: 此脚本应当被 source (被当前 shell 加载)，而不是直接执行。"
    echo "请使用以下命令:"
    echo "  source ./load_esp_idf.sh"
    echo "或者:"
    echo "  . ./load_esp_idf.sh"
fi

# 执行 ESP-IDF export.sh 脚本
. $HOME/.espressif/tools/activate_idf_v5.4.3.sh

# 将 idf.py 所在的目录添加到 PATH，解决 make 无法找到 idf.py 的问题
export PATH="$IDF_PATH/tools:$PATH"

# 清理 PATH，移除会导致冲突的交叉编译工具链内部子目录 (如 .../xtensa-esp-elf/xtensa-esp-elf/bin)
# 这些目录包含未加前缀的 'as', 'ld' 等，会干扰宿主机的编译 (例如 build mpy-cross 时)
export PATH=$(echo $PATH | tr ':' '\n' | grep -vE "/(xtensa-esp-elf|riscv32-esp-elf|esp32ulp-elf)/(xtensa-esp-elf|riscv32-esp-elf|esp32ulp-elf)/bin$" | paste -sd ":" -)
