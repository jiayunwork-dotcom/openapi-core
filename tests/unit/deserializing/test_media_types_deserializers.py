from xml.etree.ElementTree import Element

import pytest
from jsonschema_path import SchemaPath

from openapi_core.casting.schemas import oas31_schema_casters_factory
from openapi_core.deserializing.exceptions import DeserializeError
from openapi_core.deserializing.media_types import (
    media_type_deserializers as default_media_type_deserializers,
)
from openapi_core.deserializing.media_types.datatypes import MultipartPart
from openapi_core.deserializing.media_types.exceptions import (
    MediaTypeDeserializeError,
)
from openapi_core.deserializing.media_types.factories import (
    MediaTypeDeserializersFactory,
)
from openapi_core.deserializing.media_types.util import multipart_mixed_loads
from openapi_core.validation.schemas import oas31_schema_validators_factory


class TestMediaTypeDeserializer:
    @pytest.fixture
    def spec(self):
        spec_dict = {}
        return SchemaPath.from_dict(spec_dict)

    @pytest.fixture
    def deserializer_factory(self, spec):
        def create_deserializer(
            mimetype,
            schema=None,
            schema_validator=None,
            encoding=None,
            prefix_encoding=None,
            item_encoding=None,
            parameters=None,
            media_type_deserializers=default_media_type_deserializers,
            extra_media_type_deserializers=None,
        ):

            return MediaTypeDeserializersFactory.from_schema_casters_factory(
                oas31_schema_casters_factory,
                media_type_deserializers=media_type_deserializers,
            ).create(
                spec,
                mimetype,
                schema=schema,
                schema_validator=schema_validator,
                parameters=parameters,
                encoding=encoding,
                prefix_encoding=prefix_encoding,
                item_encoding=item_encoding,
                extra_media_type_deserializers=extra_media_type_deserializers,
            )

        return create_deserializer

    @pytest.mark.parametrize(
        "mimetype,parameters,value,expected",
        [
            (
                "text/plain",
                {"charset": "iso-8859-2"},
                b"\xb1\xb6\xbc\xe6",
                "ąśźć",
            ),
            (
                "text/plain",
                {"charset": "utf-8"},
                b"\xc4\x85\xc5\x9b\xc5\xba\xc4\x87",
                "ąśźć",
            ),
            ("text/plain", {}, b"\xc4\x85\xc5\x9b\xc5\xba\xc4\x87", "ąśźć"),
            ("text/plain", {}, "somestr", "somestr"),
            ("text/html", {}, "somestr", "somestr"),
        ],
    )
    def test_plain_valid(
        self, deserializer_factory, mimetype, parameters, value, expected
    ):
        deserializer = deserializer_factory(mimetype, parameters=parameters)

        result = deserializer.deserialize(value)

        assert result == expected

    @pytest.mark.parametrize(
        "mimetype",
        [
            "application/json",
            "application/vnd.api+json",
        ],
    )
    def test_json_valid(self, deserializer_factory, mimetype):
        parameters = {"charset": "utf-8"}
        deserializer = deserializer_factory(mimetype, parameters=parameters)
        value = b'{"test": "test"}'

        result = deserializer.deserialize(value)

        assert type(result) is dict
        assert result == {"test": "test"}

    @pytest.mark.parametrize(
        "mimetype",
        [
            "application/json",
            "application/vnd.api+json",
        ],
    )
    def test_json_empty(self, deserializer_factory, mimetype):
        deserializer = deserializer_factory(mimetype)
        value = b""

        with pytest.raises(DeserializeError):
            deserializer.deserialize(value)

    @pytest.mark.parametrize(
        "mimetype",
        [
            "application/json",
            "application/vnd.api+json",
        ],
    )
    def test_json_empty_object(self, deserializer_factory, mimetype):
        deserializer = deserializer_factory(mimetype)
        value = b"{}"

        result = deserializer.deserialize(value)

        assert result == {}

    @pytest.mark.parametrize(
        "mimetype",
        [
            "application/xml",
            "application/xhtml+xml",
        ],
    )
    def test_xml_empty(self, deserializer_factory, mimetype):
        deserializer = deserializer_factory(mimetype)
        value = b""

        with pytest.raises(DeserializeError):
            deserializer.deserialize(value)

    @pytest.mark.parametrize(
        "mimetype",
        [
            "application/xml",
            "application/xhtml+xml",
        ],
    )
    def test_xml_default_charset_valid(self, deserializer_factory, mimetype):
        deserializer = deserializer_factory(mimetype)
        value = b"<obj>text</obj>"

        result = deserializer.deserialize(value)

        assert type(result) is Element

    @pytest.mark.parametrize(
        "mimetype",
        [
            "application/xml",
            "application/xhtml+xml",
        ],
    )
    def test_xml_valid(self, deserializer_factory, mimetype):
        parameters = {"charset": "utf-8"}
        deserializer = deserializer_factory(mimetype, parameters=parameters)
        value = b"<obj>text</obj>"

        result = deserializer.deserialize(value)

        assert type(result) is Element

    def test_octet_stream_empty(self, deserializer_factory):
        mimetype = "application/octet-stream"
        deserializer = deserializer_factory(mimetype)
        value = b""

        result = deserializer.deserialize(value)

        assert result == b""

    @pytest.mark.parametrize(
        "mimetype",
        [
            "image/gif",
            "image/png",
        ],
    )
    def test_octet_stream_implicit(self, deserializer_factory, mimetype):
        deserializer = deserializer_factory(mimetype)
        value = b""

        result = deserializer.deserialize(value)

        assert result == value

    def test_octet_stream_simple(self, deserializer_factory):
        mimetype = "application/octet-stream"
        schema_dict = {}
        schema = SchemaPath.from_dict(schema_dict)
        deserializer = deserializer_factory(mimetype, schema=schema)
        value = b"test"

        result = deserializer.deserialize(value)

        assert result == b"test"

    def test_urlencoded_form_empty(self, deserializer_factory):
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {}
        schema = SchemaPath.from_dict(schema_dict)
        deserializer = deserializer_factory(mimetype, schema=schema)
        value = b""

        result = deserializer.deserialize(value)

        assert result == {}

    def test_urlencoded_form_empty_value(self, deserializer_factory):
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        deserializer = deserializer_factory(mimetype, schema=schema)
        value = b"name="

        result = deserializer.deserialize(value)

        assert result == {"name": ""}

    def test_urlencoded_form_simple(self, deserializer_factory):
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        encoding_dict = {
            "name": {
                "style": "form",
            },
        }
        encoding = SchemaPath.from_dict(encoding_dict)
        deserializer = deserializer_factory(
            mimetype, schema=schema, encoding=encoding
        )
        value = b"name=foo+bar"

        result = deserializer.deserialize(value)

        assert result == {
            "name": "foo bar",
        }

    def test_urlencoded_complex_cast_error(self, deserializer_factory):
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "type": "object",
            "properties": {
                "prop": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        deserializer = deserializer_factory(mimetype, schema=schema)
        value = b"prop=a&prop=b&prop=c"

        with pytest.raises(DeserializeError):
            deserializer.deserialize(value)

    def test_urlencoded_complex(self, deserializer_factory):
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "type": "object",
            "properties": {
                "prop": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        deserializer = deserializer_factory(mimetype, schema=schema)
        value = b"prop=1&prop=2&prop=3"

        result = deserializer.deserialize(value)

        assert result == {
            "prop": [1, 2, 3],
        }

    def test_urlencoded_content_type(self, deserializer_factory):
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "type": "object",
            "properties": {
                "prop": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        encoding_dict = {
            "prop": {
                "contentType": "application/json",
            },
        }
        encoding = SchemaPath.from_dict(encoding_dict)
        deserializer = deserializer_factory(
            mimetype, schema=schema, encoding=encoding
        )
        value = b'prop=["a","b","c"]'

        result = deserializer.deserialize(value)

        assert result == {
            "prop": ["a", "b", "c"],
        }

    def test_urlencoded_deepobject(self, deserializer_factory):
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "type": "object",
            "properties": {
                "color": {
                    "type": "object",
                    "properties": {
                        "R": {
                            "type": "integer",
                        },
                        "G": {
                            "type": "integer",
                        },
                        "B": {
                            "type": "integer",
                        },
                    },
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        encoding_dict = {
            "color": {
                "style": "deepObject",
                "explode": True,
            },
        }
        encoding = SchemaPath.from_dict(encoding_dict)
        deserializer = deserializer_factory(
            mimetype, schema=schema, encoding=encoding
        )
        value = b"color[R]=100&color[G]=200&color[B]=150"

        result = deserializer.deserialize(value)

        assert result == {
            "color": {
                "R": 100,
                "G": 200,
                "B": 150,
            },
        }

    def test_multipart_form_empty(self, deserializer_factory):
        mimetype = "multipart/form-data"
        schema_dict = {}
        schema = SchemaPath.from_dict(schema_dict)
        deserializer = deserializer_factory(mimetype, schema=schema)
        value = b""

        result = deserializer.deserialize(value)

        assert result == {}

    def test_multipart_form_simple(self, deserializer_factory):
        mimetype = "multipart/form-data"
        schema_dict = {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "format": "binary",
                },
                "param2": {
                    "type": "string",
                    "format": "binary",
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        encoding_dict = {
            "param1": {
                "contentType": "application/octet-stream",
            },
        }
        encoding = SchemaPath.from_dict(encoding_dict)
        parameters = {
            "boundary": "===============2872712225071193122==",
        }
        deserializer = deserializer_factory(
            mimetype, schema=schema, parameters=parameters, encoding=encoding
        )
        value = (
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="param1"\n\ntest\n'
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="param2"\n\ntest2\n'
            b"--===============2872712225071193122==--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {
            "param1": b"test",
            "param2": b"test2",
        }

    def test_multipart_form_array(self, deserializer_factory):
        mimetype = "multipart/form-data"
        schema_dict = {
            "type": "object",
            "properties": {
                "file": {
                    "type": "array",
                    "items": {},
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        parameters = {
            "boundary": "===============2872712225071193122==",
        }
        deserializer = deserializer_factory(
            mimetype, schema=schema, parameters=parameters
        )
        value = (
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="file"\n\ntest\n'
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="file"\n\ntest2\n'
            b"--===============2872712225071193122==--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {
            "file": [b"test", b"test2"],
        }

    def test_custom_simple(self, deserializer_factory):
        deserialized = "x-custom"

        def custom_deserializer(value):
            return deserialized

        custom_mimetype = "application/custom"
        extra_media_type_deserializers = {
            custom_mimetype: custom_deserializer,
        }
        deserializer = deserializer_factory(
            custom_mimetype,
            extra_media_type_deserializers=extra_media_type_deserializers,
        )
        value = b"{}"

        result = deserializer.deserialize(
            value,
        )

        assert result == deserialized

    def test_urlencoded_oneof_integer_field(self, spec, deserializer_factory):
        """Test issue #932: oneOf with urlencoded should match schema with integer field"""
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "typeA": {"type": "string"},
                        "fieldA": {"type": "string"},
                    },
                    "required": ["typeA", "fieldA"],
                },
                {
                    "type": "object",
                    "properties": {
                        "typeB": {"type": "string"},
                        "fieldB": {"type": "integer"},
                    },
                    "required": ["typeB", "fieldB"],
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        deserializer = deserializer_factory(
            mimetype, schema=schema, schema_validator=schema_validator
        )
        # String "123" should be cast to integer 123 to match the second oneOf option
        value = b"typeB=test&fieldB=123"

        result = deserializer.deserialize(value)

        assert result == {
            "typeB": "test",
            "fieldB": 123,
        }

    def test_urlencoded_oneof_string_field(self, spec, deserializer_factory):
        """Test issue #932: oneOf with urlencoded should match schema with string fields"""
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "typeA": {"type": "string"},
                        "fieldA": {"type": "string"},
                    },
                    "required": ["typeA", "fieldA"],
                },
                {
                    "type": "object",
                    "properties": {
                        "typeB": {"type": "string"},
                        "fieldB": {"type": "integer"},
                    },
                    "required": ["typeB", "fieldB"],
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        deserializer = deserializer_factory(
            mimetype, schema=schema, schema_validator=schema_validator
        )
        value = b"typeA=test&fieldA=value"

        result = deserializer.deserialize(value)

        assert result == {
            "typeA": "test",
            "fieldA": "value",
        }

    def test_urlencoded_anyof_with_types(self, spec, deserializer_factory):
        """Test anyOf with urlencoded and type coercion"""
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "active": {"type": "boolean"},
                    },
                },
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        deserializer = deserializer_factory(
            mimetype, schema=schema, schema_validator=schema_validator
        )
        # Should match both schemas after type coercion
        value = b"count=42&active=true&name=test"

        result = deserializer.deserialize(value)

        assert result == {
            "count": 42,
            "active": True,
            "name": "test",
        }

    def test_urlencoded_oneof_boolean_field(self, spec, deserializer_factory):
        """Test oneOf with boolean field requiring type coercion"""
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "mode": {"type": "string"},
                    },
                    "required": ["enabled"],
                },
                {
                    "type": "object",
                    "properties": {
                        "disabled": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                    "required": ["disabled"],
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        deserializer = deserializer_factory(
            mimetype, schema=schema, schema_validator=schema_validator
        )
        # String "true" should be cast to boolean True
        value = b"enabled=true&mode=auto"

        result = deserializer.deserialize(value)

        assert result == {
            "enabled": True,
            "mode": "auto",
        }

    def test_urlencoded_form_with_array_default(self, deserializer_factory):
        mimetype = "application/x-www-form-urlencoded"
        schema_dict = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "default": [],
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        deserializer = deserializer_factory(mimetype, schema=schema)
        value = b""

        result = deserializer.deserialize(value)

        assert result == {"tags": []}

    @pytest.mark.xfail(
        reason=(
            "multipart composed-schema branch selection is not binary-aware"
        ),
        strict=True,
    )
    def test_multipart_oneof_binary_field(self, spec, deserializer_factory):
        mimetype = "multipart/form-data"
        schema_dict = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                    },
                    "required": ["label"],
                },
                {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string", "format": "binary"},
                    },
                    "required": ["file"],
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        parameters = {
            "boundary": "===============2872712225071193122==",
        }
        deserializer = deserializer_factory(
            mimetype,
            schema=schema,
            schema_validator=schema_validator,
            parameters=parameters,
        )
        value = (
            b"--===============2872712225071193122==\n"
            b"Content-Type: application/octet-stream\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="file"\n\n\xff\xfe\n'
            b"--===============2872712225071193122==--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {
            "file": b"\xff\xfe",
        }

    def test_multipart_oneof_string_field(self, spec, deserializer_factory):
        mimetype = "multipart/form-data"
        schema_dict = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "typeA": {"type": "string"},
                        "fieldA": {"type": "string"},
                    },
                    "required": ["typeA", "fieldA"],
                },
                {
                    "type": "object",
                    "properties": {
                        "typeB": {"type": "string"},
                        "fieldB": {"type": "string"},
                    },
                    "required": ["typeB", "fieldB"],
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        parameters = {
            "boundary": "===============2872712225071193122==",
        }
        deserializer = deserializer_factory(
            mimetype,
            schema=schema,
            schema_validator=schema_validator,
            parameters=parameters,
        )
        value = (
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="typeA"\n\ntest\n'
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="fieldA"\n\nvalue\n'
            b"--===============2872712225071193122==--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {
            "typeA": "test",
            "fieldA": "value",
        }

    @pytest.mark.xfail(
        reason=(
            "multipart composed-schema branch selection is not binary-aware"
        ),
        strict=True,
    )
    def test_multipart_anyof_binary_field(self, spec, deserializer_factory):
        mimetype = "multipart/form-data"
        schema_dict = {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string", "format": "binary"},
                    },
                },
                {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                    },
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        parameters = {
            "boundary": "===============2872712225071193122==",
        }
        deserializer = deserializer_factory(
            mimetype,
            schema=schema,
            schema_validator=schema_validator,
            parameters=parameters,
        )
        value = (
            b"--===============2872712225071193122==\n"
            b"Content-Type: application/octet-stream\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="file"\n\n\xff\xfe\n'
            b"--===============2872712225071193122==--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {
            "file": b"\xff\xfe",
        }

    def test_multipart_oneof_integer_field_with_form_encoding(
        self, spec, deserializer_factory
    ):
        mimetype = "multipart/form-data"
        schema_dict = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "typeA": {"type": "string"},
                        "fieldA": {"type": "string"},
                    },
                    "required": ["typeA", "fieldA"],
                },
                {
                    "type": "object",
                    "properties": {
                        "typeB": {"type": "string"},
                        "fieldB": {"type": "integer"},
                    },
                    "required": ["typeB", "fieldB"],
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        encoding = SchemaPath.from_dict(
            {
                "typeB": {"style": "form"},
                "fieldB": {"style": "form"},
            }
        )
        parameters = {
            "boundary": "===============2872712225071193122==",
        }
        deserializer = deserializer_factory(
            mimetype,
            schema=schema,
            schema_validator=schema_validator,
            encoding=encoding,
            parameters=parameters,
        )
        value = (
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="typeB"\n\ntest\n'
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="fieldB"\n\n123\n'
            b"--===============2872712225071193122==--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {
            "typeB": "test",
            "fieldB": 123,
        }

    def test_multipart_anyof_with_form_types(self, spec, deserializer_factory):
        mimetype = "multipart/form-data"
        schema_dict = {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "active": {"type": "boolean"},
                    },
                },
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            ]
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        encoding = SchemaPath.from_dict(
            {
                "count": {"style": "form"},
                "active": {"style": "form"},
                "name": {"style": "form"},
            }
        )
        parameters = {
            "boundary": "===============2872712225071193122==",
        }
        deserializer = deserializer_factory(
            mimetype,
            schema=schema,
            schema_validator=schema_validator,
            encoding=encoding,
            parameters=parameters,
        )
        value = (
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="count"\n\n42\n'
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="active"\n\ntrue\n'
            b"--===============2872712225071193122==\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="name"\n\ntest\n'
            b"--===============2872712225071193122==--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {
            "count": 42,
            "active": True,
            "name": "test",
        }

    def test_multipart_form_binary_with_form_encoding_stays_bytes(
        self, spec, deserializer_factory
    ):
        mimetype = "multipart/form-data"
        schema_dict = {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "format": "binary",
                },
            },
        }
        schema = SchemaPath.from_dict(schema_dict)
        schema_validator = oas31_schema_validators_factory.create(spec, schema)
        encoding = SchemaPath.from_dict(
            {
                "file": {"style": "form"},
            }
        )
        parameters = {
            "boundary": "===============2872712225071193122==",
        }
        deserializer = deserializer_factory(
            mimetype,
            schema=schema,
            schema_validator=schema_validator,
            encoding=encoding,
            parameters=parameters,
        )
        value = (
            b"--===============2872712225071193122==\n"
            b"Content-Type: application/octet-stream\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="file"\n\n\xff\xfe\n'
            b"--===============2872712225071193122==--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {
            "file": b"\xff\xfe",
        }


