from typing import Optional, Dict, List, Tuple, Any
from IPython.display import display, clear_output
import ipywidgets as widgets
import json

def build_collection_form(
    client,
    output: Optional[widgets.Output] = None,
    dataset: Optional[str] = None,
    request: Optional[Dict[str, list[str]]] = None,
) -> Tuple[widgets.Dropdown, Dict[str, widgets.Widget]]:
    """
    Display an interactive form in a Jupyter notebook that dynamically updates based
    on the selected collection. The widgets are generated according to metadata that
    specifies their type (checkbox or radio) and layout (columns).

    Parameters
    ----------
    client : Any
        A client object with get_collections() and get_collection(collection_id) methods.
    output : widgets.Output, optional
        Optional output widget to display the form.
    dataset : str, optional
        Unused in current implementation.
    request : dict, optional
        Unused in current implementation.

    Returns
    -------
    Tuple[widgets.Dropdown, Dict[str, widgets.Widget]]
        The dropdown widget for collection selection and a dictionary of form widgets.
    """
    collections: List[str] = client.get_collections().collection_ids
    collections.sort()
    form_output: widgets.Output = output or widgets.Output()

    collection_widget = widgets.Dropdown(
        options=collections,
        description='Dataset',
        value=None,
    )
    
    widget_defs: Dict[str, widgets.Widget] = {}  # shared mutable dictionary

    selection_output = widgets.Output()

    def build_form(collection_id: str):
        """
        Build or rebuild the form widgets based on the selected collection's metadata.

        Parameters
        ----------
        collection_id : str
            Identifier of the selected collection.
        """
        form_output.clear_output()
        selection_output.clear_output()
        widget_defs.clear()
        if collection_id is None:
            with form_output:
                display(widgets.VBox([
                    widgets.HTML("<b>Select a dataset to begin</b>"),
                    collection_widget
                ]))
            return
        collection = client.get_collection(collection_id)
        form_widgets = form_json_to_widgets_dict(collection.form)
        
        selection: Dict[str, List[str]] = {}

        def update_selection_display():
            json_str = json.dumps(selection, indent=2)
            with selection_output:
                clear_output()
                display(widgets.HTML(f"<pre>{json_str}</pre>"))

        def on_change(change):
            for key, widget in widget_defs.items():
                selection[key] = widget._get_value() if hasattr(widget, "_get_value") else list(widget.value)

            allowed_options = collection.apply_constraints({
                k: v for k, v in selection.items() if v
            })

            for key, values in allowed_options.items():
                f_widget = form_widgets.get(key, {})
                labels = f_widget.get("labels", {})
                if key in widget_defs:
                    widget = widget_defs[key]
                    if hasattr(widget, 'children') and isinstance(widget.children[1], widgets.GridBox):
                        for tb in widget.children[1].children:
                            tb.layout.display = 'none'
                        for tb, opt in zip(widget.children[1].children, f_widget["values"]):
                            if opt in values:
                                tb.layout.display = ''
                    elif isinstance(widget, widgets.RadioButtons):
                        widget.options = [(labels.get(v, v), v) for v in values]
                        if widget.value not in values:
                            widget.value = None
                    elif isinstance(widget, widgets.SelectMultiple):
                        widget.options = values
                        widget.value = tuple([x for x in selection[key] if x in values])

            update_selection_display()

        for key, f_widget in form_widgets.items():
            widget_type = f_widget.get("type", "checkbox")
            options = f_widget["values"]
            labels = f_widget.get("labels", {})
            columns = f_widget.get("columns", 4)

            buttons = [
                widgets.ToggleButton(
                    value=False,
                    description=labels.get(opt, opt),
                    layout=widgets.Layout(width='auto'),
                    button_style=''
                ) for opt in options
            ]

            if widget_type == "checkbox":
                def get_value(tb_list=buttons, opts=options):
                    return [opt for opt, tb in zip(opts, tb_list) if tb.value]

                for tb in buttons:
                    tb.observe(on_change, names="value")

            elif widget_type == "radio":
                f_widget["title"] = f"{f_widget['title']} (select one)"
                def on_radio_click(change, opts=options, tb_list=buttons):
                    if change['new']:
                        for tb in tb_list:
                            if tb is not change['owner']:
                                tb.value = False
                        on_change(change)

                for tb in buttons:
                    tb.observe(lambda change, tb_list=buttons: on_radio_click(change, tb_list=tb_list), names='value')

                def get_value(tb_list=buttons, opts=options):
                    for opt, tb in zip(opts, tb_list):
                        if tb.value:
                            return [opt]
                    return []

            widget = widgets.VBox([
                widgets.HTML(f"<h3>{f_widget['title']}</h3>"),
                widgets.GridBox(
                    children=buttons,
                    layout=widgets.Layout(grid_template_columns=f"repeat({columns}, auto)")
                )
            ])

            default_values = f_widget.get("default", [])
            for tb, opt in zip(buttons, options):
                tb.value = opt in default_values

            widget._get_value = get_value
            widget_defs[key] = widget

        update_selection_display()
        
        with form_output:
            display(widgets.VBox([
                collection_widget,
                widgets.HTML(f"<h2>{collection.title}</h2>"),
                *[widget_defs[key] for key in widget_defs],
                widgets.HTML("<h3>Current Selection:</h3>"),
                selection_output
            ]))


    def on_collection_change(change):
        """React to changes in the selected collection and rebuild the form."""
        if change["name"] == "value" and change["new"] != change["old"]:
            build_form(change["new"])

    collection_widget.observe(on_collection_change, names="value")


    build_form(collection_widget.value)
    display(form_output)

    return collection_widget, widget_defs

