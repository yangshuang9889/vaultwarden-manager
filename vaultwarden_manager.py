# -*- coding: utf-8 -*-
"""
Vaultwarden Manager 入口（v1.8.0 模块化重构）
================================================================
单文件已拆分为 vwm 包（config / service / deploy / cert / backup / logs /
network / ui / app），本文件仅作入口转发，保持既有入口路径一致。
打包：PyInstaller --onefile --noconsole --name VaultwardenManager 本文件。
"""
from vwm.app import main

if __name__ == "__main__":
    main()
