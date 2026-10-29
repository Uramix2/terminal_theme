#!/bin/sh
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 zsh tmux fzf terminator xvfb xauth >/dev/null
cd /workspace
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 xvfb-run -a python3 tests/gtk_smoke.py
