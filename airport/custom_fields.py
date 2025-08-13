from rest_framework import serializers


class RepresentationChoiceField(serializers.ChoiceField):
    """
    A universal field that extends the standard ChoiceField.

    Its main task is to correctly display related objects
    in the API response, converting them to a string representation.

    For input data, it works like a regular ChoiceField: accepts an ID
    and validates its presence in the `choices` list.
    """
    def to_representation(self, value):
        """
        Method is called when the response (output) is serialized.
        It takes a model object (for example, an Airport instance)
        and returns its text representation.
        Value - full object,
        str - __str__ method called on this object.
        """
        return str(value)


class OptimizedRelatedField(serializers.PrimaryKeyRelatedField):
    """
    A custom field that solves the duplicate query problem,
    created by BrowsableAPIRenderer.

    It uses the standard PrimaryKeyRelatedField logic for validation,
    but uses a ready-made,
    static choices list to build the drop-down list, which prevents repeated database queries.
    """
    def __init__(self, **kwargs):
        self.static_choices = kwargs.pop("choices", [])
        super().__init__(**kwargs)

    def get_choices(self, cutoff=None):
        """
        Override the method so that it always returns our static list,
        converted to the dictionary that the renderer expects.
        """
        return dict(self.static_choices)


class CustomPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Custom field for take dynamic queryset that taken from
    view -> (get_flight_queryset).
    Return select_related-queryset from view.
    """
    def get_queryset(self):
        view = self.context.get("view")
        if view and hasattr(view, "get_flight_queryset"):
            return view.get_flight_queryset()
        raise serializers.ValidationError(f"No queryset provided for field '{self.field_name}'.")


class BulkManyPrimaryKeyRelatedField(serializers.ManyRelatedField):
    """Custom field for bulk-query for all flight IDs"""
    def __init__(self, child_relation=None, *args, **kwargs):
        """
        Remove many to avoid TypeError and create CustomPrimaryKeyRelatedField
        to work with every element of list.
        """
        kwargs.pop("many", None)
        if child_relation is None:
            child_relation = CustomPrimaryKeyRelatedField(*args, **kwargs)
        super().__init__(child_relation=child_relation, *args, **kwargs)

    def run_child_validation(self, data):
        """
        Override the method to skip individual child validation (handled in bulk)
        return data without changes
        """
        return data

    def to_internal_value(self, data):
        """
        Method for list input validation.
        Take dynamic queryset from view, create unique ids list
        and make one bulk query for all PKs.
        Return objects in input order.
        """
        if isinstance(data, str) or not hasattr(data, "__iter__"):
            self.fail("not_a_list", input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail("empty")

        queryset = self.child_relation.get_queryset()
        if queryset is None:
            raise serializers.ValidationError(f"No queryset provided for field '{self.field_name}'.")

        pks = []
        for item in data:
            try:
                pk = int(item)
            except (TypeError, ValueError):
                self.fail('incorrect_type', data_type=type(item).__name__)
            pks.append(pk)

        unique_pks = set(pks)
        objs = list(queryset.filter(pk__in=unique_pks))

        obj_map = {obj.pk: obj for obj in objs}
        if len(obj_map) != len(unique_pks):
            missing = sorted(unique_pks - set(obj_map.keys()))
            raise serializers.ValidationError(
                f"Invalid pk '{missing}' - object does not exist."
            )
        self._validated_pks = pks

        return [obj_map[pk] for pk in pks]