class TestMultipartMixedDeserializer:
    """OpenAPI 3.2 Encoding By Position for unnamed multipart media types."""

    @pytest.fixture
    def spec(self):
        return SchemaPath.from_dict({})

    @pytest.fixture
    def deserializer_factory(self, spec):
        def create_deserializer(
            mimetype,
            schema=None,
            prefix_encoding=None,
            item_encoding=None,
            parameters=None,
            media_type_deserializers=default_media_type_deserializers,
        ):
            return MediaTypeDeserializersFactory.from_schema_casters_factory(
                oas31_schema_casters_factory,
                media_type_deserializers=media_type_deserializers,
            ).create(
                spec,
                mimetype,
                schema=schema,
                parameters=parameters,
                prefix_encoding=prefix_encoding,
                item_encoding=item_encoding,
            )

        return create_deserializer

    def test_multipart_mixed_loads_keeps_order_headers_and_payloads(self):
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'{"author": "me"}\n'
            b"--BOUNDARY\n"
            b"Content-Type: text/plain; charset=utf-8\n\n"
            b"hello\n"
            b"--BOUNDARY--\n"
        )

        result = multipart_mixed_loads(value, boundary="BOUNDARY")

        assert result == [
            MultipartPart(
                content_type="application/json",
                parameters={},
                payload=b'{"author": "me"}',
            ),
            MultipartPart(
                content_type="text/plain",
                parameters={"charset": "utf-8"},
                payload=b"hello",
            ),
        ]

    def test_multipart_mixed_loads_empty_body(self):
        assert multipart_mixed_loads(b"", boundary="BOUNDARY") == []

    def test_prefix_encoding_decodes_parts_by_position(
        self, deserializer_factory
    ):
        schema = SchemaPath.from_dict(
            {
                "type": "array",
                "prefixItems": [
                    {"type": "object"},
                    {"type": "string"},
                ],
            }
        )
        prefix_encoding = SchemaPath.from_dict(
            [
                {},
                {"contentType": "text/plain"},
            ]
        )
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            parameters={"boundary": "BOUNDARY"},
        )
        # the second part declares a different Content-Type header,
        # the encoding object's contentType takes precedence
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'{"author": "me"}\n'
            b"--BOUNDARY\n"
            b"Content-Type: text/html\n\n"
            b"hello\n"
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        assert result == [{"author": "me"}, "hello"]

    def test_default_content_types_derived_from_schema(
        self, deserializer_factory
    ):
        # no encoding objects at all
        schema = SchemaPath.from_dict(
            {
                "type": "array",
                "prefixItems": [
                    {"type": "object"},
                    {"type": "string"},
                ],
            }
        )
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'{"id": 1}\n'
            b"--BOUNDARY\n"
            b"Content-Type: text/plain\n\n"
            b"plain text\n"
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        # object defaults to application/json, string defaults to text/plain
        assert result == [{"id": 1}, "plain text"]

    def test_encoding_object_without_content_type_uses_default(
        self, deserializer_factory
    ):
        schema = SchemaPath.from_dict(
            {
                "type": "array",
                "prefixItems": [
                    {"type": "object"},
                    {"type": "string"},
                ],
            }
        )
        prefix_encoding = SchemaPath.from_dict([{}, {}])
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'{"id": 1}\n'
            b"--BOUNDARY\n"
            b"Content-Type: text/plain\n\n"
            b"plain text\n"
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        assert result == [{"id": 1}, "plain text"]

    def test_item_encoding_applies_beyond_prefix_encoding(
        self, deserializer_factory
    ):
        schema = SchemaPath.from_dict(
            {
                "type": "array",
                "prefixItems": [{"type": "object"}],
                "items": {"type": "string"},
            }
        )
        prefix_encoding = SchemaPath.from_dict([{}])
        item_encoding = SchemaPath.from_dict({"contentType": "text/plain"})
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            item_encoding=item_encoding,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'{"id": 1}\n'
            b"--BOUNDARY\n"
            b"Content-Type: text/plain\n\n"
            b"first\n"
            b"--BOUNDARY\n"
            b"Content-Type: text/plain\n\n"
            b"second\n"
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        assert result == [{"id": 1}, "first", "second"]

    def test_items_schema_drives_default_content_type(
        self, deserializer_factory
    ):
        # no itemEncoding: trailing parts fall back to the items schema,
        # an object schema defaults to application/json
        schema = SchemaPath.from_dict(
            {
                "type": "array",
                "prefixItems": [{"type": "string"}],
                "items": {"type": "object"},
            }
        )
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: text/plain\n\n"
            b"label\n"
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'{"id": 2}\n'
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        assert result == ["label", {"id": 2}]

    def test_fewer_parts_than_prefix_encoding_is_not_an_error(
        self, deserializer_factory
    ):
        schema = SchemaPath.from_dict(
            {
                "type": "array",
                "prefixItems": [
                    {"type": "string"},
                    {"type": "string"},
                ],
            }
        )
        prefix_encoding = SchemaPath.from_dict(
            [
                {"contentType": "text/plain"},
                {"contentType": "text/plain"},
                {"contentType": "text/plain"},
            ]
        )
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: text/plain\n\n"
            b"only\n"
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        # the two unused encoding objects are simply ignored
        assert result == ["only"]

    def test_encoding_content_type_overrides_part_header(
        self, deserializer_factory
    ):
        schema = SchemaPath.from_dict(
            {"type": "array", "prefixItems": [{"type": "string"}]}
        )
        prefix_encoding = SchemaPath.from_dict([{"contentType": "text/plain"}])
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'{"id": 1}\n'
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        # decoded as text even though the part claims application/json
        assert result == ['{"id": 1}']

    def test_binary_part_stays_bytes(self, deserializer_factory):
        schema = SchemaPath.from_dict({"type": "array", "prefixItems": [{}]})
        prefix_encoding = SchemaPath.from_dict([{"contentType": "image/png"}])
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: image/png\n\n"
            b"\x89PNG binary\n"
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        assert result == [b"\x89PNG binary"]

    def test_nested_multipart_part(self, deserializer_factory):
        schema = SchemaPath.from_dict(
            {
                "type": "array",
                "prefixItems": [
                    {
                        "type": "array",
                        "prefixItems": [
                            {"type": "object"},
                            {"type": "string"},
                        ],
                        "items": {"type": "string"},
                    }
                ],
            }
        )
        prefix_encoding = SchemaPath.from_dict(
            [
                {
                    "contentType": "multipart/mixed",
                    "prefixEncoding": [
                        {"contentType": "application/json"},
                        {},
                    ],
                    "itemEncoding": {"contentType": "text/plain"},
                }
            ]
        )
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            parameters={"boundary": "OUTER"},
        )
        inner_body = (
            b"--INNER\n"
            b"Content-Type: application/json\n\n"
            b'{"k": "v"}\n'
            b"--INNER\n"
            b"Content-Type: text/html\n\n"
            b"plain text\n"
            b"--INNER\n"
            b"Content-Type: text/plain\n\n"
            b"trailing\n"
            b"--INNER--\n"
        )
        value = (
            b"--OUTER\n"
            b'Content-Type: multipart/mixed; boundary="INNER"\n\n'
            + inner_body
            + b"--OUTER--\n"
        )

        result = deserializer.deserialize(value)

        # nested boundary comes from the part's own Content-Type header
        assert result == [[{"k": "v"}, "plain text", "trailing"]]

    def test_nested_multipart_part_without_inner_encoding(
        self, deserializer_factory
    ):
        # nested encoding object without prefixEncoding/itemEncoding,
        # inner parts fall back to their position schema defaults
        schema = SchemaPath.from_dict(
            {
                "type": "array",
                "prefixItems": [
                    {
                        "type": "array",
                        "prefixItems": [
                            {"type": "object"},
                            {"type": "string"},
                        ],
                    }
                ],
            }
        )
        prefix_encoding = SchemaPath.from_dict(
            [{"contentType": "multipart/mixed"}]
        )
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            parameters={"boundary": "OUTER"},
        )
        inner_body = (
            b"--INNER\n"
            b"Content-Type: application/json\n\n"
            b'{"k": "v"}\n'
            b"--INNER\n"
            b"Content-Type: text/plain\n\n"
            b"plain text\n"
            b"--INNER--\n"
        )
        value = (
            b"--OUTER\n"
            b'Content-Type: multipart/mixed; boundary="INNER"\n\n'
            + inner_body
            + b"--OUTER--\n"
        )

        result = deserializer.deserialize(value)

        assert result == [[{"k": "v"}, "plain text"]]

    def test_undecodable_part_raises_media_type_deserialize_error(
        self, deserializer_factory
    ):
        schema = SchemaPath.from_dict(
            {"type": "array", "prefixItems": [{"type": "object"}]}
        )
        prefix_encoding = SchemaPath.from_dict(
            [{"contentType": "application/json"}]
        )
        deserializer = deserializer_factory(
            "multipart/mixed",
            schema=schema,
            prefix_encoding=prefix_encoding,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b"{not valid json\n"
            b"--BOUNDARY--\n"
        )

        with pytest.raises(MediaTypeDeserializeError):
            deserializer.deserialize(value)

    def test_form_data_with_array_schema_is_not_decoded_by_position(
        self, deserializer_factory
    ):
        # multipart/form-data stays on the named-property path
        schema = SchemaPath.from_dict({"type": "array"})
        deserializer = deserializer_factory(
            "multipart/form-data",
            schema=schema,
            parameters={"boundary": "BOUNDARY"},
        )
        value = (
            b"--BOUNDARY\n"
            b"Content-Type: text/plain\nMIME-Version: 1.0\n"
            b'Content-Disposition: form-data; name="field"\n\n'
            b"value\n"
            b"--BOUNDARY--\n"
        )

        result = deserializer.deserialize(value)

        assert result == {}
