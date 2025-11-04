"""
JSON Widget Renderer for ChatKit
Renders arbitrary JSON data as interactive widgets
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
)

JsonValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]


@dataclass(frozen=True)
class JsonWidgetData:
    """Container for JSON data to be rendered as a widget."""
    
    title: str
    data: Dict[str, Any]
    key: str = "json_widget"
    max_depth: int = 3
    show_types: bool = True


def render_json_widget(data: JsonWidgetData) -> WidgetRoot:
    """Build a JSON data widget from arbitrary JSON data."""
    
    header = Box(
        padding=4,
        background="surface-secondary",
        children=[
            Row(
                justify="between",
                align="center",
                children=[
                    Title(
                        value=data.title,
                        size="lg",
                        weight="semibold",
                    ),
                    Text(
                        value="JSON Data",
                        size="xs",
                        color="tertiary",
                        weight="medium",
                    ),
                ],
            ),
        ],
    )
    
    content = _render_json_content(data.data, depth=0, max_depth=data.max_depth, show_types=data.show_types)
    
    body = Box(
        padding=4,
        gap=3,
        children=[content],
    )
    
    return Card(
        key=data.key,
        padding=0,
        children=[header, body],
    )


def _render_json_content(
    value: JsonValue, 
    depth: int = 0, 
    max_depth: int = 3, 
    show_types: bool = True,
    key_name: str = ""
) -> WidgetComponent:
    """Recursively render JSON content as widget components."""
    
    if depth > max_depth:
        return Text(
            value="... (max depth reached)",
            color="tertiary",
            size="sm",
            style="italic",
        )
    
    if isinstance(value, dict):
        return _render_object(value, depth, max_depth, show_types)
    elif isinstance(value, list):
        return _render_array(value, depth, max_depth, show_types)
    else:
        return _render_primitive(value, show_types, key_name)


def _render_object(
    obj: Dict[str, Any], 
    depth: int, 
    max_depth: int, 
    show_types: bool
) -> WidgetComponent:
    """Render a JSON object as a widget component."""
    
    if not obj:
        return Text(
            value="{}",
            color="tertiary",
            size="sm",
            family="mono",
        )
    
    items = []
    for key, value in obj.items():
        key_component = Text(
            value=f"{key}:",
            weight="medium",
            size="sm",
            color="secondary",
        )
        
        value_component = _render_json_content(
            value, 
            depth + 1, 
            max_depth, 
            show_types, 
            key_name=key
        )
        
        items.append(
            Row(
                gap=2,
                align="start",
                children=[
                    Box(
                        minWidth=100,
                        children=[key_component],
                    ),
                    Box(
                        flex="1",
                        children=[value_component],
                    ),
                ],
            )
        )
    
    return Box(
        padding=3,
        radius="md",
        background="surface-tertiary",
        children=[
            Col(
                gap=2,
                children=items,
            )
        ],
    )


def _render_array(
    arr: List[Any], 
    depth: int, 
    max_depth: int, 
    show_types: bool
) -> WidgetComponent:
    """Render a JSON array as a widget component."""
    
    if not arr:
        return Text(
            value="[]",
            color="tertiary",
            size="sm",
            family="mono",
        )
    
    items = []
    for i, value in enumerate(arr):
        index_component = Text(
            value=f"[{i}]",
            weight="medium",
            size="sm",
            color="tertiary",
            family="mono",
        )
        
        value_component = _render_json_content(
            value, 
            depth + 1, 
            max_depth, 
            show_types,
            key_name=f"item_{i}"
        )
        
        items.append(
            Row(
                gap=2,
                align="start",
                children=[
                    Box(
                        minWidth=50,
                        children=[index_component],
                    ),
                    Box(
                        flex="1",
                        children=[value_component],
                    ),
                ],
            )
        )
    
    return Box(
        padding=3,
        radius="md",
        background="surface-tertiary",
        children=[
            Col(
                gap=2,
                children=items,
            )
        ],
    )


def _render_primitive(
    value: JsonValue, 
    show_types: bool, 
    key_name: str = ""
) -> WidgetComponent:
    """Render a primitive JSON value as a widget component."""
    
    if value is None:
        display_value = "null"
        color = "tertiary"
        type_info = "null"
    elif isinstance(value, bool):
        display_value = "true" if value else "false"
        color = "accent" if value else "error"
        type_info = "boolean"
    elif isinstance(value, (int, float)):
        display_value = str(value)
        color = "success"
        type_info = "number"
    elif isinstance(value, str):
        # Truncate very long strings
        if len(value) > 100:
            display_value = f'"{value[:97]}..."'
        else:
            display_value = f'"{value}"'
        color = "primary"
        type_info = "string"
    else:
        display_value = str(value)
        color = "secondary"
        type_info = "unknown"
    
    components = [
        Text(
            value=display_value,
            color=color,
            size="sm",
            family="mono" if value is not None and not isinstance(value, str) else "default",
        )
    ]
    
    if show_types and type_info:
        components.append(
            Text(
                value=f"({type_info})",
                color="tertiary",
                size="xs",
                style="italic",
            )
        )
    
    return Row(
        gap=2,
        align="center",
        children=components,
    )


def json_widget_copy_text(data: JsonWidgetData) -> str:
    """Generate human-readable fallback text for the JSON widget."""
    
    try:
        json_str = json.dumps(data.data, indent=2, ensure_ascii=False)
        return f"{data.title}\n\n{json_str}"
    except Exception:
        return f"{data.title}\n\nJSON data (could not serialize for display)"


# Sample JSON data for testing
SAMPLE_JSON_DATA = {
    "user": {
        "id": 12345,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "active": True,
        "profile": {
            "age": 30,
            "location": "San Francisco, CA",
            "interests": ["programming", "hiking", "photography"],
            "settings": {
                "theme": "dark",
                "notifications": True,
                "privacy_level": "medium"
            }
        }
    },
    "metadata": {
        "created_at": "2024-01-15T10:30:00Z",
        "last_updated": "2024-11-01T12:00:00Z",
        "version": 2.1,
        "tags": ["premium", "verified"],
        "stats": {
            "login_count": 156,
            "posts_created": 23,
            "followers": 89
        }
    }
}


def create_sample_json_widget() -> WidgetRoot:
    """Create a sample JSON widget for testing."""
    
    widget_data = JsonWidgetData(
        title="User Profile Data",
        data=SAMPLE_JSON_DATA,
        key="sample_json",
        max_depth=4,
        show_types=True
    )
    
    return render_json_widget(widget_data)
