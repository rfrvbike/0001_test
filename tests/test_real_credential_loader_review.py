from __future__ import annotations

import inspect
import unittest

from x_auto_ops.credential_loader import CredentialBundle
from x_auto_ops.mock_transport import contains_sensitive_marker
from x_auto_ops.real_credential_loader import (
    CredentialNotFoundError,
    CredentialStorageAdapter,
    CredentialStorageError,
    CredentialValidationError,
    EnvCredentialAdapter,
    FileCredentialAdapter,
    OsCredentialAdapter,
    RealCredentialLoader,
    RealCredentialLoaderDisabledError,
    SecretManagerAdapter,
)


class RealCredentialLoaderReviewTests(unittest.TestCase):
    def test_real_credential_loader_remains_disabled(self) -> None:
        with self.assertRaises(RealCredentialLoaderDisabledError) as ctx:
            RealCredentialLoader().load()

        self.assertEqual(str(ctx.exception), "Real credential loader disabled")
        self.assertFalse(contains_sensitive_marker(str(ctx.exception)))

    def test_storage_adapter_interface_exists(self) -> None:
        self.assertTrue(hasattr(CredentialStorageAdapter, "load_credentials"))
        self.assertIn("load_credentials", CredentialStorageAdapter.__dict__)

    def test_adapter_skeletons_are_disabled_only(self) -> None:
        adapters = (
            EnvCredentialAdapter(),
            SecretManagerAdapter(),
            FileCredentialAdapter(),
            OsCredentialAdapter(),
        )

        for adapter in adapters:
            with self.subTest(adapter=adapter.__class__.__name__):
                with self.assertRaises(RealCredentialLoaderDisabledError) as ctx:
                    adapter.load_credentials()
                self.assertEqual(str(ctx.exception), "Real credential loader disabled")
                self.assertFalse(contains_sensitive_marker(str(ctx.exception)))

    def test_loader_can_accept_adapter_without_using_it(self) -> None:
        class TrackingAdapter:
            called = False

            def load_credentials(self) -> CredentialBundle:
                self.called = True
                raise AssertionError("adapter must not be called while loader is disabled")

        adapter = TrackingAdapter()
        loader = RealCredentialLoader(adapter=adapter)

        with self.assertRaises(RealCredentialLoaderDisabledError):
            loader.load()

        self.assertFalse(adapter.called)

    def test_error_classes_exist_for_future_mapping(self) -> None:
        self.assertTrue(issubclass(CredentialNotFoundError, RuntimeError))
        self.assertTrue(issubclass(CredentialStorageError, RuntimeError))
        self.assertTrue(issubclass(CredentialValidationError, RuntimeError))

    def test_no_real_credential_read_paths_exist_in_module_source(self) -> None:
        module = inspect.getmodule(RealCredentialLoader)
        source = inspect.getsource(module)

        forbidden = (
            "open(",
            "Path(",
            ".env",
            "os.environ",
            "getenv",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "HTTPConnection",
            "localStorage",
            "sessionStorage",
        )
        for term in forbidden:
            self.assertNotIn(term, source)

    def test_no_adapter_instantiates_credential_bundle(self) -> None:
        module = inspect.getmodule(RealCredentialLoader)
        source = inspect.getsource(module)

        self.assertNotIn("CredentialBundle(", source)


if __name__ == "__main__":
    unittest.main()
