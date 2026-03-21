from __future__ import annotations

import json
import logging
import random
from pathlib import Path

import gradio as gr
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.collection import WildcardTextFile
from dynamicprompts.wildcards.tree import WildcardTreeNode
from modules import script_callbacks

from sd_dynamic_prompts.element_ids import make_element_id

LOAD_FILE_ACTION = "load file"
LOAD_TREE_ACTION = "load tree"
MESSAGE_PROCESSING_ACTION = "message processing"

logger = logging.getLogger(__name__)

wildcard_manager: WildcardManager


def initialize(manager: WildcardManager):
    global wildcard_manager
    wildcard_manager = manager
    script_callbacks.on_ui_tabs(on_ui_tabs)


def _format_node_for_json(
    wildcard_manager: WildcardManager,
    node: WildcardTreeNode,
) -> list[dict]:
    collections = [
        {
            "name": node.qualify_name(coll),
            "wrappedName": wildcard_manager.to_wildcard(node.qualify_name(coll)),
            "children": [],
        }
        for coll in sorted(node.collections)
    ]
    child_items = [
        {"name": name, "children": _format_node_for_json(wildcard_manager, child_node)}
        for name, child_node in sorted(node.child_nodes.items())
    ]
    return [*collections, *child_items]


def on_ui_tabs():
    help_html = f"""
    <ol>
        <li>Place your wildcard .txt files in the <code>{wildcard_manager.path}</code> folder.</li>
        <li>Each .txt file should contain one option per line.</li>
        <li>Click on the files that appear in the tree to edit them.</li>
        <li>Use wildcards in your prompt with <code>__filename__</code> syntax (without the .txt extension).</li>
        <li>Subfolders are supported: <code>__subfolder/filename__</code></li>
    </ol>
    """

    with gr.Blocks() as wildcards_tab:
        with gr.Row():
            with gr.Column():
                gr.Textbox(
                    placeholder="Search in wildcard names...",
                    elem_id=make_element_id("wildcard-search"),
                    label="",
                )
                gr.HTML("Loading...", elem_id=make_element_id("wildcard-tree"))
                with gr.Accordion("Help", open=False):
                    gr.HTML(help_html)
                refresh_wildcards_button = gr.Button(
                    "Refresh wildcards",
                    elem_id=make_element_id("wildcard-load-tree-button"),
                )
            with gr.Column():
                gr.Textbox(
                    "",
                    elem_id=make_element_id("wildcard-file-name"),
                    interactive=False,
                    label="Wildcards file",
                )
                gr.Textbox(
                    "",
                    elem_id=make_element_id("wildcard-file-editor"),
                    lines=10,
                    interactive=True,
                    label="File editor",
                )
                save_button = gr.Button(
                    "Save wildcards",
                    scale=1,
                    elem_id=make_element_id("wildcard-save-button"),
                )

        # Hidden scratch textboxes and button for communication with JS bits.
        client_to_server_message_textbox = gr.Textbox(
            "",
            elem_id=make_element_id("wildcard-c2s-message-textbox"),
            visible=False,
        )
        server_to_client_message_textbox = gr.Textbox(
            "",
            elem_id=make_element_id("wildcard-s2c-message-textbox"),
            visible=False,
        )
        client_to_server_message_action_button = gr.Button(
            "Action",
            elem_id=make_element_id("wildcard-c2s-action-button"),
            visible=False,
        )

        # Handle the frontend sending a message
        client_to_server_message_action_button.click(
            handle_message,
            inputs=[client_to_server_message_textbox],
            outputs=[server_to_client_message_textbox],
        )

        refresh_wildcards_button.click(
            refresh_wildcards_callback,
            inputs=[],
            outputs=[server_to_client_message_textbox],
        )

        save_button.click(
            save_file_callback,
            _js="SDDP.onSaveFileClick",
            inputs=[client_to_server_message_textbox],
            outputs=[server_to_client_message_textbox],
        )

    return ((wildcards_tab, "Wildcards Manager", "sddp-wildcard-manager"),)


def create_payload(*, action: str, success: bool, **rest) -> str:
    return json.dumps(
        {
            "id": random.randint(0, 1000000),
            "action": action,
            "success": success,
            **rest,
        },
    )


def refresh_wildcards_callback():
    wildcard_manager.clear_cache()
    root = wildcard_manager.tree.root
    tree = _format_node_for_json(wildcard_manager, root)
    collection_count = len(list(root.walk_full_names()))
    return create_payload(
        action=LOAD_TREE_ACTION,
        success=True,
        tree=tree,
        collection_count=collection_count,
    )


def handle_message(event_str: str) -> str:
    try:
        event = json.loads(event_str)
        if event["action"] == LOAD_FILE_ACTION:
            return handle_load_wildcard(event)
        raise ValueError(f"Unknown event: {event}")
    except Exception as e:
        return create_payload(
            action=MESSAGE_PROCESSING_ACTION,
            success=False,
            message=f"Error processing message: {e}",
        )


def handle_load_wildcard(event: dict) -> str:
    name = event["name"]
    wf = wildcard_manager.get_file(name)
    if isinstance(wf, WildcardTextFile):
        contents = wf.read_text()
        can_edit = True
    else:
        values = "\n".join(str(val) for val in wf.get_values())
        contents = f"# File can't be edited\n{values}"
        can_edit = False

    return create_payload(
        action=LOAD_FILE_ACTION,
        success=True,
        contents=contents,
        can_edit=can_edit,
        name=name,
        wrapped_name=wildcard_manager.to_wildcard(name),
    )


def save_file_callback(event_str: str):
    try:
        event = json.loads(event_str)
        wf = wildcard_manager.get_file(event["wildcard"]["name"])
        if isinstance(wf, WildcardTextFile):
            wf.write_text(event["contents"].strip())
        else:
            raise Exception("Can't save non-text files")
        wildcard_manager.clear_cache()
        return handle_load_wildcard({"name": event["wildcard"]["name"]})
    except Exception as e:
        logger.exception(e)
