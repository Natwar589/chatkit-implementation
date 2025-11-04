"""
ChatKit Widget JSON Renderer
Renders ChatKit widget JSON structures as actual ChatKit widgets
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Union
from dataclasses import dataclass

from chatkit.widgets import (
    Box,
    Card,
    Col,
    Row,
    Text,
    Title,
    WidgetComponent,
    WidgetRoot,
    Button,
    Divider,
    Caption,
    Image,
    Spacer,
    DatePicker,
    Select,
)

JsonWidgetSpec = Dict[str, Any]


@dataclass(frozen=True)
class ChatKitWidgetData:
    """Container for ChatKit widget JSON specification."""
    
    title: str
    widget_spec: JsonWidgetSpec
    key: str = "chatkit_widget"


def render_chatkit_widget_from_json(data: ChatKitWidgetData) -> WidgetRoot:
    """Render a ChatKit widget from JSON specification."""
    
    try:
        # Parse the widget specification
        widget = _parse_widget_component(data.widget_spec)
        
        # If it's already a Card, return it directly
        if isinstance(widget, Card):
            return widget
        
        # Otherwise, wrap it in a Card
        return Card(
            key=data.key,
            padding=0,
            children=[widget] if widget else [],
        )
        
    except Exception as e:
        # Fallback error widget
        return Card(
            key=data.key,
            padding=4,
            children=[
                Text(
                    value=f"Error rendering widget: {str(e)}",
                    color="error",
                    weight="medium"
                )
            ]
        )


def _parse_widget_component(spec: JsonWidgetSpec) -> WidgetComponent | None:
    """Parse a single widget component from JSON specification."""
    
    if not isinstance(spec, dict) or "type" not in spec:
        return None
    
    widget_type = spec["type"]
    
    # Handle different widget types
    if widget_type == "Card":
        return _parse_card(spec)
    elif widget_type == "Row":
        return _parse_row(spec)
    elif widget_type == "Col":
        return _parse_col(spec)
    elif widget_type == "Text":
        return _parse_text(spec)
    elif widget_type == "Title":
        return _parse_title(spec)
    elif widget_type == "Box":
        return _parse_box(spec)
    elif widget_type == "Button":
        return _parse_button(spec)
    elif widget_type == "Divider":
        return _parse_divider(spec)
    elif widget_type == "Caption":
        return _parse_caption(spec)
    elif widget_type == "Image":
        return _parse_image(spec)
    elif widget_type == "Spacer":
        return _parse_spacer(spec)
    elif widget_type == "DatePicker":
        return _parse_datepicker(spec)
    elif widget_type == "Select":
        return _parse_select(spec)
    else:
        # Unknown widget type - render as text
        return Text(
            value=f"Unknown widget type: {widget_type}",
            color="tertiary",
            size="sm"
        )


def _parse_card(spec: JsonWidgetSpec) -> Card:
    """Parse a Card widget."""
    
    children = []
    if "children" in spec:
        for child_spec in spec["children"]:
            child = _parse_widget_component(child_spec)
            if child:
                children.append(child)
    
    # Handle confirm/cancel buttons
    if "confirm" in spec or "cancel" in spec:
        button_row_children = []
        
        if "cancel" in spec:
            cancel_spec = spec["cancel"]
            button_kwargs = {
                "label": cancel_spec.get("label", "Cancel"),
                "variant": "outline",
                "size": "sm"
            }
            # Add action if specified
            if "action" in cancel_spec:
                button_kwargs["onClickAction"] = cancel_spec["action"]
            
            button_row_children.append(Button(**button_kwargs))
        
        if "confirm" in spec:
            confirm_spec = spec["confirm"]
            button_kwargs = {
                "label": confirm_spec.get("label", "Confirm"),
                "variant": "solid",
                "size": "sm"
            }
            # Add action if specified
            if "action" in confirm_spec:
                button_kwargs["onClickAction"] = confirm_spec["action"]
            
            button_row_children.append(Button(**button_kwargs))
        
        # Add button row to children
        if button_row_children:
            children.append(Row(
                justify="end",
                gap=2,
                children=button_row_children
            ))
    
    # Build card with all supported parameters
    card_kwargs = {
        "children": children,
        "size": spec.get("size", "md")
    }
    
    # Add optional parameters if specified
    if "background" in spec:
        card_kwargs["background"] = spec["background"]
    if "padding" in spec:
        card_kwargs["padding"] = spec["padding"]
    if "theme" in spec:
        card_kwargs["theme"] = spec["theme"]
    if "status" in spec:
        card_kwargs["status"] = spec["status"]
    if "collapsed" in spec:
        card_kwargs["collapsed"] = spec["collapsed"]
    if "asForm" in spec:
        card_kwargs["asForm"] = spec["asForm"]
    
    return Card(**card_kwargs)


def _parse_row(spec: JsonWidgetSpec) -> Row:
    """Parse a Row widget."""
    
    children = []
    if "children" in spec:
        for child_spec in spec["children"]:
            child = _parse_widget_component(child_spec)
            if child:
                children.append(child)
    
    return Row(
        gap=spec.get("gap", 2),
        align=spec.get("align", "center"),
        justify=spec.get("justify", "start"),
        children=children
    )


def _parse_col(spec: JsonWidgetSpec) -> Col:
    """Parse a Col widget."""
    
    children = []
    if "children" in spec:
        for child_spec in spec["children"]:
            child = _parse_widget_component(child_spec)
            if child:
                children.append(child)
    
    return Col(
        gap=spec.get("gap", 2),
        align=spec.get("align", "start"),
        children=children
    )


def _parse_text(spec: JsonWidgetSpec) -> Text:
    """Parse a Text widget."""
    
    # Handle editable text (show placeholder if no value)
    value = spec.get("value", "")
    if "editable" in spec and not value:
        editable = spec["editable"]
        value = editable.get("placeholder", "[Editable text]")
    
    # Valid ChatKit text colors
    VALID_COLORS = {
        "primary", "secondary", "tertiary", "success", "warning", "error", 
        "accent", "muted", "inherit"
    }
    
    # Map common color names to valid ChatKit colors
    color_mapping = {
        "default": "primary",
        "normal": "primary", 
        "text": "primary",
        "label": "primary",  # Changed from secondary to primary
        "disabled": "muted",
        "danger": "error",
        "info": "accent"
        # Removed "caption": "tertiary" mapping
    }
    
    # Get color from spec, default to primary for better visibility
    color = spec.get("color")
    
    if color is None:
        # No color specified - use primary for better visibility
        mapped_color = "primary"
    elif color not in VALID_COLORS:
        # Invalid color - try to map it, fallback to primary
        mapped_color = color_mapping.get(color, "primary")
    else:
        # Valid color - use as is
        mapped_color = color
    
    # Build text widget with explicit parameters
    text_kwargs = {
        "value": value,
        "size": spec.get("size", "md"),
        "weight": spec.get("weight", "normal"),
        "color": mapped_color
    }
    
    # Add optional parameters only if specified
    if "width" in spec:
        text_kwargs["width"] = spec["width"]
    if "minLines" in spec:
        text_kwargs["minLines"] = spec["minLines"]
    if "style" in spec and spec["style"] == "italic":
        text_kwargs["italic"] = True
    
    return Text(**text_kwargs)


def _parse_title(spec: JsonWidgetSpec) -> Title:
    """Parse a Title widget."""
    
    # Valid ChatKit colors (same as Text)
    VALID_COLORS = {
        "primary", "secondary", "tertiary", "success", "warning", "error", 
        "accent", "muted", "inherit"
    }
    
    color = spec.get("color", "primary")
    if color not in VALID_COLORS:
        color = "primary"  # fallback to primary
    
    return Title(
        value=spec.get("value", ""),
        size=spec.get("size", "lg"),
        weight=spec.get("weight", "semibold"),
        color=color
    )


def _parse_box(spec: JsonWidgetSpec) -> Box:
    """Parse a Box widget."""
    
    children = []
    if "children" in spec:
        for child_spec in spec["children"]:
            child = _parse_widget_component(child_spec)
            if child:
                children.append(child)
    
    # Valid ChatKit box directions
    VALID_DIRECTIONS = {"row", "col"}
    
    # Map common direction names to valid ChatKit directions
    direction_mapping = {
        "column": "col",
        "row": "row",
        "col": "col",
        "horizontal": "row",
        "vertical": "col"
    }
    
    direction = spec.get("direction", "col")
    mapped_direction = direction_mapping.get(direction, "col")
    
    # Ensure we're using a valid direction
    if mapped_direction not in VALID_DIRECTIONS:
        mapped_direction = "col"  # fallback to default
    
    return Box(
        padding=spec.get("padding", 0),
        gap=spec.get("gap", 0),
        direction=mapped_direction,
        align=spec.get("align", "start"),
        justify=spec.get("justify", "start"),
        background=spec.get("background"),
        radius=spec.get("radius"),
        children=children
    )


def _parse_button(spec: JsonWidgetSpec) -> Button:
    """Parse a Button widget."""
    
    # Valid ChatKit button variants
    VALID_VARIANTS = {"solid", "soft", "outline", "ghost"}
    
    # Map common variant names to valid ChatKit variants
    variant_mapping = {
        "primary": "solid",
        "secondary": "outline", 
        "tertiary": "ghost",
        "outline": "outline",
        "solid": "solid",
        "soft": "soft",
        "ghost": "ghost"
    }
    
    variant = spec.get("variant", "solid")
    mapped_variant = variant_mapping.get(variant, "solid")
    
    # Ensure we're using a valid variant
    if mapped_variant not in VALID_VARIANTS:
        mapped_variant = "solid"  # fallback to default
    
    button_kwargs = {
        "label": spec.get("label", "Button"),
        "variant": mapped_variant,
        "size": spec.get("size", "md")
    }
    
    # Add action if specified
    if "action" in spec:
        button_kwargs["onClickAction"] = spec["action"]
    
    return Button(**button_kwargs)


def _parse_divider(spec: JsonWidgetSpec) -> WidgetComponent:
    """Parse a Divider widget."""
    
    # ChatKit doesn't have a Divider widget, so we'll simulate it with a Box
    return Box(
        padding={"top": 2, "bottom": 2},
        children=[
            Box(
                height=1,
                background="surface-tertiary",
                width="100%"
            )
        ]
    )


def _parse_caption(spec: JsonWidgetSpec) -> Caption:
    """Parse a Caption widget."""
    
    # Valid ChatKit colors (same as Text)
    VALID_COLORS = {
        "primary", "secondary", "tertiary", "success", "warning", "error", 
        "accent", "muted", "inherit"
    }
    
    # Get color from spec, default to tertiary for captions (they are meant to be subtle)
    color = spec.get("color")
    
    if color is None:
        # No color specified - use tertiary for captions (subtle by design)
        mapped_color = "tertiary"
    elif color not in VALID_COLORS:
        # Invalid color - fallback to tertiary
        mapped_color = "tertiary"
    else:
        # Valid color - use as is
        mapped_color = color
    
    # Build caption widget
    caption_kwargs = {
        "value": spec.get("value", ""),
        "color": mapped_color,
        "size": spec.get("size", "sm"),
        "weight": spec.get("weight", "normal")
    }
    
    # Add optional parameters only if specified
    if "textAlign" in spec:
        caption_kwargs["textAlign"] = spec["textAlign"]
    if "truncate" in spec:
        caption_kwargs["truncate"] = spec["truncate"]
    if "maxLines" in spec:
        caption_kwargs["maxLines"] = spec["maxLines"]
    
    return Caption(**caption_kwargs)


def _parse_image(spec: JsonWidgetSpec) -> Image:
    """Parse an Image widget."""
    
    # Build image widget with required and optional parameters
    image_kwargs = {
        "src": spec.get("src", ""),  # Required: image source URL
        "alt": spec.get("alt", "Image")  # Alt text for accessibility
    }
    
    # Add optional parameters only if specified
    optional_params = [
        "fit", "position", "radius", "frame", "flush", 
        "height", "width", "size", "minHeight", "minWidth", "minSize",
        "maxHeight", "maxWidth", "maxSize", "margin", "background", 
        "aspectRatio", "flex"
    ]
    
    for param in optional_params:
        if param in spec:
            image_kwargs[param] = spec[param]
    
    return Image(**image_kwargs)


def _parse_spacer(spec: JsonWidgetSpec) -> Spacer:
    """Parse a Spacer widget."""
    
    spacer_kwargs = {}
    
    # Add optional parameters only if specified
    if "minSize" in spec:
        spacer_kwargs["minSize"] = spec["minSize"]
    
    return Spacer(**spacer_kwargs)


def _parse_datepicker(spec: JsonWidgetSpec) -> DatePicker:
    """Parse a DatePicker widget."""
    
    # Build datepicker widget
    datepicker_kwargs = {
        "name": spec.get("name", "date"),
        "placeholder": spec.get("placeholder", "Select date")
    }
    
    # Add optional parameters only if specified
    optional_params = [
        "onChangeAction", "defaultValue", "min", "max", "variant", 
        "size", "side", "align", "pill", "block", "clearable", "disabled"
    ]
    
    for param in optional_params:
        if param in spec:
            datepicker_kwargs[param] = spec[param]
    
    return DatePicker(**datepicker_kwargs)


def _parse_select(spec: JsonWidgetSpec) -> Select:
    """Parse a Select widget."""
    
    # Build select widget
    select_kwargs = {
        "name": spec.get("name", "select"),
        "options": spec.get("options", []),
        "placeholder": spec.get("placeholder", "Select option")
    }
    
    # Add optional parameters only if specified
    optional_params = [
        "onChangeAction", "defaultValue", "variant", "size", 
        "pill", "block", "clearable", "disabled"
    ]
    
    for param in optional_params:
        if param in spec:
            select_kwargs[param] = spec[param]
    
    return Select(**select_kwargs)


def chatkit_widget_copy_text(data: ChatKitWidgetData) -> str:
    """Generate human-readable fallback text for the ChatKit widget."""
    
    try:
        json_str = json.dumps(data.widget_spec, indent=2, ensure_ascii=False)
        return f"{data.title}\n\nWidget Specification:\n{json_str}"
    except Exception:
        return f"{data.title}\n\nChatKit widget (could not serialize specification)"


# Sample email widget data for testing
SAMPLE_EMAIL_WIDGET = {
    "type": "Card",
    "size": "lg",
    "confirm": {
        "action": {
            "type": "email.send"
        },
        "label": "Send email"
    },
    "cancel": {
        "action": {
            "type": "email.discard"
        },
        "label": "Discard"
    },
    "children": [
        {
            "type": "Row",
            "children": [
                {
                    "type": "Text",
                    "value": "FROM",
                    "width": 80,
                    "weight": "semibold",
                    "color": "tertiary",
                    "size": "xs"
                },
                {
                    "type": "Text",
                    "value": "zj@openai.com",
                    "color": "tertiary"
                }
            ]
        },
        {
            "type": "Divider",
            "flush": True
        },
        {
            "type": "Row",
            "children": [
                {
                    "type": "Text",
                    "value": "TO",
                    "width": 80,
                    "weight": "semibold",
                    "color": "tertiary",
                    "size": "xs"
                },
                {
                    "type": "Text",
                    "value": "weedon@openai.com",
                    "editable": {
                        "name": "email.to",
                        "required": True,
                        "placeholder": "name@example.com"
                    }
                }
            ]
        },
        {
            "type": "Divider",
            "flush": True
        },
        {
            "type": "Row",
            "children": [
                {
                    "type": "Text",
                    "value": "SUBJECT",
                    "width": 80,
                    "weight": "semibold",
                    "color": "tertiary",
                    "size": "xs"
                },
                {
                    "type": "Text",
                    "value": "ChatKit Roadmap",
                    "editable": {
                        "name": "email.subject",
                        "required": True,
                        "placeholder": "Email subject"
                    }
                }
            ]
        },
        {
            "type": "Divider",
            "flush": True
        },
        {
            "type": "Text",
            "value": "Hey David, \n\nHope you're doing well! Just wanted to check in and see if there are any updates on the ChatKit roadmap. We're excited to see what's coming next and how we can make the most of the upcoming features.\n\nEspecially curious to see how you support widgets!\n\nBest, Zach",
            "minLines": 9,
            "editable": {
                "name": "email.body",
                "required": True,
                "placeholder": "Write your message…"
            }
        }
    ]
}


def create_sample_email_widget() -> WidgetRoot:
    """Create the sample email widget for testing."""
    
    widget_data = ChatKitWidgetData(
        title="Email Composer",
        widget_spec=SAMPLE_EMAIL_WIDGET,
        key="sample_email"
    )
    
    return render_chatkit_widget_from_json(widget_data)