def form_json_to_widgets_dict(
    form: list[dict[str, Any]],
    ignore_widget_names: List[str] = [
        "download_format",
        "data_format"
    ],
    ignore_widget_types: List[str] = [
        "ExclusiveGroupWidget",
        "FreeEditionWidget",
        "GeographicExtentWidget",
        "GeographicLocationWidget",
        "LicenceWidget",
    ]
) -> dict[str, Any]:
    """
    Convert a JSON-style form specification into a dictionary of widget metadata.

    Parameters
    ----------
    form : list of dict
        A list of widget metadata dictionaries.
    ignore_widget_names : list of str
        Widget names to exclude.
    ignore_widget_types : list of str
        Widget types to exclude.

    Returns
    -------
    dict[str, Any]
        A dictionary mapping widget names to metadata dicts.
    """
    out_widgets = {}
    widget_map = {
        "StringListWidget": "checkbox",
        "StringListArrayWidget": "checkbox",
        "StringChoiceWidget": "radio",
    }
    for widget in form:
        widget_name = widget.get("name", "")
        widget_type = widget.get("type", "")
        if widget_name in ignore_widget_names or widget_type in ignore_widget_types:
            continue
        if widget_name in out_widgets:
            continue
        out_widgets[widget_name] = {
            k: widget[k] for k in ["label", "type"] if k in widget
        }
        details = widget.get("details", {})
        if "groups" in details:
            labels = {}
            values = []
            columns = 1
            for group in details["groups"]:
                labels.update(group.get("labels", {}))
                values += [v for v in group.get("values", []) if v not in values]
                columns = max(columns, group.get("columns", 1))
        else:
            labels = details.get("labels", {})
            values = details.get("values", [])
            columns = details.get("columns", 1)
        out_widgets[widget_name]["labels"] = labels
        out_widgets[widget_name]["values"] = values
        out_widgets[widget_name]["title"] = widget.get("label", "")
        out_widgets[widget_name]["type"] = widget_map.get(widget_type, widget_type)
        out_widgets[widget_name]["columns"] = columns
        if "default" in details:
            out_widgets[widget_name]["default"] = details["default"]
    return out_widgets


def widgets_to_request(
    collection_widget: widgets.Dropdown,
    widget_defs: Dict[str, widgets.Widget],
) -> Tuple[str, Dict[str, list[str]]]:
    """
    Convert the state of widgets into a request dictionary.

    Parameters
    ----------
    collection_widget : widgets.Dropdown
        Dropdown widget to select collection.
    widget_defs : dict
        Dictionary of widgets with ._get_value() methods.

    Returns
    -------
    Tuple[str, dict]
        The collection ID and dictionary of selected values.
    """
    collection_id = collection_widget.value
    request = {
        key: widget._get_value()
        for key, widget in widget_defs.items()
        if hasattr(widget, "_get_value") and widget._get_value()
    }
    for key, values in request.items():
        if isinstance(values, list) and len(values) == 1:
            request[key] = values[0]

    return collection_id, request