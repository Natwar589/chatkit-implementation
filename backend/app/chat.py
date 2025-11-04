"""ChatKit server integration for the boilerplate backend."""

from __future__ import annotations

import inspect
import logging
from datetime import datetime
from typing import Annotated, Any, AsyncIterator, Final, Literal
from uuid import uuid4

from agents import Agent, RunContextWrapper, Runner, function_tool
from chatkit.agents import (
    AgentContext,
    ClientToolCall,
    ThreadItemConverter,
    stream_agent_response,
)
from chatkit.server import ChatKitServer, ThreadItemDoneEvent
from chatkit.types import (
    Attachment,
    ClientToolCallItem,
    HiddenContextItem,
    ThreadItem,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)
from openai.types.responses import ResponseInputContentParam
from pydantic import ConfigDict, Field

from .constants import INSTRUCTIONS, MODEL
from .facts import Fact, fact_store
from .memory_store import MemoryStore
from .sample_widget import render_weather_widget, weather_widget_copy_text
from .weather import (
    WeatherLookupError,
    retrieve_weather,
)
from .weather import (
    normalize_unit as normalize_temperature_unit,
)
from .json_widget import (
    JsonWidgetData,
    render_json_widget,
    json_widget_copy_text,
    create_sample_json_widget,
)
from .chatkit_widget_renderer import (
    ChatKitWidgetData,
    render_chatkit_widget_from_json,
    chatkit_widget_copy_text,
    create_sample_email_widget,
)

# If you want to check what's going on under the hood, set this to DEBUG
logging.basicConfig(level=logging.INFO)

SUPPORTED_COLOR_SCHEMES: Final[frozenset[str]] = frozenset({"light", "dark"})
CLIENT_THEME_TOOL_NAME: Final[str] = "switch_theme"


