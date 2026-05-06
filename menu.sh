#!/usr/bin/env bash

# 这是一个给非技术用户准备的菜单脚本
# 目标是把常用操作都变成中文菜单，不需要自己记命令

set -u
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

print_line() {
  printf '\n%s\n' "=================================================="
}

pause_screen() {
  printf '\n按回车继续'
  read -r _
}

ensure_env_file() {
  if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    printf '\n已自动创建 .env 文件\n'
  fi
}

ensure_python311() {
  if ! command -v python >/dev/null 2>&1; then
    printf '\n当前系统没有 python 命令\n'
    return 1
  fi

  if ! python --version 2>&1 | grep -q "3.11"; then
    printf '\n当前 python 不是 3.11\n'
    printf '请先把默认 python 切到 3.11 再继续\n'
    printf '当前版本是: '
    python --version
    return 1
  fi
}

ensure_venv() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    printf '\n还没有检测到 .venv\n'
    printf '准备使用当前 python 创建虚拟环境\n'
    ensure_python311 || return 1
    python -m venv "$VENV_DIR" || return 1
  fi
}

run_cli() {
  ensure_venv || return 1
  ensure_env_file
  PYTHONPATH="$ROOT_DIR/src" \
  MPLBACKEND=Agg \
  MPLCONFIGDIR="$ROOT_DIR/output/matplotlib" \
  "$PYTHON_BIN" -m ashare_backtest.cli "$@"
}

read_common_dates() {
  printf '开始日期 直接回车默认 20180101: '
  read -r START_DATE
  printf '结束日期 直接回车默认 20251231: '
  read -r END_DATE
}

build_date_args() {
  DATE_ARGS=()
  [[ -n "${START_DATE:-}" ]] && DATE_ARGS+=(--start "$START_DATE")
  [[ -n "${END_DATE:-}" ]] && DATE_ARGS+=(--end "$END_DATE")
}

read_strategy() {
  printf '\n可选策略\n'
  printf '1. ma_cross\n'
  printf '2. momentum\n'
  printf '3. mean_reversion\n'
  printf '4. bollinger_band\n'
  printf '请输入策略编号: '
  read -r strategy_choice

  case "$strategy_choice" in
    1) STRATEGY_NAME="ma_cross" ;;
    2) STRATEGY_NAME="momentum" ;;
    3) STRATEGY_NAME="mean_reversion" ;;
    4) STRATEGY_NAME="bollinger_band" ;;
    *) printf '\n策略编号无效\n'; return 1 ;;
  esac
}

read_strategy_args() {
  STRATEGY_ARGS=(--strategy "$STRATEGY_NAME")

  case "$STRATEGY_NAME" in
    ma_cross)
      printf '短均线窗口 直接回车默认 5: '
      read -r short_window
      printf '长均线窗口 直接回车默认 20: '
      read -r long_window
      [[ -n "$short_window" ]] && STRATEGY_ARGS+=(--short-window "$short_window")
      [[ -n "$long_window" ]] && STRATEGY_ARGS+=(--long-window "$long_window")
      ;;
    momentum)
      printf '回看窗口 直接回车默认 20: '
      read -r lookback
      printf '阈值 直接回车默认 0.03: '
      read -r threshold
      [[ -n "$lookback" ]] && STRATEGY_ARGS+=(--lookback "$lookback")
      [[ -n "$threshold" ]] && STRATEGY_ARGS+=(--threshold "$threshold")
      ;;
    mean_reversion)
      printf '均值窗口 直接回车默认 20: '
      read -r window
      printf '开仓 z 值 直接回车默认 1.5: '
      read -r entry_z
      printf '平仓 z 值 直接回车默认 0.5: '
      read -r exit_z
      [[ -n "$window" ]] && STRATEGY_ARGS+=(--window "$window")
      [[ -n "$entry_z" ]] && STRATEGY_ARGS+=(--entry-z "$entry_z")
      [[ -n "$exit_z" ]] && STRATEGY_ARGS+=(--exit-z "$exit_z")
      ;;
    bollinger_band)
      printf '布林带窗口 直接回车默认 20: '
      read -r window
      printf '标准差倍数 直接回车默认 2.0: '
      read -r num_std
      [[ -n "$window" ]] && STRATEGY_ARGS+=(--window "$window")
      [[ -n "$num_std" ]] && STRATEGY_ARGS+=(--num-std "$num_std")
      ;;
  esac
}

create_venv() {
  print_line
  printf '步骤说明\n'
  printf '这一步会在项目目录里创建 .venv\n'
  ensure_python311 || return 1
  python -m venv "$VENV_DIR" || return 1
  printf '\n虚拟环境创建完成\n'
}

