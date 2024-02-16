#! /usr/bin/python3

"""
Module provides extensible generic factory.
"""

import logging
from threading import Lock
from typing import Any
from inspect import signature
from collections import OrderedDict

from gears.singleton_meta import SingletonController


class Factory(metaclass=SingletonController):
    """
    Factory class to create objects based on:
    - provided key
    - provided marker within the class attribute
    - provided args and kwargs
    You need to register your builders before using the factory.
    """
    _lock: Lock = Lock()
    _logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._builders: dict[str, type] = OrderedDict({})
        self._default: str = ""
        if logger:
            self._logger = logger

    def set_default(self, key: str) -> None:
        """ Set the default builder """
        excs: Exception | None = None
        with self._lock:
            if key not in self._builders.keys():
                excs = ValueError(f"Builder {key} not found")
            else:
                self._default = key
        if excs is not None:
            raise excs

    def get_default(self) -> str:
        """ Get the default builder """
        with self._lock:
            return self._default

    def register(
        self,
        key: str,
        builder: type,
    ) -> None:
        """ Register a class to be produced """
        make_default: bool = False
        exc: Exception | None = None
        with self._lock:
            if key in self._builders.keys():
                exc = KeyError(f"Builder {key} already registered")
            if self._default == "":
                make_default = True
            self._builders[key] = builder
        if exc:
            raise exc
        if make_default:
            self.set_default(key)

    def _generate_builder_sign_list(self, builders: dict[str, type]) -> dict[str, list[Any]]:
        """ Generates a list of signatures for builders """
        return {
            name: (list(signature(builder.__init__).parameters))
            for name, builder in builders.items()
        }

    def _select_builder_by_marker(
        self, marker: tuple[str, Any] | str, builders: dict[str, type]
    ) -> str | None:
        """ Selects the builder based on the marker provided """
        m_name: str
        if isinstance(marker, tuple):
            m_name, m_value = marker
        else:
            m_name = marker
        matched_builders_by_marker: list[str] = []

        for name, builder in builders.items():
            if hasattr(builder, m_name):
                matched_builders_by_marker.append(name)
                # pylint: disable=line-too-long
                if 'm_value' in locals() and getattr(builder, m_name) == m_value:  # type: ignore
                    return name
        if 'm_value' in locals():
            self._logger.warning(
                "Marker %s(%s) not found, using other mechanisms to select correct product",
                m_name, m_value  # type: ignore
            )
        if matched_builders_by_marker:
            return matched_builders_by_marker[0]
        return None

    def _select_builder_by_args(
        self, args: list[Any], kw_args: dict[str, Any], builders: dict[str, type] | None = None
    ) -> str | None:
        """ Selects the builder based on the signature of init """
        if not builders:
            builders = self._builders
        for name, signtr in self._generate_builder_sign_list(builders).items():
            # If args are more than the signature, we can't use this builder
            # If they are less it's ranked in the next check
            if (len(args) + len(kw_args)) > len(signtr):
                continue
            if all(key in signtr for key in kw_args.keys()):
                return name
        return None

    def _select_builder_by_base_class(self, base_class: type | None) -> dict[str, type]:
        """ Selects builders based on the base class """
        if not base_class:
            return self._builders
        return {
            name: builder
            for name, builder in self._builders.items()
            if issubclass(builder, base_class)
        }

    # pylint: disable=too-many-arguments
    def _choose_builder(
        self,
        args: list[Any],
        kw_args: dict[str, Any],
        key: str | None = None,
        marker: tuple[str, Any] | str | None = None,
        base_class: type | None = None
    ) -> str:
        """
        Chooses a builder, returns it's key.
        If base_class is supplied all following selections are done based
            on the builders that are subclass of the base
        We have the option to supply key, to directly choose the builder.
        If a marker is supplied, we will use it to choose the builder.
        If marker is a tuple we will return the first builder that has member, matching the first
            element of the tuple by name and second as value.
            If none matches, marker will be used as it was passed as a string.
        If marker is a string, we will return the first builder
            that has a member with the same name.
        If none of those cases are matched - the first builder who's args completelly
            match the supplied arg list is returned.
        If none of the above are matched, the first builder with most matched arguments is returned.
            Note: If some arg from provided is not matched - that builder will not be returned.
        If none of the above are matched, the default builder is returned.
        """

        def default_builder() -> str:
            """
            Return the default builder.
            Raise ValueError if default builder is not subclass of base class
            """
            if not base_class:
                return self._default
            if not issubclass(self._builders[self._default], base_class):
                # pylint: disable=line-too-long
                raise ValueError(
                    "Default builder is not subclass of base class while falling for default builder"
                )
            return self._default

        if not self._builders:
            raise ValueError("No builders registered")

        builders: dict[str, type] = self._select_builder_by_base_class(base_class)

        if not builders:
            raise ValueError(f"No builders found for base class {base_class}")

        # No hints, no info, no args/kwargs - give the default
        if not args and not kw_args and not key and not marker:
            return default_builder()

        # Give them what they asked for
        if key and key in builders:
            return key

        if key:
            self._logger.warning(
                "Builder %s not found, usigng other mechanisms to select correct product",
                key
            )
        # Select based on marker
        if marker:
            if name := self._select_builder_by_marker(marker, builders=builders):
                return name
            self._logger.warning(
                "Marker %s not found, using other mechanisms to select correct product",
                marker
            )

        if name := self._select_builder_by_args(args, kw_args):
            return name
        self._logger.warning(
            "No builder found for args %s, %s, using default builder",
            args, kw_args
        )
        return default_builder()

    def create(
        self,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        key: str | None = None,
        marker: tuple[str, Any] | str | None = None,
        base_class: type | None = None
    ) -> Any:
        """
        Create an object based on the supplied args.
        """
        if not args:
            args = []
        if not kwargs:
            kwargs = {}
        builder_key: str = self._choose_builder(args, kwargs, key, marker, base_class)
        builder: type = self._builders[builder_key]
        return builder(*args, **kwargs)
