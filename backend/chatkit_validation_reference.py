#!/usr/bin/env python3
"""
ChatKit Widget Validation Reference
Documents the valid parameter values for ChatKit widgets to prevent validation errors.
"""

# Valid parameter values for ChatKit widgets
CHATKIT_VALIDATION_RULES = {
    "Button": {
        "variant": ["solid", "soft", "outline", "ghost"],
        "size": ["xs", "sm", "md", "lg", "xl"],
        "action_param": "onClickAction"  # Not "action"
    },
    
    "Box": {
        "direction": ["row", "col"],  # Not "column"
        "align": ["start", "center", "end", "stretch"],
        "justify": ["start", "center", "end", "between", "around", "evenly"]
    },
    
    "Text": {
        "size": ["xs", "sm", "md", "lg", "xl"],
        "weight": ["normal", "medium", "semibold", "bold"],
        "color": ["primary", "secondary", "tertiary", "success", "warning", "error", "accent"],
        "family": ["default", "mono"],
        "style": ["normal", "italic"]
    },
    
    "Card": {
        "size": ["xs", "sm", "md", "lg", "xl"],
        "theme": ["light", "dark"],
        "background": "CSS background value (gradients, colors, etc.)",
        "padding": "number (padding in pixels)",
        "status": ["success", "warning", "error"],
        "collapsed": "boolean",
        "asForm": "boolean",
        "confirm": "object with label and action",
        "cancel": "object with label and action"
    },
    
    "Row": {
        "align": ["start", "center", "end", "stretch"],
        "justify": ["start", "center", "end", "between", "around", "evenly"]
    },
    
    "Col": {
        "align": ["start", "center", "end", "stretch"],
        "justify": ["start", "center", "end", "between", "around", "evenly"]
    },
    
    "Caption": {
        "size": ["xs", "sm", "md", "lg", "xl"],
        "weight": ["normal", "medium", "semibold", "bold"],
        "color": ["primary", "secondary", "tertiary", "success", "warning", "error", "accent", "muted"],
        "textAlign": ["left", "center", "right", "justify"]
    },
    
    "Image": {
        "src": "URL string (required)",
        "alt": "Alt text string",
        "fit": ["cover", "contain", "fill", "scale-down", "none"],
        "position": ["center", "top", "bottom", "left", "right"],
        "size": ["xs", "sm", "md", "lg", "xl"],
        "radius": "number or string",
        "width": "number",
        "height": "number"
    },
    
    "Spacer": {
        "minSize": "number (minimum space size)"
    },
    
    "DatePicker": {
        "name": "string (required)",
        "placeholder": "string",
        "variant": ["default", "outline", "ghost"],
        "size": ["xs", "sm", "md", "lg", "xl"],
        "defaultValue": "date string",
        "min": "date string",
        "max": "date string",
        "onChangeAction": "action object"
    },
    
    "Select": {
        "name": "string (required)",
        "options": "array of {label, value} objects (required)",
        "placeholder": "string",
        "variant": ["default", "outline", "ghost"],
        "size": ["xs", "sm", "md", "lg", "xl"],
        "defaultValue": "string",
        "onChangeAction": "action object"
    }
}

# Common mapping from user-friendly names to ChatKit values
PARAMETER_MAPPINGS = {
    "button_variant": {
        "primary": "solid",
        "secondary": "outline",
        "tertiary": "ghost",
        "default": "solid"
    },
    
    "box_direction": {
        "column": "col",
        "horizontal": "row",
        "vertical": "col",
        "default": "col"
    },
    
    "text_weight": {
        "regular": "normal",
        "strong": "bold",
        "default": "normal"
    }
}

def validate_and_map_parameter(widget_type: str, param_name: str, value: str) -> str:
    """
    Validate and map a parameter value to ensure it's valid for ChatKit.
    
    Args:
        widget_type: Type of widget (e.g., "Button", "Box")
        param_name: Name of the parameter (e.g., "variant", "direction")
        value: The value to validate/map
        
    Returns:
        Valid ChatKit parameter value
    """
    
    # Get validation rules for this widget type
    widget_rules = CHATKIT_VALIDATION_RULES.get(widget_type, {})
    valid_values = widget_rules.get(param_name, [])
    
    # If value is already valid, return it
    if value in valid_values:
        return value
    
    # Try to map the value
    mapping_key = f"{widget_type.lower()}_{param_name}"
    if mapping_key in PARAMETER_MAPPINGS:
        mapping = PARAMETER_MAPPINGS[mapping_key]
        if value in mapping:
            return mapping[value]
        # Return default if available
        if "default" in mapping:
            return mapping["default"]
    
    # Fallback to first valid value if available
    if valid_values:
        return valid_values[0]
    
    # Return original value as last resort
    return value

def get_validation_info():
    """Print validation information for debugging."""
    print("🔍 ChatKit Widget Validation Reference")
    print("=" * 50)
    
    for widget_type, rules in CHATKIT_VALIDATION_RULES.items():
        print(f"\n📦 {widget_type}:")
        for param, values in rules.items():
            if isinstance(values, list):
                print(f"   {param}: {', '.join(values)}")
            else:
                print(f"   {param}: {values}")
    
    print(f"\n🔄 Parameter Mappings:")
    for mapping_key, mapping in PARAMETER_MAPPINGS.items():
        print(f"   {mapping_key}:")
        for old_val, new_val in mapping.items():
            if old_val != "default":
                print(f"     '{old_val}' → '{new_val}'")

if __name__ == "__main__":
    get_validation_info()
    
    # Test some validations
    print(f"\n🧪 Validation Tests:")
    print(f"Button variant 'primary' → '{validate_and_map_parameter('Button', 'variant', 'primary')}'")
    print(f"Button variant 'secondary' → '{validate_and_map_parameter('Button', 'variant', 'secondary')}'")
    print(f"Box direction 'column' → '{validate_and_map_parameter('Box', 'direction', 'column')}'")
    print(f"Box direction 'horizontal' → '{validate_and_map_parameter('Box', 'direction', 'horizontal')}'")
