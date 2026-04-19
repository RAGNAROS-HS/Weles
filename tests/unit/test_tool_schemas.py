import pytest

from weles.tools.history_tools import ADD_TO_HISTORY_SCHEMA
from weles.tools.profile_tools import SAVE_PROFILE_FIELD_SCHEMA, UPDATE_PREFERENCE_SCHEMA
from weles.tools.reddit import SEARCH_REDDIT_SCHEMA
from weles.tools.web import SEARCH_WEB_SCHEMA


@pytest.mark.parametrize(
    "schema, field",
    [
        (ADD_TO_HISTORY_SCHEMA, "item_name"),
        (ADD_TO_HISTORY_SCHEMA, "category"),
        (ADD_TO_HISTORY_SCHEMA, "notes"),
        (SAVE_PROFILE_FIELD_SCHEMA, "value"),
        (UPDATE_PREFERENCE_SCHEMA, "value"),
        (UPDATE_PREFERENCE_SCHEMA, "reason"),
        (SEARCH_REDDIT_SCHEMA, "query"),
        (SEARCH_WEB_SCHEMA, "query"),
    ],
)
def test_schema_has_max_length(schema, field):
    props = schema.get("properties", {})
    assert field in props, f"Field {field!r} not found in schema"
    assert "maxLength" in props[field], f"Field {field!r} missing maxLength"
    assert isinstance(props[field]["maxLength"], int)
    assert props[field]["maxLength"] > 0