install_deps() {
  print_line
  printf '步骤说明\n'
  printf '这一步会把项目依赖装进 .venv\n'
  ensure_venv || return 1
  "$PYTHON_BIN" -m pip install --upgrade pip || return 1
  "$PYTHON_BIN" -m pip install -e ".[dev]" || return 1
  ensure_env_file
  printf '\n依赖安装完成\n'
}

init_db() {
  print_line
  printf '步骤说明\n'
  printf '这一步会根据当前 .env 配置初始化数据库表\n'
  run_cli init-db
}

list_symbols() {
  print_line
  printf '当前数据库里的股票代码\n'
  run_cli list-symbols
}

fetch_one() {
  print_line
  printf '请输入 6 位股票代码 例如 600519: '
  read -r symbol
  read_common_dates
  build_date_args
  run_cli fetch --symbol "$symbol" "${DATE_ARGS[@]}"
}

fetch_many() {
  print_line
  printf '请输入多个股票代码 用逗号分隔\n'
  printf '示例 600519,000001,601318\n'
  read -r symbols
  read_common_dates
  build_date_args
  run_cli fetch --symbols "$symbols" "${DATE_ARGS[@]}"
}

fetch_watchlist() {
  print_line
  printf '这一步会抓取 .env 里的 WATCHLIST\n'
  read_common_dates
  build_date_args
  run_cli fetch --use-watchlist "${DATE_ARGS[@]}"
}

backtest_one() {
  print_line
  printf '请输入要回测的股票代码: '
  read -r symbol
  read_common_dates
  build_date_args
  read_strategy || return 1
  read_strategy_args
  run_cli backtest --symbol "$symbol" "${DATE_ARGS[@]}" "${STRATEGY_ARGS[@]}"
}

backtest_portfolio() {
  print_line
  printf '组合名称 直接回车默认 watchlist: '
  read -r portfolio_name
  printf '股票来源\n'
  printf '1. 手动输入多个股票代码\n'
  printf '2. 直接使用 .env 里的 WATCHLIST\n'
  printf '请输入编号: '
  read -r source_choice

  SYMBOL_ARGS=()
  case "$source_choice" in
    1)
      printf '请输入多个股票代码 用逗号分隔: '
      read -r symbols
      SYMBOL_ARGS=(--symbols "$symbols")
      ;;
    2)
      SYMBOL_ARGS=(--use-watchlist)
      ;;
    *)
      printf '\n来源编号无效\n'
      return 1
      ;;
  esac

  read_common_dates
  build_date_args
  read_strategy || return 1
  read_strategy_args

  if [[ -z "$portfolio_name" ]]; then
    portfolio_name="watchlist"
  fi

  run_cli backtest-portfolio "${SYMBOL_ARGS[@]}" "${DATE_ARGS[@]}" "${STRATEGY_ARGS[@]}" --portfolio-name "$portfolio_name"
}

paper_signal() {
  print_line
  printf '请输入股票代码: '
  read -r symbol
  read_common_dates
  build_date_args
  read_strategy || return 1
  read_strategy_args
  run_cli paper --symbol "$symbol" "${DATE_ARGS[@]}" "${STRATEGY_ARGS[@]}"
}

run_tests() {
  print_line
  printf '这一步会执行测试\n'
  ensure_venv || return 1
  PYTHONPATH="$ROOT_DIR/src" "$PYTHON_BIN" -m pytest
}

show_menu() {
  clear
  print_line
  printf 'A股抓取回测 项目菜单\n'
  printf '项目目录: %s\n' "$ROOT_DIR"
  print_line
  printf '1. 创建 Python 3.11 虚拟环境\n'
  printf '2. 安装项目依赖\n'
  printf '3. 初始化数据库表\n'
  printf '4. 查看数据库里已有的股票\n'
  printf '5. 抓取单只股票数据\n'
  printf '6. 抓取多只股票数据\n'
  printf '7. 抓取 WATCHLIST 里的股票\n'
  printf '8. 跑单只股票回测\n'
  printf '9. 跑组合回测\n'
  printf '10. 生成最新模拟信号\n'
  printf '11. 运行测试\n'
  printf '0. 退出\n'
  print_line
  printf '请输入编号: '
}

main_loop() {
  while true; do
    show_menu
    read -r choice

    case "$choice" in
      1) create_venv ;;
      2) install_deps ;;
      3) init_db ;;
      4) list_symbols ;;
      5) fetch_one ;;
      6) fetch_many ;;
      7) fetch_watchlist ;;
      8) backtest_one ;;
      9) backtest_portfolio ;;
      10) paper_signal ;;
      11) run_tests ;;
      0) printf '\n已退出\n'; exit 0 ;;
      *) printf '\n请输入正确编号\n' ;;
    esac

    pause_screen
  done
}

main_loop
