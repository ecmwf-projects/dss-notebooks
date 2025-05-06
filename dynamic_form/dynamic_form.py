from typing import Optional, Dict, List
from IPython.display import display, clear_output
import ipywidgets as widgets


def build_collection_form(client, output: Optional[widgets.Output] = None) -> None:
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

        # Initial constraints
        initial_options = collection.apply_constraints({})

        # Filter out keys with no options
        initial_options = {
            k: v for k, v in initial_options.items() if v
        }

        # Create widget per constrained key
        widget_defs: Dict[str, widgets.SelectMultiple] = {
            key: widgets.SelectMultiple(
                description=key,
                options=values,
            )
            for key, values in initial_options.items()
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

    # React to collection change
    def on_collection_change(change):
        if change["name"] == "value" and change["new"] != change["old"]:
            build_form(change["new"])

    collection_widget.observe(on_collection_change, names="value")

    # Build initial form
    build_form(collection_widget.value)
    display(form_output)