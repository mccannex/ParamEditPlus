__author__ = 'rainsbp'

import adsk.core
import adsk.fusion
import traceback

from .Fusion360Utilities.Fusion360Utilities import get_app_objects
from .Fusion360Utilities.Fusion360CommandBase import Fusion360CommandBase

# Possibly modify the user parameters if an input with '_param_command' was entered and contains a valid expression
def maybe_modify_params(inputs):

    # Gets necessary application objects from utility function
    app_objects = get_app_objects()
    design = app_objects['design']

    # check to see if a StringValueCommandInput Object with id '_param_command' exists and is not empty
    # @ref: https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-8B9041D5-75CC-4515-B4BB-4CF2CD5BC359#StringValueCommandInput
    input = inputs.itemById('_param_command')
    if input is not None:
        if input.value != '':
            try:
                # check that input.value contains an equals sign
                if input.value.find('=') > 1:

                    # input.value contains an expression like new_param=5mm; create two strings, one for the name and one for the value
                    param_name  = input.value.split('=')[0].strip()
                    param_value = input.value.split('=')[1].strip()

                    units_manager   = app_objects['units_manager']
                    realInputNumber = units_manager.evaluateExpression(param_value, units_manager.defaultLengthUnits)
                    realValueInput  = adsk.core.ValueInput.createByReal(realInputNumber)

                    # check to see if the parameter already exists in design.userParameters
                    if design.userParameters.itemByName(param_name) is not None:
                        design.userParameters.itemByName(param_name).expression = param_value
                        app_objects['ui'].messageBox(f"Updated parameter:\n{param_name} = {design.userParameters.itemByName(param_name).expression}")
                        return True
                    
                    # otherwise, if the parameter does not exist, add it
                    design.userParameters.add(param_name, realValueInput, units_manager.defaultLengthUnits, '')
                    app_objects['ui'].messageBox(f"Added parameter:\n{param_name} = {design.userParameters.itemByName(param_name).expression}")
                    return True
                
                # also check if the input value begins with the string "del "
                elif input.value.find('del ') == 0:
                    param_name = input.value.split('del ')[1]

                    # attempt to delete the parameter
                    # @ref: https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-5f76a1ac-68fd-45da-bc7d-9bec963d775d
                    # note: there is a bug in Fusion 360 where the deleteMe() method returns True if the parameter can't be deleted 
                    # because it is being referenced by other parameters - 2023-11-15
                    if design.userParameters.itemByName(param_name).deleteMe():
                        app_objects['ui'].messageBox(f"Deleted parameter:\n{param_name}")
                        return True
                    else:
                        app_objects['ui'].messageBox(f"Unable to delete parameter:\n{param_name}")
                        return False

                # input.value does not contain an equals sign; consider this an error
                else:
                    app_objects['ui'].messageBox(f"Unable to evaluate expression:\n{input.value}")
                    return False

            # uh oh, something went wrong
            except:
                app_objects['ui'].messageBox(f"Unable to add parameter:\n{input.value}")
                return False


# Gets necessary application objects from utility function
def update_params(inputs):
    app_objects = get_app_objects()
    design = app_objects['design']
    units_manager = app_objects['units_manager']

    if inputs.count < 1:
        app_objects['ui'].messageBox('No User Parameters in the model')
        return

    # Set all parameter values based on the input form
    for param in design.userParameters:
        input_expression = inputs.itemById(param.name).value

        # Use Fusion Units Manager to validate user expression
        if units_manager.isValidExpression(input_expression, param._get_unit()): # units_manager.defaultLengthUnits):

            # Set parameter value from input form
            param.expression = input_expression

        else:
            app_objects['ui'].messageBox(f"This expression was invalid: \n{param.name}\n{input_expression}")

# @see: https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-8B9041D5-75CC-4515-B4BB-4CF2CD5BC359#BrowserCommandInput
# lots of different command input options available
class ParamEditPlusCommand(Fusion360CommandBase):
    def on_preview(self, command, inputs, args, input_values):
        update_params(inputs)

    def on_execute(self, command, inputs, args, input_values):
        # if a new param was added, don't run update_params()
        # TODO: reopen the dialog after saving if a new param was added
        if not maybe_modify_params(inputs):
            update_params(inputs)

    def on_create(self, command, inputs):
        
        # Gets necessary application objects from utility function
        app_objects = get_app_objects()
        design = app_objects['design']

        # Sort the parameters alphabetically
        sorted_params = sorted(design.userParameters, key=lambda x: x.name, reverse=False) 

        # Create a tab for the parameters command input and an html file in ./resources that explains a bit
        if inputs.itemById('group_param_command') is None:
            inputs.addGroupCommandInput('group_param_command', 'Parameter Command Input')
            groupAddNew = inputs.itemById('group_param_command').children
            new_parameter = groupAddNew.addStringValueInput('_param_command',
                                        'Parameter Command',
                                        '')
            new_parameter.tooltip = 'Allows for the creation of user parameters'
            new_parameter.tooltipDescription = (
                'Examples:\n'
                'new_param = 10mm # set/update\n'
                'del new_param # delete param'
            )

        # Create a tab that lists all existing user parameters, sorted alphabetically
        if inputs.itemById('group_user_params') is None:
            inputs.addGroupCommandInput('group_user_params', 'User Parameters')
            groupUserParams = inputs.itemById('group_user_params').children

            for param in sorted_params:
                edit_parameter = groupUserParams.addStringValueInput(param.name,
                                           param.name,
                                           param.expression)
                edit_parameter.tooltip = param.comment
        
