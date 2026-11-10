from base64 import b64encode

import pytest

from openapi_core import OpenAPI
from openapi_core import V30RequestValidator
from openapi_core.deserializing.media_types.exceptions import (
    MediaTypeDeserializeError,
)
from openapi_core.templating.media_types.exceptions import MediaTypeNotFound
from openapi_core.templating.paths.exceptions import OperationNotFound
from openapi_core.templating.paths.exceptions import PathNotFound
from openapi_core.templating.security.exceptions import SecurityNotFound
from openapi_core.testing import MockRequest
from openapi_core.validation.request.exceptions import InvalidRequestBody
from openapi_core.validation.request.exceptions import MissingRequiredParameter
from openapi_core.validation.request.exceptions import (
    RequestBodyValidationError,
)
from openapi_core.validation.request.exceptions import SecurityValidationError
from openapi_core.validation.schemas.exceptions import InvalidSchemaValue


class TestRequestValidator:
    host_url = "http://petstore.swagger.io"

    api_key = "12345"

    @property
    def api_key_encoded(self):
        api_key_bytes = self.api_key.encode("utf8")
        api_key_bytes_enc = b64encode(api_key_bytes)
        return str(api_key_bytes_enc, "utf8")

    @pytest.fixture(scope="session")
    def spec_dict(self, v30_petstore_content):
        return v30_petstore_content

    @pytest.fixture(scope="session")
    def spec(self, v30_petstore_spec):
        return v30_petstore_spec

    @pytest.fixture(scope="session")
    def request_validator(self, spec):
        return V30RequestValidator(spec)

    def test_request_server_error(self, request_validator):
        request = MockRequest("http://petstore.invalid.net/v1", "get", "/")

        with pytest.raises(PathNotFound):
            request_validator.validate(request)

    def test_path_not_found(self, request_validator):
        request = MockRequest(self.host_url, "get", "/v1")

        with pytest.raises(PathNotFound):
            request_validator.validate(request)

    def test_operation_not_found(self, request_validator):
        request = MockRequest(self.host_url, "patch", "/v1/pets")

        with pytest.raises(OperationNotFound):
            request_validator.validate(request)

    def test_missing_parameter(self, request_validator):
        request = MockRequest(self.host_url, "get", "/v1/pets")

        with pytest.raises(MissingRequiredParameter):
            with pytest.warns(DeprecationWarning):
                request_validator.validate(request)

    def test_omitted_required_deprecated_parameter(self):
        spec = OpenAPI.from_dict(
            {
                "openapi": "3.1.0",
                "info": {"version": "0", "title": "test"},
                "paths": {
                    "/test": {
                        "get": {
                            "parameters": [
                                {
                                    "name": "foo",
                                    "in": "query",
                                    "schema": {},
                                    "deprecated": True,
                                    "required": True,
                                },
                            ]
                        }
                    }
                },
            }
        )

        request = MockRequest("http://localhost", "get", "/test")

        with pytest.raises(MissingRequiredParameter):
            spec.validate_request(request)

    def test_omitted_optional_deprecated_parameter(self):
        spec = OpenAPI.from_dict(
            {
                "openapi": "3.1.0",
                "info": {"version": "0", "title": "test"},
                "paths": {
                    "/test": {
                        "get": {
                            "parameters": [
                                {
                                    "name": "foo",
                                    "in": "query",
                                    "schema": {},
                                    "deprecated": True,
                                },
                            ]
                        }
                    }
                },
            }
        )

        request = MockRequest("http://localhost", "get", "/test")
        result = spec.validate_request(request)

        assert result is None

    def test_security_not_found(self, request_validator):
        request = MockRequest(
            self.host_url,
            "get",
            "/v1/pets/1",
            path_pattern="/v1/pets/{petId}",
            view_args={"petId": "1"},
        )

        with pytest.raises(SecurityValidationError) as exc_info:
            request_validator.validate(request)

        assert exc_info.value.__cause__ == SecurityNotFound(
            [["petstore_auth"]]
        )

    def test_media_type_not_found(self, request_validator):
        data = b"csv,data"
        headers = {
            "api-key": self.api_key_encoded,
        }
        cookies = {
            "user": "123",
        }
        request = MockRequest(
            "https://development.gigantic-server.com",
            "post",
            "/v1/pets",
            path_pattern="/v1/pets",
            content_type="text/csv",
            data=data,
            headers=headers,
            cookies=cookies,
        )

        with pytest.raises(RequestBodyValidationError) as exc_info:
            request_validator.validate(request)

        assert exc_info.value.__cause__ == MediaTypeNotFound(
            mimetype="text/csv",
            availableMimetypes=[
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain",
            ],
        )

    def test_valid(self, request_validator):
        authorization = "Basic " + self.api_key_encoded
        headers = {
            "Authorization": authorization,
        }
        request = MockRequest(
            self.host_url,
            "get",
            "/v1/pets/1",
            path_pattern="/v1/pets/{petId}",
            view_args={"petId": "1"},
            headers=headers,
        )

        result = request_validator.validate(request)

        assert result is None

    def test_array_parameter_with_empty_default(self):
        spec = OpenAPI.from_dict(
            {
                "openapi": "3.1.0",
                "info": {"version": "0", "title": "test"},
                "paths": {
                    "/test": {
                        "get": {
                            "parameters": [
                                {
                                    "name": "foo",
                                    "in": "query",
                                    "schema": {"type": "array", "default": []},
                                }
                            ],
                            "responses": {"200": {"description": ""}},
                        },
                    }
                },
            }
        )
        request = MockRequest("http://localhost", "get", "/test")

        result = spec.validate_request(request)

        assert result is None

    def test_array_parameter_with_populated_default(self):
        spec = OpenAPI.from_dict(
            {
                "openapi": "3.1.0",
                "info": {"version": "0", "title": "test"},
                "paths": {
                    "/test": {
                        "get": {
                            "parameters": [
                                {
                                    "name": "foo",
                                    "in": "query",
                                    "schema": {
                                        "type": "array",
                                        "default": ["a", "b", "c"],
                                    },
                                }
                            ],
                            "responses": {"200": {"description": ""}},
                        },
                    }
                },
            }
        )
        request = MockRequest("http://localhost", "get", "/test")

        result = spec.validate_request(request)

        assert result is None


