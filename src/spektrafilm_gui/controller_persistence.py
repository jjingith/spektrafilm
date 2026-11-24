from __future__ import annotations

import json
from typing import Any, Callable

from spektrafilm_gui.i18n import tr, trf


def save_current_as_default(
    *,
    viewer: Any,
    widgets: Any,
    collect_gui_state_fn: Callable[..., Any],
    save_default_gui_state_fn: Callable[[Any], None],
    set_status_fn: Callable[..., None],
    dialog_parent_fn: Callable[[Any], Any],
    message_box: Any,
) -> None:
    gui_state = collect_gui_state_fn(widgets=widgets)
    try:
        save_default_gui_state_fn(gui_state)
    except (OSError, ValueError) as exc:
        message_box.critical(
            dialog_parent_fn(viewer),
            tr('Save current as default'),
            trf('Failed to save default GUI state.\n\n{exc}', exc=exc),
        )
        return

    set_status_fn(viewer, tr('Saved current GUI state as the startup default'))


def save_current_state_to_file(
    *,
    viewer: Any,
    widgets: Any,
    file_dialog: Any,
    collect_gui_state_fn: Callable[..., Any],
    save_gui_state_to_path_fn: Callable[[Any, str], None],
    set_status_fn: Callable[..., None],
    dialog_parent_fn: Callable[[Any], Any],
    message_box: Any,
) -> None:
    filepath, _ = file_dialog.get_save_file_name(
        dialog_parent_fn(viewer),
        tr('Save GUI state'),
        'gui_state.json',
        tr('JSON (*.json)'),
    )
    if not filepath:
        return

    gui_state = collect_gui_state_fn(widgets=widgets)
    try:
        save_gui_state_to_path_fn(gui_state, filepath)
    except (OSError, ValueError) as exc:
        message_box.critical(
            dialog_parent_fn(viewer),
            tr('Save GUI state'),
            trf('Failed to save GUI state.\n\n{exc}', exc=exc),
        )
        return

    set_status_fn(viewer, trf('Saved GUI state to {filepath}', filepath=filepath))


def load_state_from_file(
    *,
    viewer: Any,
    widgets: Any,
    file_dialog: Any,
    load_gui_state_from_path_fn: Callable[[str], Any],
    apply_gui_state_fn: Callable[..., None],
    sync_canvas_background_fn: Callable[[], None],
    set_status_fn: Callable[..., None],
    dialog_parent_fn: Callable[[Any], Any],
    message_box: Any,
) -> None:
    filepath, _ = file_dialog.get_open_file_name(
        dialog_parent_fn(viewer),
        tr('Load GUI state'),
        '',
        tr('JSON (*.json)'),
    )
    if not filepath:
        return

    try:
        gui_state = load_gui_state_from_path_fn(filepath)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        message_box.critical(
            dialog_parent_fn(viewer),
            tr('Load GUI state'),
            trf('Failed to load GUI state.\n\n{exc}', exc=exc),
        )
        return

    apply_gui_state_fn(gui_state, widgets=widgets)
    sync_canvas_background_fn()
    set_status_fn(viewer, trf('Loaded GUI state from {filepath}', filepath=filepath))


def restore_factory_default(
    *,
    viewer: Any,
    widgets: Any,
    project_default_gui_state: Any,
    clear_saved_default_gui_state_fn: Callable[[], None],
    apply_gui_state_fn: Callable[..., None],
    sync_canvas_background_fn: Callable[[], None],
    set_status_fn: Callable[..., None],
    dialog_parent_fn: Callable[[Any], Any],
    message_box: Any,
) -> None:
    try:
        clear_saved_default_gui_state_fn()
    except OSError as exc:
        message_box.critical(
            dialog_parent_fn(viewer),
            tr('Restore factory default'),
            trf('Failed to clear the saved startup default.\n\n{exc}', exc=exc),
        )
        return

    apply_gui_state_fn(project_default_gui_state, widgets=widgets)
    sync_canvas_background_fn()
    set_status_fn(viewer, tr('Restored factory default GUI state'))