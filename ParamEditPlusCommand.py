"""
Fusion 360 Add-in Command for Enhanced Parameter Management

This module provides an interactive command dialog for creating, modifying, and deleting
user parameters in Fusion 360 designs. It offers both a command-line style input and 
direct parameter value editing capabilities.

Key Features:
- Remove reliance on using the mouse for parameter editing
- Parameter creation/modification via command input (param = value)
- Parameter deletion (del param)
- Direct editing of existing parameters
- Add-in reload functionality
- Real-time input validation

Dependencies:
- adsk.core, adsk.fusion: Fusion 360 API
- Fusion360Utilities: Helper utilities for command creation

Threading: Runs on Fusion 360's main thread only
Version: 1.0
"""

import adsk.core   #type: ignore
import adsk.fusion #type: ignore
import os
import time
from .Fusion360Utilities.Fusion360Utilities import get_app_objects
from .Fusion360Utilities.Fusion360CommandBase import Fusion360CommandBase
import traceback
from dataclasses import dataclass
from typing import Optional

VALID_RELOAD_COMMANDS = {'reload', 'restart'}  # Using set for O(1) lookup
COMMAND_HELP_TEXT = '''<h2>Examples:</h2>
new_param = 10mm
<small>- set/update "new_param" to 10mm</small>

del new_param
<small>- delete the "new_param" parameter</small>

reload | restart
<small>- restart this add-in</small>'''

# Define unit categories and their valid units
FUSION_UNITS = {
    'LENGTH'             : {'mm', 'cm', 'm', 'hm', 'micron', 'in', 'ft', 'yd', 'mi', 'nauticalMile', 'mil'},
    'ANGLE'              : {'rad', 'deg', 'grad'},
    'CURRENCY'           : {'dol'},
    'CURRENT'            : {'A'},
    'LUMINOSITY'         : {'cd', 'EV'},
    'MASS'               : {'g', 'kg', 'slug', 'lbmass', 'ouncemass', 'tonmass'},
    'PIECES'             : {'pcs'},
    'SUBSTANCE'          : {'mole'},
    'TEMPERATURE'        : {'K', 'C', 'F', 'R'},
    'TIME'               : {'s', 'min', 'hr'},
    'SOLID_ANGLE'        : {'sr'},
    'SPEED'              : {'mps', 'fps', 'mph', 'knots'},
    'AREA'               : {'acre', 'circular_mil'},
    'VOLUME'             : {'l', 'gal', 'qt', 'pt', 'cup', 'fl_oz'},
    'PRESSURE'           : {'mPa', 'Pa', 'MPa', 'psi', 'psf', 'ksi', 'bar', 'atm', 'inH2O', 'ftH2O', 'mH2O', 'mmHg', 'inHg'},
    'FORCE'              : {'N', 'dyne', 'lbforce', 'ounceforce', 'tonforce'},
    'POWER'              : {'W', 'hp'},
    'ENERGY'             : {'J', 'erg', 'calorie', 'Btu'},
    'ANGULAR_VELOCITY'   : {'rpm'},
    'LUMINOUS_FLUX'      : {'lm'},
    'ILLUMINANCE'        : {'lx'},
    'ELECTROMOTIVE_FORCE': {'V'},
    'RESISTANCE'         : {'ohm'},
    'CHARGE'             : {'columb'},
    'CAPACITANCE'        : {'farad'},
    'CONDUCTANCE'        : {'S', 'mho'},
    'MAGNETIC_FLUX'      : {'Wb', 'maxwell'},
    'MAGNETIC_FIELD'     : {'T', 'gamma', 'gauss'},
    'INDUCTANCE'         : {'H'},
    'MAGNETIZING_FIELD'  : {'oersted'},
    'FREQUENCY'          : {'Hz'},
    'VISCOSITY'          : {'poise'},
    'FLOW_RATE'          : {'CCS', 'CIS', 'CFM', 'CMH', 'GPH', 'LPH'}
}