class TestMultipartMixedRequestValidator:
    """OpenAPI 3.2 Encoding By Position request body validation."""

    def _build_spec(self, media_type):
        return OpenAPI.from_dict(
            {
                "openapi": "3.2.0",
                "info": {"version": "0", "title": "test"},
                "paths": {
                    "/test": {
                        "post": {
                            "requestBody": {
                                "required": True,
                                "content": {"multipart/mixed": media_type},
                            },
                            "responses": {"200": {"description": ""}},
                        }
                    }
                },
            }
        )

    def test_multipart_mixed_valid(self):
        spec = self._build_spec(
            {
                "schema": {
                    "type": "array",
                    "prefixItems": [
                        {"type": "object"},
                        {"type": "string"},
                    ],
                    "items": {"type": "string"},
                },
                "prefixEncoding": [{}, {"contentType": "text/plain"}],
                "itemEncoding": {"contentType": "text/plain"},
            }
        )
        data = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'{"id": 1}\n'
            b"--BOUNDARY\n"
            b"Content-Type: text/html\n\n"
            b"hello\n"
            b"--BOUNDARY\n"
            b"Content-Type: text/plain\n\n"
            b"world\n"
            b"--BOUNDARY--\n"
        )
        request = MockRequest(
            "http://localhost",
            "post",
            "/test",
            content_type="multipart/mixed; boundary=BOUNDARY",
            data=data,
        )

        result = spec.validate_request(request)

        assert result is None

    def test_multipart_mixed_nested_valid(self):
        spec = self._build_spec(
            {
                "schema": {
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
                },
                "prefixEncoding": [
                    {
                        "contentType": "multipart/mixed",
                        "prefixEncoding": [
                            {"contentType": "application/json"},
                            {},
                        ],
                    }
                ],
            }
        )
        inner_body = (
            b"--INNER\n"
            b"Content-Type: application/json\n\n"
            b'{"k": "v"}\n'
            b"--INNER\n"
            b"Content-Type: text/plain\n\n"
            b"nested\n"
            b"--INNER--\n"
        )
        data = (
            b"--OUTER\n"
            b'Content-Type: multipart/mixed; boundary="INNER"\n\n'
            + inner_body
            + b"--OUTER--\n"
        )
        request = MockRequest(
            "http://localhost",
            "post",
            "/test",
            content_type='multipart/mixed; boundary="OUTER"',
            data=data,
        )

        result = spec.validate_request(request)

        assert result is None

    def test_multipart_mixed_deserialize_error(self):
        spec = self._build_spec(
            {
                "schema": {
                    "type": "array",
                    "prefixItems": [{"type": "object"}],
                },
                "prefixEncoding": [{"contentType": "application/json"}],
            }
        )
        data = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b"{not valid json\n"
            b"--BOUNDARY--\n"
        )
        request = MockRequest(
            "http://localhost",
            "post",
            "/test",
            content_type="multipart/mixed; boundary=BOUNDARY",
            data=data,
        )

        with pytest.raises(RequestBodyValidationError) as exc_info:
            spec.validate_request(request)

        assert isinstance(exc_info.value, RequestBodyValidationError)
        assert not isinstance(exc_info.value, InvalidRequestBody)
        assert isinstance(exc_info.value.__cause__, MediaTypeDeserializeError)

    def test_multipart_mixed_invalid_schema_value(self):
        spec = self._build_spec(
            {
                "schema": {
                    "type": "array",
                    "prefixItems": [{"type": "object"}],
                },
                "prefixEncoding": [{"contentType": "application/json"}],
            }
        )
        # valid JSON, but the decoded value does not match the array schema
        data = (
            b"--BOUNDARY\n"
            b"Content-Type: application/json\n\n"
            b'"just a string"\n'
            b"--BOUNDARY--\n"
        )
        request = MockRequest(
            "http://localhost",
            "post",
            "/test",
            content_type="multipart/mixed; boundary=BOUNDARY",
            data=data,
        )

        with pytest.raises(InvalidRequestBody) as exc_info:
            spec.validate_request(request)

        assert isinstance(exc_info.value.__cause__, InvalidSchemaValue)
