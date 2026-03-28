#!/usr/bin/env python3
"""
Voice Aura - 语音输入管理器（GUI 入口）
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from frontend.main_gui import main

if __name__ == "__main__":
    main()