# Create a flat set of all valid units for quick lookup
ALL_VALID_UNITS = {unit for units in FUSION_UNITS.values() for unit in units}

@dataclass
class ParameterData:
    """Data structure for parameter information"""
    name     : str
    value    : float
    unit_type: str
    comment  : str = ''


# Command handler for the Parameter Edit Plus dialog
class ParamEditPlusCommand(Fusion360CommandBase):
    """
    Command handler for the Parameter Edit Plus dialog.
    
    Provides an enhanced parameter management interface with command-line capabilities
    and direct parameter editing. Supports real-time validation and maintains dialog
    state between executions.
    
    Inherits from: Fusion360CommandBase
    """

    # Class constructor, loads the command definition and enables logging
    # input: cmd_def, debug
    # output: None
    def __init__(self, cmd_def, debug):
        """
        @brief Initialize the command handler
        @param cmd_def: Dictionary containing command definition and configuration
        @param debug: Debug mode flag
        """
        super().__init__(cmd_def, debug)
        self.enable_logging = cmd_def.get('enable_logging', False)
        self.logger         = cmd_def.get('logger', lambda x, d: None)
        # self.app_objects    = get_app_objects()

    # Handles the reload command
    # input: command_value (either "reload" or "restart")
    # output: bool
    def _maybe_trigger_addin_reload(self, command_value: str) -> bool:
        """
        @brief Handles add-in reload/restart commands
        
        @param command_value: User input command string
        @return bool: True if reload was triggered, False otherwise
        
        Steps:
        1. Check if command matches reload keywords
        2. Locate add-in in current directory
        3. Stop current instance
        4. Start new instance
        
        @note This is used to refresh the add-in without restarting Fusion 360
        """
        if command_value.strip().lower() not in ['reload', 'restart']:
            return False
        
        app_objects = get_app_objects()
            
        # self.logger(f"fn: maybe_trigger_addin_reload()", self.enable_logging)
        try:
            # Force logging to console
            self.logger("*** Restarting ParamEditPlus ***", True)
            app = adsk.core.Application.get()
            
            # Get the direct parent directory (ParamEditPlus folder)
            current_dir = os.path.dirname(os.path.realpath(__file__))
            this_add_in = app.scripts.itemByPath(current_dir)

            if this_add_in:
                this_add_in.stop()
                time.sleep(0.5)
                this_add_in.run()
                return True
            
            app_objects['ui'].messageBox("Failed to reload add-in: Add-in not found")
            return False
            
        except Exception as e:
            app_objects['ui'].messageBox(f"Failed to reload add-in: {str(e)}")
            return False

    # Parses and validates a parameter command string.
    # input: command_value (str)
    # output: ParameterData
    def _parse_parameter_command(self, command_value: str) -> ParameterData:
        """
        Parses and validates a parameter command string.
            
        Args:
            command_value (str): Raw command string in format "name=value[unit]"
                            Examples: "width=10mm", "height=5in", "sides=6"
        
        Returns:
            ParameterData: Validated parameter information
            
        Raises:
            ValueError: If command format is invalid or parameter expression is invalid
        """
        # Validate basic command format
        if '=' not in command_value:
            raise ValueError("Invalid parameter format. Expected 'name=value'")
        
        # Split command into name and value parts
        param_name, param_value = command_value.split('=', 1)
        param_name = param_name.strip()
        param_value = param_value.strip()
        
        if not param_name or not param_value:
            self.logger(f"param_name: {param_name}, param_value: {param_value}", self.enable_logging)   
            raise ValueError("Parameter name and value cannot be empty")

        # Parse into components
        value_parts = param_value.replace(' ', '')
        numeric_part = ''.join(c for c in value_parts if c.isdigit() or c in '.-')
        unit_part = ''.join(c for c in value_parts if c.isalpha())

        # Validate numeric value
        if not numeric_part:
            self.logger(f"numeric_part: {numeric_part}", self.enable_logging)
            raise ValueError("Parameter must have a numeric value")
        
        try:
            numeric_value = float(numeric_part)
        except ValueError:
            self.logger(f"numeric_part: {numeric_part}", self.enable_logging)
            raise ValueError(f"Invalid numeric value: {numeric_part}")

        # If no unit specified, create unitless parameter
        if not unit_part:
            unit_type = ''
        else:
            # Validate unit if specified
            if unit_part not in ALL_VALID_UNITS:
                self.logger(f"unit_type: {unit_part}", self.enable_logging)
                raise ValueError(f"Invalid unit type: {unit_part}")
            unit_type = unit_part

        return ParameterData(
            name      = param_name,
            value     = numeric_value,
            unit_type = unit_type,
            comment   = ''
        )

    # Handles parameter modification
    # input: "name=value"
    # output: None
    def _handle_parameter_modification(self, command_value: str) -> None:
        """
        Handles creation or modification of Fusion 360 user parameters.
        
        Args:
            command_value (str): Raw command string in format "name=value"
        """

        app_objects = get_app_objects()

        try:
            # Parse and validate the parameter command
            param_data = self._parse_parameter_command(command_value)
            design = app_objects['design']

            # Get or create parameter
            existing_param = design.userParameters.itemByName(param_data.name)
            
            if existing_param:
                # Update existing parameter
                # method parameter objects are 1) adsk.fusion.UserParameter, 2) ParameterData
                self._assign_parameter_value(existing_param, param_data)
                self.logger(f"Updated parameter: {param_data.name} = {param_data.value}", self.enable_logging)
            else:
                # Create new parameter with the correct value from the start
                expression = f"{param_data.value} {param_data.unit_type}"
                new_param = design.userParameters.add(
                    param_data.name,
                    adsk.core.ValueInput.createByString(expression),
                    param_data.unit_type,
                    param_data.comment
                )

                if not new_param:
                    raise ValueError(f"Failed to create parameter: {param_data.name}")

                self.logger(f"Created new parameter: {param_data.name} = {expression}", self.enable_logging)

        except ValueError as ve:
            error_msg = f"Parameter validation error for input: {command_value} - {str(ve)}"
            self.logger(error_msg, self.enable_logging)
            app_objects['ui'].messageBox(error_msg)
            
        except Exception as e:
            error_msg = f"Unable to process parameter modification for input: {command_value} - {str(e)}"
            self.logger(error_msg, self.enable_logging)
            app_objects['ui'].messageBox(error_msg)

    # Handles parameter deletion
    # input: "del param_name"
    # output: None
    def _handle_parameter_deletion(self, command_value: str) -> None:
        """
        @brief Deletes a user parameter from the design
        
        @param command_value: Command string in format "del param_name"
        
        Steps:
        1. Extract parameter name from command
        2. Locate parameter in design
        3. Delete if found, show error if not found
        
        @throws Exception if parameter deletion fails
        @note Parameter deletion is irreversible
        """
        
        app_objects = get_app_objects()

        # self.logger(f"fn: _handle_parameter_deletion()", self.enable_logging)
        try:
            design = app_objects['design']
            param_name = command_value.split('del ')[1].strip()

            param = design.userParameters.itemByName(param_name)
            if param:
                param.deleteMe()
            else:
                app_objects['ui'].messageBox(f"Parameter not found: {param_name}")

        except Exception as e:
            app_objects['ui'].messageBox(f"Unable to delete parameter: {str(e)}")


    # Assigns a value to an existing Fusion 360 parameter object, handling unit conversion if needed
    # input: user_parameter (adsk.fusion.UserParameter), parameter_data (ParameterData)
    # output: None
    # throws: ValueError if the expression cannot be validated for the parameter's unit type
    def _assign_parameter_value(self, user_parameter: adsk.fusion.UserParameter, parameter_data: ParameterData) -> None:
        """
        Assigns a value to an existing Fusion 360 parameter using validated parameter data
        
        Args:
            user_parameter: Existing Fusion 360 parameter to update
            parameter_data: Validated parameter data containing new value and unit information
        
        Raises:
            ValueError: If the expression cannot be validated for the parameter's unit type
            ValueError: If attempting to convert from a unit type to no units
        """

        app_objects = get_app_objects()

        try:
            design = app_objects['design']
            
            self.logger(f"Assigning value: {parameter_data.value} {parameter_data.unit_type} to parameter: {user_parameter.name}", 
                       self.enable_logging)

            # Prevent conversion from units to no units
            if user_parameter.unit and not parameter_data.unit_type:
                raise ValueError(f"Cannot convert parameter from '{user_parameter.unit}' to no units. Only unitless parameters can be converted to specific units.")

            # Construct the expression with units
            expression = str(parameter_data.value)
            if parameter_data.unit_type:
                expression += f" {parameter_data.unit_type}"

            try:
                # If changing unit types, we need to delete and recreate
                if not user_parameter.unit and parameter_data.unit_type:
                    param_name = user_parameter.name
                    user_parameter.deleteMe()
                    new_param = design.userParameters.add(
                        param_name,
                        adsk.core.ValueInput.createByString(expression),
                        parameter_data.unit_type,
                        ''  # comment
                    )
                else:
                    # No unit change, just update the expression
                    user_parameter.expression = expression

                self.logger(f"Assignment successful: {expression}", self.enable_logging)

            except Exception as e:
                raise ValueError(
                    f"Failed to update parameter '{user_parameter.name}'\n"
                    f"Current unit type: {user_parameter.unit or '(no units)'}\n"
                    f"Attempted expression: {expression}\n"
                    f"Error: {str(e)}"
                )

        except Exception as e:
            self.logger(f"Error in _assign_parameter_value: {str(e)}", self.enable_logging)
            raise

    # Validates the command input field if present
    # called from: on_preview()
    # input: command_input
    # output: True if valid, False otherwise
    # accepted values: 
    #   - "reload" or "restart" to reload the add-in
    #   - "del param_name" to delete a parameter
    #   - "param_name = value" to create or update a parameter
    # throws: ValueError if the command input is invalid
    def _validate_command_input(self, command_input):
        """
        @brief Validates user input in the command field
        
        @param command_input: Command input field object
        @return bool: True if input is valid, False otherwise
        
        Validates:
        1. Special commands (reload/restart)
        2. Parameter creation/modification (name = value)
        3. Parameter deletion (del name)
        
        @note Sets isValueError on command_input field if validation fails
        """
        if not command_input or not command_input.value:
            return True
        
        app_objects = get_app_objects()

        try:
            command_value = command_input.value.strip()
            
            # Check for special commands first
            if command_value.lower() in VALID_RELOAD_COMMANDS:
                return True
            
            # Check for deletion command
            if command_value.startswith('del ') and bool(command_value[4:].strip()):
                return True
            
            # Validate parameter command
            if '=' in command_value:
                param_data = self._parse_parameter_command(command_value)
                
                # If updating existing parameter, check if conversion is allowed
                design = app_objects['design']
                existing_param = design.userParameters.itemByName(param_data.name)
                if existing_param and existing_param.unit and not param_data.unit_type:
                    command_input.isValueError = True
                    return False
                    
                # Validate expression against target unit type
                is_valid = app_objects['units_manager'].isValidExpression(
                    f"{param_data.value} {param_data.unit_type}",
                    param_data.unit_type
                )
                command_input.isValueError = not is_valid
                return is_valid
            
            command_input.isValueError = True
            return False
            
        except:
            command_input.isValueError = True
            self.logger("Command validation failed: exception during validation", self.enable_logging)
            self.logger(f"Input: {command_input.value}", self.enable_logging)
            return False

    # Validates all parameter fields in the group
    # input: parameter_fields_group
    # output: True if all fields are valid, False if any have errors
    def _validate_parameter_fields(self, parameter_fields_group):
        """
        @brief Validates all parameter input fields in the dialog
        
        @param parameter_fields_group: Group containing parameter input fields
        @param design: Active Fusion 360 design
        @param units_manager: Fusion 360 units manager
        @return bool: True if all fields are valid, False if any have errors
        
        Steps:
        1. Iterate through all user parameters
        2. Validate each parameter's expression
        3. Mark invalid fields with error state
        
        @note Updates UI to show validation state for each field
        """
        # self.logger(f"fn: _validate_parameter_fields()", self.enable_logging)
        if not parameter_fields_group:
            return True
        
        app_objects = get_app_objects()
            
        has_errors    = False
        units_manager = app_objects['units_manager']
        design        = app_objects['design']
        
        # Check each parameter field
        for user_parameter in design.userParameters:
            field = parameter_fields_group.children.itemById(user_parameter.name)
            if field:
                is_valid = units_manager.isValidExpression(field.value, user_parameter.unit)
                field.isValueError = not is_valid
                has_errors = has_errors or not is_valid

                # Log an invalid parameter field
                if not is_valid:
                    self.logger(f"Invalid parameter field: {user_parameter.name} = {field.value}", self.enable_logging)
                
        # if has_errors:
        #     self.logger("Parameter validation failed: has errors", self.enable_logging)
            
        return not has_errors

    # Processes the command input
    # input: inputs
    # output: None
    # throws: Exception if the command input fails
    def process_command_input(self, inputs):
        """
        @brief Processes user input from the command field
        
        @param inputs: Command inputs collection
        
        Steps:
        1. Get command input field value
        2. Route to appropriate handler based on command type:
           - Parameter creation/modification (contains '=')
           - Parameter deletion (starts with 'del')
        3. Show error message for invalid commands
        
        @note This is the main command processing entry point
        """
        # self.logger(f"fn: process_command_input()", self.enable_logging)
        
        # Check for command input field and ensure it's not empty
        command_input = inputs.itemById('command_input_field')
        if command_input is None or command_input.value == '':
            return

        command_value = command_input.value
        self.logger(f"Processing command input: {command_value}", self.enable_logging)
        
        app_objects = get_app_objects()

        try:
            # Handle parameter creation/modification
            if command_value.find('=') > 1:
                self._handle_parameter_modification(command_value)
            
            # Handle parameter deletion
            elif command_value.find('del ') == 0:
                self._handle_parameter_deletion(command_value)

            # Invalid command format
            else:
                app_objects['ui'].messageBox(f"Unable to evaluate expression: {command_value}")

        except Exception as e:
            app_objects['ui'].messageBox(f"Unable to process command: {str(e)}")

    # Updates existing parameter values based on the parameter input fields
    # input: inputs (adsk.core.Inputs)
    # output: None
    # throws: Exception if the parameter updates fail
    def process_parameter_field_updates(self, inputs):
        """
        Updates existing parameters based on dialog field values
        
        Args:
            inputs: Command inputs collection containing parameter fields
        
        Steps:
        1. Validate each parameter's new value
        2. Update valid parameters
        3. Report any invalid expressions
        """

        app_objects = get_app_objects()
        design = app_objects['design']
        
        try:
            invalid_expressions = []

            # Loop through all existing parameters and update them if the value is valid
            for user_parameter in design.userParameters:
                field = inputs.itemById(user_parameter.name)
                if not field:
                    continue
                    
                try:
                    # Check if this is an attempt to convert to unitless
                    if user_parameter.unit and not any(unit in field.value for unit in ALL_VALID_UNITS):
                        invalid_expressions.append((
                            user_parameter.name, 
                            f"Cannot convert from '{user_parameter.unit}' to no units. Parameters with units must keep their unit type."
                        ))
                        continue

                    # Create parameter data from field value and assign the value to the parameter
                    parameter_data = self._parse_parameter_command(f"{user_parameter.name}={field.value}")
                    self._assign_parameter_value(user_parameter, parameter_data)
                except ValueError as ve:
                    invalid_expressions.append((user_parameter.name, str(ve)))
            
            # Report any invalid expressions
            if invalid_expressions:
                error_msg = "Invalid expressions found:\n" + \
                           "\n".join(f"{name}: {msg}" for name, msg in invalid_expressions)
                app_objects['ui'].messageBox(error_msg)
                
        except Exception as e:
            self.logger(f"Error updating parameters: {str(e)}", self.enable_logging)
            app_objects['ui'].messageBox(f"Unable to update parameters: {str(e)}")

    # Executes the command
    def on_execute(self, command, inputs, args, input_values):
        """
        @brief Main command execution handler
        
        @param command: Command being executed
        @param inputs: Command inputs collection
        @param args: Command event arguments
        @param input_values: Dictionary of input values
        
        Steps:
        1. Check for and process command input if present
        2. Handle reload command if requested
        3. Process parameter updates for existing fields
        4. Set validation state in args
        
        @note This is called when user clicks OK or presses Enter
        """
        # self.logger(f"fn: on_execute()", self.enable_logging)
        
        app_objects = get_app_objects()

        # Check if there's a command to process
        command_input = inputs.itemById('command_input_field')
        if command_input and command_input.value:
            try:
                # Check for reload command first
                if self._maybe_trigger_addin_reload(command_input.value):
                    return
                
                # Process command first
                self.process_command_input(inputs)
                
                # Only process parameter updates for existing parameters
                if not command_input.value.find('=') > 1:  # Skip if this was a new parameter command
                    self.process_parameter_field_updates(inputs)
                    
            except Exception as e:
                app_objects['ui'].messageBox(f"Error in command execution when processing command input '{command_input.value}': {str(e)}")
                args.isValidResult = False
        else:
            self.process_parameter_field_updates(inputs)

    # This method fires when the command is created
    # This will create the dialog and the input fields
    def on_create(self, command, inputs):
        """
        @brief Creates the command dialog interface
        
        @param command: Command being created
        @param inputs: Command inputs collection to populate
        
        Creates:
        1. Command input field with help tooltip
        2. Parameter fields group
        3. Input field for each existing parameter with unit type and category tooltip
        
        @note Dialog layout is preserved between executions
        """
        # self.logger(f"fn: on_create()", self.enable_logging)
        
        app_objects = get_app_objects()

        # Create sorted list of parameters for consistent display
        sorted_parameters = sorted(app_objects['design'].userParameters, key=lambda x: x.name, reverse=False) 

        # Create command input group
        inputs.addGroupCommandInput('command_input_container', 'Command Input [tab to focus]')
        command_input_group = inputs.itemById('command_input_container').children

        # Create the main command input field with tooltip help
        # @note: Thanks to Teknicallity for the input focus fix here!:
        # - "The addBrowserCommandInput method seems to take priority of keyboard inputs, including the tab key. 
        #    By moving this text to a hover tooltip, the tab functionality is restored."
        # @ref: https://github.com/mccannex/ParamEditPlus/pull/9
        command_text_input = command_input_group.addStringValueInput(
            'command_input_field',
            'Parameter Command',
            ''
        )
        command_text_input.tooltip = 'Hover for usage examples'
        command_text_input.tooltipDescription = COMMAND_HELP_TEXT
        
        # Create parameter fields group
        inputs.addGroupCommandInput('parameter_fields_container', 'User Parameters')
        parameter_fields_group = inputs.itemById('parameter_fields_container').children

        # Create input field for each existing parameter
        for param in sorted_parameters:
            input_field = parameter_fields_group.addStringValueInput(
                param.name,
                param.name,
                param.expression
            )
            
            # Find the category - handle unitless parameters
            unit_category = 'NO_UNITS' if param.unit == '' else next(
                (category for category, units in FUSION_UNITS.items() 
                 if param.unit in units), 'UNKNOWN')
            
            # Format tooltip value based on whether it has units
            units_manager = app_objects['units_manager']
            if param.unit == '':
                formatted_value = f"{param.value:.6g}"  # Simple formatting for unitless values
            else:
                formatted_value = units_manager.formatValue(
                    param.value,
                    param.unit,
                    6,
                    False,
                    2,
                    True
                )
            
            tooltip_text = (
                f'Parameter Type: {unit_category}\n'
                f'Stored As: {"(no units)" if param.unit == "" else param.unit}\n'
                f'Current Expression: {param.expression}\n'
                f'Computed Value: {formatted_value}'
            )
            input_field.tooltip = tooltip_text

    # This method is called automatically about 1 second after any text input changes
    # It validates both the main command input field and all parameter value fields
    # The command input field is checked for valid syntax (e.g. "param = value" or "del param")
    # Parameter fields are validated to ensure they contain valid Fusion 360 expressions
    # Sets args.isValidResult to True only if all validation passes, preventing invalid inputs
    def on_preview(self, command, inputs, args, input_values):
        """
        @brief Validates all inputs during command preview
        
        @param command: Active command
        @param inputs: Command inputs collection
        @param args: Command event arguments
        @param input_values: Dictionary of input values
        
        Steps:
        1. Validate command input field
        2. Validate all parameter fields
        3. Set args.isValidResult based on validation
        
        @note Called automatically ~1 second after any input changes
        """
        # self.logger(f"fn: on_preview()", self.enable_logging)
        
        # First validate the command input
        command_input = inputs.itemById('command_input_field')
        if not self._validate_command_input(command_input):
            args.isValidResult = False
            return
            
        # If command input is valid (or empty), validate parameter fields
        parameter_fields_group = inputs.itemById('parameter_fields_container')
        if not self._validate_parameter_fields(parameter_fields_group):
            args.isValidResult = False
            return


    # This method fires when the command is destroyed
    def on_destroy(self, command, inputs, reason, input_values):
        """
        @brief Handles command destruction and manages dialog persistence
        
        @param command: Command being destroyed
        @param inputs: Command inputs collection
        @param reason: Termination reason
        @param input_values: Dictionary of input values
        
        Steps:
        1. Check termination reason
        2. If completed normally:
           - Re-open dialog
        3. Otherwise:
           - Log termination reason
        
        @note Critical for maintaining dialog persistence
        """
        app_objects = get_app_objects()

        try:
            # Only restart if the command completed normally (not cancelled)
            if reason == adsk.core.CommandTerminationReason.CompletedTerminationReason:
                self.logger("Command completed normally, re-opening dialog...", self.enable_logging)
                adsk.doEvents()
                command.parentCommandDefinition.execute()
            else:
                # Log the termination reason
                reason_name = {
                    adsk.core.CommandTerminationReason.AbortedTerminationReason      : 'Aborted',
                    adsk.core.CommandTerminationReason.CancelledTerminationReason    : 'Cancelled',
                    adsk.core.CommandTerminationReason.CompletedTerminationReason    : 'Completed',
                    adsk.core.CommandTerminationReason.PreEmptedTerminationReason    : 'PreEmpted',
                    adsk.core.CommandTerminationReason.SessionEndingTerminationReason: 'SessionEnding',
                    adsk.core.CommandTerminationReason.UnknownTerminationReason      : 'Unknown'
                }.get(reason, 'Unrecognized')
                self.logger(f"Command terminated with reason {reason_name}, not restarting", self.enable_logging)

        except:
            if app_objects['ui']:
                app_objects['ui'].messageBox('Destroy handler failed: {}'.format(traceback.format_exc()))
