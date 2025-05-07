from typing import Optional, Dict, List, Tuple, Any
from IPython.display import display, clear_output
import ipywidgets as widgets

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
        description='Collection',
        value=collections[0],
    )

    def build_form(collection_id: str) -> Dict[str, widgets.Widget]:
        """
        Build or rebuild the form widgets based on the selected collection's metadata.

        Parameters
        ----------
        collection_id : str
            Identifier of the selected collection.

        Returns
        -------
        Dict[str, widgets.Widget]
            A dictionary mapping field names to their corresponding widgets.
        """
        form_output.clear_output()
        collection = client.get_collection(collection_id)
        selection: Dict[str, List[str]] = {}
        form_widgets = form_json_to_widgets_dict(collection.form)

        widget_defs: Dict[str, widgets.Widget] = {}

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

        for key, f_widget in form_widgets.items():
            widget_type = f_widget.get("type", "checkbox")
            options = f_widget["values"]
            labels = f_widget.get("labels", {})
            columns = f_widget.get("columns", 4)

            if widget_type == "checkbox":
                toggle_buttons = [
                    widgets.ToggleButton(
                        value=False,
                        description=labels.get(opt, opt),
                        layout=widgets.Layout(width='auto'),
                        button_style=''
                    ) for opt in options
                ]

                def get_toggle_value(tb_list=toggle_buttons, opts=options):
                    return [opt for opt, tb in zip(opts, tb_list) if tb.value]

                for tb in toggle_buttons:
                    tb.observe(on_change, names="value")

                widget = widgets.VBox([
                    widgets.HTML(f"<b>{f_widget['title']}</b>"),
                    widgets.GridBox(
                        children=toggle_buttons,
                        layout=widgets.Layout(grid_template_columns=f"repeat({columns}, auto)")
                    )
                ])
                widget._get_value = get_toggle_value
                widget_defs[key] = widget

            elif widget_type == "radio":
                radio_buttons = [
                    widgets.ToggleButton(
                        value=False,
                        description=labels.get(opt, opt),
                        layout=widgets.Layout(width='auto'),
                        button_style=''
                    ) for opt in options
                ]

                def on_radio_click(change, opts=options, tb_list=radio_buttons):
                    if change['new']:
                        for tb in tb_list:
                            if tb is not change['owner']:
                                tb.value = False
                        on_change(change)

                for tb in radio_buttons:
                    tb.observe(lambda change, tb_list=radio_buttons: on_radio_click(change, tb_list=tb_list), names='value')

                def get_radio_value(tb_list=radio_buttons, opts=options):
                    for opt, tb in zip(opts, tb_list):
                        if tb.value:
                            return [opt]
                    return []

                widget = widgets.VBox([
                    widgets.HTML(f"<b>{f_widget['title']}</b>"),
                    widgets.GridBox(
                        children=radio_buttons,
                        layout=widgets.Layout(grid_template_columns=f"repeat({columns}, auto)")
                    )
                ])
                widget._get_value = get_radio_value
                widget_defs[key] = widget

            else:
                widget = widgets.SelectMultiple(
                    options=options,
                    description=key
                )
                widget.observe(on_change, names="value")
                widget._get_value = lambda w=widget: list(w.value)
                widget_defs[key] = widget

        with form_output:
            display(widgets.VBox([
                widgets.HTML(f"<h3>{collection.title}</h3>"),
                collection_widget,
                *[widget_defs[key] for key in widget_defs]
            ]))

        return widget_defs

    def on_collection_change(change):
        """React to changes in the selected collection and rebuild the form."""
        if change["name"] == "value" and change["new"] != change["old"]:
            build_form(change["new"])

    collection_widget.observe(on_collection_change, names="value")

    widget_defs = build_form(collection_widget.value)
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
        key: widget._get_value() if hasattr(widget, "_get_value") else list(widget.value)
        for key, widget in widget_defs.items()
        if (hasattr(widget, "_get_value") and widget._get_value()) or widget.value
    }
    for key, values in request.items():
        if isinstance(values, list) and len(values) == 1:
            request[key] = values[0]

    return collection_id, request