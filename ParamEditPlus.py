"""
Fusion 360 Parameter Management Add-in
====================================

A comprehensive add-in for enhanced parameter management in Fusion 360 designs, providing
both command-line and direct editing interfaces for user parameters.

Key Features:
- Command-line parameter creation/modification (param = value)
- Parameter deletion via command (del param)
- Direct parameter value editing
- Multi-workspace support (Solid, Surface, Mesh, etc.)
- Real-time input validation
- Add-in reload capability

Technical Details:
----------------
- Version: 1.0
- Author: Original by @tapnair, Extended by @mccannex
- License: MIT
- Dependencies:
  * adsk.core: Core Fusion 360 API
  * adsk.fusion: Fusion 360 CAD API
  * Fusion360Utilities: Command creation utilities
- Threading: Single-threaded (Fusion 360 main thread only)
- Supported Platforms: Windows, macOS

Implementation Notes:
------------------
1. Command initialization occurs for each supported workspace
2. Parameters are validated before being applied to the model
3. Logging can be enabled for debugging purposes
"""

import copy
import adsk.core #type: ignore
from .ParamEditPlusCommand import ParamEditPlusCommand

# Set to True to display logging from within the Fusion360Utilities
debug          = False

# Set to True to enable logging from the ParamEditPlusCommand class
enable_logging = False

# Initialize lists for commands and command definitions
commands            = []
command_definitions = []

# Add simple logging functionality
def log_message(message, enable_logging=False):
    """
    @brief Logs diagnostic messages to the Fusion 360 console
    
    @param message: str - The message to be logged
    @param enable_logging: bool - Whether logging is enabled (default: False)
    
    @note Messages are prefixed with 'ParamEditPlus:' for filtering
    """
    if enable_logging:
        app = adsk.core.Application.get()
        app.log(f"ParamEditPlus: {message}")

# Define parameters for ParamEditPlusCommand base command
base_cmd = {
    'cmd_name'        : 'ParamEditPlus',
    'cmd_description' : 'Enables you to edit all User Parameters (extended)',
    'cmd_resources'   : './resources',
    'cmd_id'          : 'cmdID_ParamEditPlus',
    'toolbar_panel_id': 'SolidModifyPanel',
    'workspace'       : 'FusionSolidEnvironment',
    'class'           : ParamEditPlusCommand,
    'logger'          : log_message,
    'enable_logging'  : enable_logging
}

# @note: Thanks again to Teknicallity for the overall fix idea here
# @ref: https://github.com/mccannex/ParamEditPlus/pull/7

# Define workspace configurations
workspace_configs = {
    'Solid'  : 'SolidModifyPanel',
    'Surface': 'SurfaceModifyPanel',
    'Mesh'   : 'ParaMeshModifyPanel',
    'Form'   : 'TSplineModifyPanel',
    'Sheet'  : 'SheetMetalModifyPanel',
    'PCB'    : 'PCBModifyPanel',
    'Sketch' : 'SketchModifyPanel'
}

# Create and configure commands
for workspace_name, panel_id in workspace_configs.items():
    cmd = copy.deepcopy(base_cmd)
    cmd['cmd_id'] = f'cmdID_ParamEditPlus_{workspace_name}'
    cmd['toolbar_panel_id'] = panel_id
    # log_message(f"Initializing command for {workspace_name} workspace", enable_logging)
    command_definitions.append(cmd)

# Process the command definitions
for cmd_def in command_definitions:
    command = cmd_def['class'](cmd_def, debug)
    commands.append(command)

# log a startup message
log_message("--------------------------------", enable_logging)
log_message("ParamEditPlus startup", enable_logging)

def run(context):
    for run_command in commands:
        run_command.on_run()

def stop(context):
    for stop_command in commands:
        stop_command.on_stop()

