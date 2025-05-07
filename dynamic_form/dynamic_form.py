from typing import Optional, Dict, List, Tuple, Any
from IPython.display import display, clear_output
import ipywidgets as widgets


def build_collection_form(
    client,
    output: Optional[widgets.Output] = None,
    dataset: Optional[str] = None,
    request: Optional[Dict[str, list[str]]] = None,
) -> None:
    """
    Display an interactive form in a Jupyter notebook that dynamically rebuilds 
    when the selected collection changes. Constraints are applied via the collection's 
    `apply_constraints` method.

    Parameters
    ----------
    client : Any
        A datapi.ApiClient instance or compatible object that provides:
            - get_collections().collection_ids
            - get_collection(collection_id), which returns an object with:
                - .title (str)
                - .apply_constraints(selection_dict) -> dict[str, list[str]]

    output : widgets.Output, optional
        A pre-allocated Output widget to display the form in.
        If None, a new Output widget is created.

    Returns
    -------
    None
        The form is displayed in the notebook cell output. This function does not return a value.
    """
    collections: List[str] = client.get_collections().collection_ids
    collections.sort()
    form_output: widgets.Output = output or widgets.Output()

    # Top-level dropdown for collection selection
    collection_widget = widgets.Dropdown(
        options=collections,
        description='Collection',
        value=collections[0],
    )
    
    def build_form(collection_id: str) -> None:
        """
        Build or rebuild the form based on the selected collection.

        Parameters
        ----------
        collection_id : str
            The ID of the selected collection.
        """
        form_output.clear_output()
        collection = client.get_collection(collection_id)
        selection: Dict[str, List[str]] = {}
        form_widgets = form_json_to_widgets_dict(collection.form)
        full_form_values = {
            k: w["values"] for k, w in form_widgets.items()
        }
        # Create widget per constrained key
        widget_defs: Dict[str, widgets.SelectMultiple] = {
            key: widgets.SelectMultiple(
                description=key,
                options=f_widget["values"],
            )
            for key, f_widget in form_widgets.items()
        }

        # Callback to update widgets on value change
        def on_change(change):
            for key in widget_defs:
                selection[key] = list(widget_defs[key].value)

            allowed_options = collection.apply_constraints({
                k: v for k, v in selection.items() if v
            })

            for key, values in allowed_options.items():
                if key in widget_defs:
                    widget = widget_defs[key]
                    # Update options and preserve valid selections
                    widget.options = values
                    widget.value = tuple([x for x in selection[key] if x in values])

        for widget in widget_defs.values():
            widget.observe(on_change, names='value')

        with form_output:
            display(widgets.VBox([
                widgets.HTML(f"<h3>{collection.title}</h3>"),
                collection_widget,
                *[widget_defs[key] for key in widget_defs]
            ]))

        return widget_defs

    # React to collection change
    def on_collection_change(change):
        if change["name"] == "value" and change["new"] != change["old"]:
            build_form(change["new"])

    collection_widget.observe(on_collection_change, names="value")

    # Build initial form
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
    Convert a form JSON to a dictionary of widgets.

    Parameters
    ----------
    form : list[dict[str, Any]]
        A list of dictionaries representing the form.

    Returns
    -------
    dict[str, Any]
        A dictionary mapping widget IDs to their values.
    """
    out_widgets = {}
    for widget in form:
        widget_name = widget.get("name", "")
        widget_type = widget.get("type", "")
        if widget_name in ignore_widget_names or widget_type in ignore_widget_types:
            continue
        if widget_name in out_widgets:
            log.warning(
                f"Duplicate widget name '{widget_name}' found in form JSON. "
                "Ignoring second occurrence."
            )
            continue
        out_widgets[widget_name] = {
            k: widget[k] for k in ["label", "type"] if k in widget
        }
        details = widget.get("details", {})
        # ignore groups for now
        if "groups" in details:
            labels = {}
            values = []
            for group in details["groups"]:
                labels.update({
                    k: v for k, v in group.get("labels", {}).items()
                })
                values += [v for v in group.get("values", []) if v not in values]
        else:
            labels = details.get("labels", {})
            values = details.get("values", [])
        out_widgets[widget_name]["labels"] = labels
        out_widgets[widget_name]["values"] = values
    return out_widgets


def widgets_to_request(
    collection_widget: widgets.Dropdown,
    widget_defs: Dict[str, widgets.SelectMultiple],
) -> Tuple[str, Dict[str, list[str]]]:
    """
    Convert the state of the widgets to a request dictionary.

    Parameters
    ----------
    widget_defs : dict
        A dictionary of widget definitions.

    Returns
    -------
    dict
        A dictionary representing the current state of the widgets.
    """
    collection_id = collection_widget.value
    request = {
        key: list(widget.value) for key, widget in widget_defs.items() if widget.value
    }
    for key, values in request.items():
        if len(values) == 1:
            request[key] = values[0]

    return collection_id, request