def _normalize_color_scheme(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in SUPPORTED_COLOR_SCHEMES:
        return normalized
    if "dark" in normalized:
        return "dark"
    if "light" in normalized:
        return "light"
    raise ValueError("Theme must be either 'light' or 'dark'.")


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _is_tool_completion_item(item: Any) -> bool:
    return isinstance(item, ClientToolCallItem)


class FactAgentContext(AgentContext):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    store: Annotated[MemoryStore, Field(exclude=True)]
    request_context: dict[str, Any]


async def _stream_saved_hidden(ctx: RunContextWrapper[FactAgentContext], fact: Fact) -> None:
    await ctx.context.stream(
        ThreadItemDoneEvent(
            item=HiddenContextItem(
                id=_gen_id("msg"),
                thread_id=ctx.context.thread.id,
                created_at=datetime.now(),
                content=(
                    f'<FACT_SAVED id="{fact.id}" threadId="{ctx.context.thread.id}">{fact.text}</FACT_SAVED>'
                ),
            ),
        )
    )


@function_tool(description_override="Record a fact shared by the user so it is saved immediately.")
async def save_fact(
    ctx: RunContextWrapper[FactAgentContext],
    fact: str,
) -> dict[str, str] | None:
    try:
        saved = await fact_store.create(text=fact)
        confirmed = await fact_store.mark_saved(saved.id)
        if confirmed is None:
            raise ValueError("Failed to save fact")
        await _stream_saved_hidden(ctx, confirmed)
        ctx.context.client_tool_call = ClientToolCall(
            name="record_fact",
            arguments={"fact_id": confirmed.id, "fact_text": confirmed.text},
        )
        print(f"FACT SAVED: {confirmed}")
        return {"fact_id": confirmed.id, "status": "saved"}
    except Exception:
        logging.exception("Failed to save fact")
        return None


@function_tool(
    description_override="Switch the chat interface between light and dark color schemes."
)
async def switch_theme(
    ctx: RunContextWrapper[FactAgentContext],
    theme: str,
) -> dict[str, str] | None:
    logging.debug(f"Switching theme to {theme}")
    try:
        requested = _normalize_color_scheme(theme)
        ctx.context.client_tool_call = ClientToolCall(
            name=CLIENT_THEME_TOOL_NAME,
            arguments={"theme": requested},
        )
        return {"theme": requested}
    except Exception:
        logging.exception("Failed to switch theme")
        return None


@function_tool(
    description_override="Look up the current weather and upcoming forecast for a location and render an interactive weather dashboard."
)
async def get_weather(
    ctx: RunContextWrapper[FactAgentContext],
    location: str,
    unit: Literal["celsius", "fahrenheit"] | str | None = None,
) -> dict[str, str | None]:
    print("[WeatherTool] tool invoked", {"location": location, "unit": unit})
    try:
        normalized_unit = normalize_temperature_unit(unit)
    except WeatherLookupError as exc:
        print("[WeatherTool] invalid unit", {"error": str(exc)})
        raise ValueError(str(exc)) from exc

    try:
        data = await retrieve_weather(location, normalized_unit)
    except WeatherLookupError as exc:
        print("[WeatherTool] lookup failed", {"error": str(exc)})
        raise ValueError(str(exc)) from exc

    print(
        "[WeatherTool] lookup succeeded",
        {
            "location": data.location,
            "temperature": data.temperature,
            "unit": data.temperature_unit,
        },
    )
    try:
        widget = render_weather_widget(data)
        copy_text = weather_widget_copy_text(data)
        payload: Any
        try:
            payload = widget.model_dump()
        except AttributeError:
            payload = widget
        print("[WeatherTool] widget payload", payload)
    except Exception as exc:  # noqa: BLE001
        print("[WeatherTool] widget build failed", {"error": str(exc)})
        raise ValueError("Weather data is currently unavailable for that location.") from exc

    print("[WeatherTool] streaming widget")
    try:
        await ctx.context.stream_widget(widget, copy_text=copy_text)
    except Exception as exc:  # noqa: BLE001
        print("[WeatherTool] widget stream failed", {"error": str(exc)})
        raise ValueError("Weather data is currently unavailable for that location.") from exc

    print("[WeatherTool] widget streamed")

    observed = data.observation_time.isoformat() if data.observation_time else None

    return {
        "location": data.location,
        "unit": normalized_unit,
        "observed_at": observed,
    }


@function_tool(
    description_override="Render arbitrary JSON data as an interactive widget for visualization."
)
async def render_json_data(
    ctx: RunContextWrapper[FactAgentContext],
    title: str,
    json_data: str,
    max_depth: int = 3,
    show_types: bool = True,
) -> dict[str, Any]:
    """
    Render arbitrary JSON data as an interactive widget.

    Args:
        title: Title for the widget
        json_data: JSON string to render
        max_depth: Maximum nesting depth to display (default: 3)
        show_types: Whether to show data types (default: true)
    """
    print("[JsonTool] tool invoked", {"title": title, "max_depth": max_depth})
    
    try:
        import json
        
        # Parse the JSON string
        parsed_data = json.loads(json_data)
        print("[JsonTool] JSON parsed successfully")
        
        # Create widget data
        widget_data = JsonWidgetData(
            title=title,
            data=parsed_data,
            key=f"json_{hash(json_data) % 10000}",
            max_depth=max_depth,
            show_types=show_types
        )
        
        # Render the widget
        widget = render_json_widget(widget_data)
        copy_text = json_widget_copy_text(widget_data)
        
        print("[JsonTool] widget created, streaming...")
        await ctx.context.stream_widget(widget, copy_text=copy_text)
        print("[JsonTool] widget streamed successfully")
        
        return {
            "title": title,
            "status": "success",
            "data_keys": list(parsed_data.keys()) if isinstance(parsed_data, dict) else None,
            "data_length": len(parsed_data) if isinstance(parsed_data, (dict, list)) else None
        }
        
    except json.JSONDecodeError as exc:
        print("[JsonTool] JSON decode error", {"error": str(exc)})
        raise ValueError(f"Invalid JSON: {str(exc)}") from exc
    except Exception as exc:
        print("[JsonTool] unexpected error", {"error": str(exc)})
        raise ValueError(f"Error rendering JSON: {str(exc)}") from exc


@function_tool(
    description_override="Show a sample JSON widget with demo data for testing purposes."
)
async def show_sample_json_widget(
    ctx: RunContextWrapper[FactAgentContext]
) -> dict[str, Any]:
    """Show a sample JSON widget with demo data."""
    print("[JsonTool] showing sample widget")
    
    try:
        widget = create_sample_json_widget()
        copy_text = "Sample JSON Widget\n\nThis is a demonstration of how JSON data can be rendered as an interactive widget."
        
        print("[JsonTool] sample widget created, streaming...")
        await ctx.context.stream_widget(widget, copy_text=copy_text)
        print("[JsonTool] sample widget streamed successfully")
        
        return {"status": "success", "message": "Sample JSON widget displayed"}
        
    except Exception as exc:
        print("[JsonTool] sample widget error", {"error": str(exc)})
        raise ValueError(f"Error showing sample: {str(exc)}") from exc


@function_tool(
    description_override="Render a ChatKit widget from JSON specification - creates actual ChatKit UI components."
)
async def render_chatkit_widget(
    ctx: RunContextWrapper[FactAgentContext],
    title: str,
    widget_json: str,
) -> dict[str, Any]:
    """
    Render a ChatKit widget from JSON specification.

    Args:
        title: Title for the widget
        widget_json: JSON string containing ChatKit widget specification
    """
    print("[ChatKitWidget] tool invoked", {"title": title})
    
    try:
        import json
        
        # Parse the widget JSON
        widget_spec = json.loads(widget_json)
        print("[ChatKitWidget] Widget JSON parsed successfully")
        
        # Create widget data
        widget_data = ChatKitWidgetData(
            title=title,
            widget_spec=widget_spec,
            key=f"chatkit_{hash(widget_json) % 10000}"
        )
        
        # Render the widget
        widget = render_chatkit_widget_from_json(widget_data)
        copy_text = chatkit_widget_copy_text(widget_data)
        
        print("[ChatKitWidget] widget created, streaming...")
        await ctx.context.stream_widget(widget, copy_text=copy_text)
        print("[ChatKitWidget] widget streamed successfully")
        
        return {
            "title": title,
            "status": "success",
            "widget_type": widget_spec.get("type", "unknown"),
            "has_children": "children" in widget_spec
        }
        
    except json.JSONDecodeError as exc:
        print("[ChatKitWidget] JSON decode error", {"error": str(exc)})
        raise ValueError(f"Invalid widget JSON: {str(exc)}") from exc
    except Exception as exc:
        print("[ChatKitWidget] unexpected error", {"error": str(exc)})
        raise ValueError(f"Error rendering ChatKit widget: {str(exc)}") from exc


@function_tool(
    description_override="Show the sample email widget from the ChatKit documentation."
)
async def show_sample_email_widget(
    ctx: RunContextWrapper[FactAgentContext]
) -> dict[str, Any]:
    """Show the sample email widget for testing ChatKit widget rendering."""
    print("[ChatKitWidget] showing sample email widget")
    
    try:
        widget = create_sample_email_widget()
        copy_text = "Sample Email Widget\n\nThis demonstrates how ChatKit widget JSON specifications are rendered as actual UI components."
        
        print("[ChatKitWidget] email widget created, streaming...")
        await ctx.context.stream_widget(widget, copy_text=copy_text)
        print("[ChatKitWidget] email widget streamed successfully")
        
        return {"status": "success", "message": "Sample email widget displayed"}
        
    except Exception as exc:
        print("[ChatKitWidget] email widget error", {"error": str(exc)})
        raise ValueError(f"Error showing email widget: {str(exc)}") from exc


@function_tool(
    description_override="Show a beautiful weather widget with forecast icons and temperatures."
)
async def show_weather_widget(
    ctx: RunContextWrapper[FactAgentContext]
) -> dict[str, Any]:
    """Show a weather widget with current conditions and 5-day forecast."""
    print("[ChatKitWidget] showing weather widget")
    
    try:
        # Create weather widget with theme and styling
        weather_widget_spec = {
            "type": "Card",
            "theme": "dark",
            "size": "sm",
            "padding": 8,
            "background": "linear-gradient(111deg, #1769C8 0%, #258AE3 56.92%, #31A3F8 100%)",
            "children": [
                {
                    "type": "Col",
                    "align": "center",
                    "gap": 3,
                    "children": [
                        {
                            "type": "Image",
                            "src": "https://cdn.openai.com/API/storybook/mixed-sun.png",
                            "alt": "Weather icon",
                            "width": 60,
                            "height": 60
                        },
                        {
                            "type": "Row",
                            "align": "center",
                            "gap": 2,
                            "children": [
                                {
                                    "type": "Title",
                                    "value": "47°",
                                    "size": "xl",
                                    "weight": "normal",
                                    "color": "muted"
                                },
                                {
                                    "type": "Title",
                                    "value": "69°",
                                    "size": "xl",
                                    "color": "primary",
                                    "weight": "normal"
                                }
                            ]
                        },
                        {
                            "type": "Caption",
                            "value": "San Francisco, CA",
                            "color": "primary"
                        },
                        {
                            "type": "Text",
                            "value": "Partly sunny skies accompanied by some clouds",
                            "textAlign": "center"
                        },
                        {
                            "type": "Row",
                            "gap": 6,
                            "children": [
                                {
                                    "type": "Col",
                                    "align": "center",
                                    "gap": 0,
                                    "children": [
                                        {
                                            "type": "Image",
                                            "src": "https://cdn.openai.com/API/storybook/mostly-sunny.png",
                                            "alt": "Mostly sunny",
                                            "width": 40,
                                            "height": 40
                                        },
                                        {
                                            "type": "Text",
                                            "value": "54°"
                                        }
                                    ]
                                },
                                {
                                    "type": "Col",
                                    "align": "center",
                                    "gap": 0,
                                    "children": [
                                        {
                                            "type": "Image",
                                            "src": "https://cdn.openai.com/API/storybook/rain.png",
                                            "alt": "Rain",
                                            "width": 40,
                                            "height": 40
                                        },
                                        {
                                            "type": "Text",
                                            "value": "54°"
                                        }
                                    ]
                                },
                                {
                                    "type": "Col",
                                    "align": "center",
                                    "gap": 0,
                                    "children": [
                                        {
                                            "type": "Image",
                                            "src": "https://cdn.openai.com/API/storybook/mixed-sun.png",
                                            "alt": "Mixed sun",
                                            "width": 40,
                                            "height": 40
                                        },
                                        {
                                            "type": "Text",
                                            "value": "54°"
                                        }
                                    ]
                                },
                                {
                                    "type": "Col",
                                    "align": "center",
                                    "gap": 0,
                                    "children": [
                                        {
                                            "type": "Image",
                                            "src": "https://cdn.openai.com/API/storybook/windy.png",
                                            "alt": "Windy",
                                            "width": 40,
                                            "height": 40
                                        },
                                        {
                                            "type": "Text",
                                            "value": "54°"
                                        }
                                    ]
                                },
                                {
                                    "type": "Col",
                                    "align": "center",
                                    "gap": 0,
                                    "children": [
                                        {
                                            "type": "Image",
                                            "src": "https://cdn.openai.com/API/storybook/mostly-sunny.png",
                                            "alt": "Mostly sunny",
                                            "width": 40,
                                            "height": 40
                                        },
                                        {
                                            "type": "Text",
                                            "value": "54°"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        widget_data = ChatKitWidgetData(
            title="Weather Forecast",
            widget_spec=weather_widget_spec,
            key="weather_forecast"
        )
        
        widget = render_chatkit_widget_from_json(widget_data)
        copy_text = "Weather Forecast Widget\n\nShows current temperature (47°-69°) in San Francisco with partly sunny conditions and 5-day forecast icons."
        
        print("[ChatKitWidget] weather widget created, streaming...")
        await ctx.context.stream_widget(widget, copy_text=copy_text)
        print("[ChatKitWidget] weather widget streamed successfully")
        
        return {"status": "success", "message": "Weather widget displayed"}
        
    except Exception as exc:
        print("[ChatKitWidget] weather widget error", {"error": str(exc)})
        raise ValueError(f"Error showing weather widget: {str(exc)}") from exc


@function_tool(
    description_override="Show a vivid color test widget to verify colors are working properly."
)
async def show_color_test_widget(
    ctx: RunContextWrapper[FactAgentContext]
) -> dict[str, Any]:
    """Show a widget with vivid colors to test color rendering."""
    print("[ChatKitWidget] showing color test widget")
    
    try:
        # Create vivid color test widget
        vivid_widget_spec = {
            "type": "Card",
            "size": "lg",
            "children": [
                {
                    "type": "Title",
                    "value": "🎨 Color Test Widget",
                    "color": "primary",
                    "size": "lg"
                },
                {
                    "type": "Text",
                    "value": "🔴 This should be ERROR RED",
                    "color": "error",
                    "weight": "bold",
                    "size": "lg"
                },
                {
                    "type": "Text", 
                    "value": "🟢 This should be SUCCESS GREEN",
                    "color": "success",
                    "weight": "bold",
                    "size": "lg"
                },
                {
                    "type": "Text",
                    "value": "🔵 This should be ACCENT BLUE", 
                    "color": "accent",
                    "weight": "bold",
                    "size": "lg"
                },
                {
                    "type": "Text",
                    "value": "⚫ This should be MUTED GRAY",
                    "color": "muted",
                    "weight": "medium",
                    "size": "md"
                },
                {
                    "type": "Row",
                    "gap": 4,
                    "children": [
                        {
                            "type": "Text",
                            "value": "PRIMARY",
                            "color": "primary",
                            "weight": "semibold"
                        },
                        {
                            "type": "Text",
                            "value": "SECONDARY", 
                            "color": "secondary",
                            "weight": "semibold"
                        },
                        {
                            "type": "Text",
                            "value": "TERTIARY",
                            "color": "tertiary", 
                            "weight": "semibold"
                        }
                    ]
                }
            ]
        }
        
        widget_data = ChatKitWidgetData(
            title="Vivid Color Test",
            widget_spec=vivid_widget_spec,
            key="vivid_colors"
        )
        
        widget = render_chatkit_widget_from_json(widget_data)
        copy_text = "Vivid Color Test Widget\n\nThis widget tests if colors are properly displayed in ChatKit. Each text should appear in a different color."
        
        print("[ChatKitWidget] color test widget created, streaming...")
        await ctx.context.stream_widget(widget, copy_text=copy_text)
        print("[ChatKitWidget] color test widget streamed successfully")
        
        return {"status": "success", "message": "Color test widget displayed"}
        
    except Exception as exc:
        print("[ChatKitWidget] color test widget error", {"error": str(exc)})
        raise ValueError(f"Error showing color test widget: {str(exc)}") from exc


def _user_message_text(item: UserMessageItem) -> str:
    parts: list[str] = []
    for part in item.content:
        text = getattr(part, "text", None)
        if text:
            parts.append(text)
    return " ".join(parts).strip()


class FactAssistantServer(ChatKitServer[dict[str, Any]]):
    """ChatKit server wired up with the fact-recording tool."""

    def __init__(self) -> None:
        self.store: MemoryStore = MemoryStore()
        super().__init__(self.store)
        tools = [save_fact, switch_theme, get_weather, render_json_data, show_sample_json_widget, render_chatkit_widget, show_sample_email_widget, show_weather_widget, show_color_test_widget]
        self.assistant = Agent[FactAgentContext](
            model=MODEL,
            name="ChatKit Guide",
            instructions=INSTRUCTIONS,
            tools=tools,  # type: ignore[arg-type]
        )
        self._thread_item_converter = self._init_thread_item_converter()

    async def respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        agent_context = FactAgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )

        target_item: ThreadItem | None = item
        if target_item is None:
            target_item = await self._latest_thread_item(thread, context)

        if target_item is None or _is_tool_completion_item(target_item):
            return

        agent_input = await self._to_agent_input(thread, target_item)
        if agent_input is None:
            return

        result = Runner.run_streamed(
            self.assistant,
            agent_input,
            context=agent_context,
        )

        async for event in stream_agent_response(agent_context, result):
            yield event
        return

    async def to_message_content(self, _input: Attachment) -> ResponseInputContentParam:
        raise RuntimeError("File attachments are not supported in this demo.")

    def _init_thread_item_converter(self) -> Any | None:
        converter_cls = ThreadItemConverter
        if converter_cls is None or not callable(converter_cls):
            return None

        attempts: tuple[dict[str, Any], ...] = (
            {"to_message_content": self.to_message_content},
            {"message_content_converter": self.to_message_content},
            {},
        )

        for kwargs in attempts:
            try:
                return converter_cls(**kwargs)
            except TypeError:
                continue
        return None

    async def _latest_thread_item(
        self, thread: ThreadMetadata, context: dict[str, Any]
    ) -> ThreadItem | None:
        try:
            items = await self.store.load_thread_items(thread.id, None, 1, "desc", context)
        except Exception:  # pragma: no cover - defensive
            return None

        return items.data[0] if getattr(items, "data", None) else None

    async def _to_agent_input(
        self,
        thread: ThreadMetadata,
        item: ThreadItem,
    ) -> Any | None:
        if _is_tool_completion_item(item):
            return None

        converter = getattr(self, "_thread_item_converter", None)
        if converter is not None:
            for attr in (
                "to_input_item",
                "convert",
                "convert_item",
                "convert_thread_item",
            ):
                method = getattr(converter, attr, None)
                if method is None:
                    continue
                call_args: list[Any] = [item]
                call_kwargs: dict[str, Any] = {}
                try:
                    signature = inspect.signature(method)
                except (TypeError, ValueError):
                    signature = None

                if signature is not None:
                    params = [
                        parameter
                        for parameter in signature.parameters.values()
                        if parameter.kind
                        not in (
                            inspect.Parameter.VAR_POSITIONAL,
                            inspect.Parameter.VAR_KEYWORD,
                        )
                    ]
                    if len(params) >= 2:
                        next_param = params[1]
                        if next_param.kind in (
                            inspect.Parameter.POSITIONAL_ONLY,
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        ):
                            call_args.append(thread)
                        else:
                            call_kwargs[next_param.name] = thread

                result = method(*call_args, **call_kwargs)
                if inspect.isawaitable(result):
                    return await result
                return result

        if isinstance(item, UserMessageItem):
            return _user_message_text(item)

        return None

    async def _add_hidden_item(
        self,
        thread: ThreadMetadata,
        context: dict[str, Any],
        content: str,
    ) -> None:
        await self.store.add_thread_item(
            thread.id,
            HiddenContextItem(
                id=_gen_id("msg"),
                thread_id=thread.id,
                created_at=datetime.now(),
                content=content,
            ),
            context,
        )


def create_chatkit_server() -> FactAssistantServer | None:
    """Return a configured ChatKit server instance if dependencies are available."""
    return FactAssistantServer()
