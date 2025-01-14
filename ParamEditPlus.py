# Author-Patrick Rainsberry
# Description-Creates a GUI for all User Parameters
# extended from https://github.com/tapnair/ParamEdit

# Script to update all user parameters in a model
# Any variables will be loaded into the UI form with current value
# New values are validated before applying to the model. 

# Importing sample Fusion Command
# Could import multiple Command definitions here
import copy
from .ParamEditPlusCommand import ParamEditPlusCommand

commands = []
command_definitions = []

# Define parameters for vent maker command
base_cmd = {
    'cmd_name'        : 'ParamEdit Plus',
    'cmd_description' : 'Enables you to edit all User Parameters (extended)',
    'cmd_resources'   : './resources',
    'cmd_id'          : 'cmdID_ParamEditPlus',
    'workspace'       : 'FusionSolidEnvironment',
    'toolbar_panel_id': 'SolidModifyPanel',
    'class'           : ParamEditPlusCommand
}

solid_cmd = copy.deepcopy(base_cmd)
surface_cmd = copy.deepcopy(base_cmd)
mesh_cmd = copy.deepcopy(base_cmd)
form_cmd = copy.deepcopy(base_cmd)
sheet_cmd = copy.deepcopy(base_cmd)
plastic_cmd = copy.deepcopy(base_cmd)
pcb_cmd = copy.deepcopy(base_cmd)
sketch_cmd = copy.deepcopy(base_cmd)

solid_cmd['toolbar_panel_id'] = 'SolidModifyPanel'
surface_cmd['toolbar_panel_id'] = 'SurfaceModifyPanel'
mesh_cmd['toolbar_panel_id'] = 'ParaMeshModifyPanel'
form_cmd['toolbar_panel_id'] = 'TSplineModifyPanel'
sheet_cmd['toolbar_panel_id'] = 'SheetMetalModifyPanel'
pcb_cmd['toolbar_panel_id'] = 'PCBModifyPanel'
sketch_cmd['toolbar_panel_id'] = 'SketchModifyPanel'

solid_cmd['cmd_id'] = 'cmdID_ParamEditPlus_Solid'
surface_cmd['cmd_id'] = 'cmdID_ParamEditPlus_Surface'
mesh_cmd['cmd_id'] = 'cmdID_ParamEditPlus_Mesh'
form_cmd['cmd_id'] = 'cmdID_ParamEditPlus_Form'
sheet_cmd['cmd_id'] = 'cmdID_ParamEditPlus_Sheet'
pcb_cmd['cmd_id'] = 'cmdID_ParamEditPlus_PCB'
sketch_cmd['cmd_id'] = 'cmdID_ParamEditPlus_Sketch'

command_definitions.append(solid_cmd)
command_definitions.append(surface_cmd)
command_definitions.append(mesh_cmd)
command_definitions.append(form_cmd)
command_definitions.append(sheet_cmd)
command_definitions.append(pcb_cmd)
command_definitions.append(sketch_cmd)

# Set to True to display various useful messages when debugging your app
debug = False

# Don't change anything below here:
for cmd_def in command_definitions:
    command = cmd_def['class'](cmd_def, debug)
    commands.append(command)


def run(context):
    for run_command in commands:
        run_command.on_run()


def stop(context):
    for stop_command in commands:
        stop_command.on_stop()
