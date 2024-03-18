#! /usr/vin/env python3

"""
This module provides somewhat naive, generic RBAC wrappers.
When used on classes, this module will transform
    their public methods in a non-obvious way. Be aware of that modiffication!
Althought it's intended to serve as a lazy way to enable RBAC on your code,
    it does impose some requirements about both classes and functions that
    are decorated with it.
It's not a drop-in solution, as it imposes requirements
    at least on the way your functions/methods are called.
Note, decorated classes will have two net attributes - __rbac__ and __rbac_default__.
Decorated functions and methods will have
    __rbac_permission__ and __rbac_pass_entity__ attributes added.
"""

import re
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Any, Callable
from threading import Lock
from gears.singleton_meta import SingletonController


RBAC_CLASS_VAR: str = "_rbac"
RBAC_CLASS_PASS_VAR: str = "_rback_pass"
RBAC_PERMISSION_KEY: str = "__rbac_permission__"
RBAC_PASS_ENTITY_KEY: str = "__rbac_pass_entity__"


class RBACError(Exception):
    """ Base class for RBAC errors """


class AccessDenied(RBACError):
    """ Raised when access is denied """


class RBACNotFound(RBACError):
    """ Raised when entity is not found """


class RBACMissingEntity(RBACError):
    """ Raised when entity is missing in the arg list """


class RBACEntityNotFound(RBACError):
    """ Raised when entity is not found """


class RBACPermissionNotFound(RBACError):
    """ Raised when permission is not found """


class RBACRoleNotFound(RBACError):
    """ Raised when role is not found """


class PermissionType(IntEnum):
    """
    Enum for the different types of permissions.
    Use the NONE permission level when assigning to callables if
        no permissions are required for a method.
    Don't assign NONE permissions to entities.
    All permission levels include the lower levels.
    """
    NONE = 0
    READ = 100
    WRITE = 200
    EXECUTE = 300


@dataclass(frozen=True)
class Permission:
    """
    Permission is a named permission with specified level.
    All permissions are unique accross the system and are identified by name and level.
    Permissions are directly attached to the various callables.
    Each callable can have only one permission attached.
    Permissions are attached to Role and can't be attached directly to entities.
    """
    name: str
    level: PermissionType

    def __str__(self) -> str:
        return f"{self.name}:{self.level.name}"

    @staticmethod
    def str_to_perm(s: str) -> "Permission":
        """ Converts a string to a Permission """
        pname, plevel = s.split(":")
        return Permission(name=pname, level=PermissionType[plevel])

    def __eq__(self, other) -> bool:
        return self.name == other.name and self.level >= other.level

    def __lt__(self, other) -> bool:
        return self.level < other.level

    def __gt__(self, other) -> bool:
        return self.level > other.level


@dataclass
class Role:
    """
    Role groups permissions.
    Roles are attachable to entities via RoleBinding.
    """

    name: str
    permissions: dict[str, Permission] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._lock: Lock = Lock()

    def attach_permission(self, permission: Permission) -> None:
        """ Adds a permission to the role """
        with self._lock:
            self.permissions[str(permission)] = permission

    def can_do(self, permission: Permission) -> bool:
        """ Returns True if the role has the permission """
        pname = str(permission)
        with self._lock:
            return pname in self.permissions and self.permissions[pname] == permission


@dataclass
class Entity:
    """ Entity is a named entity. Entity names are unique accross the system """
    name: str

    def __post_init__(self) -> None:
        self._lock: Lock = Lock()
        regex: str = r"^(user|group):[a-zA-Z0-9_]+$"
        if not re.match(regex, self.name):
            raise ValueError(
                f"Invalid entity name - {self.name}. Entity names are checked with {regex}"
            )


@dataclass
class User(Entity):
    """
    Users are entities that should be bound to a user, technical or personal,
    that have a single representation. If a user interacts with the app
    over multiple interfaces, for example web interface as well as from stdin,
    it's better to create a user for each interface and group them into a group.
    """
    name: str

    def __post_init__(self) -> None:
        self.name: str = f"user:{self.name}"
        super().__post_init__()


@dataclass
class Group(Entity):
    """ Group is an entity that groups multiple users """
    users: dict[str, User] = field(default_factory=dict)

    def __post_init__(self):
        self.name = f"group:{self.name}"
        super().__post_init__()

    def add_user(self, user: User) -> None:
        """ Naivelly adds users to the group """
        with self._lock:
            self.users[user.name] = user

    def get_users(self) -> list[User]:
        """ Returns a list of users in the group """
        with self._lock:
            return list(self.users.values())

    def get_user_names(self) -> list[str]:
        """ Returns a list of user names in the group """
        with self._lock:
            return list(self.users.keys())

    def has_entity(self, entity: Entity) -> bool:
        """ Returns True if the user is in the group """
        if isinstance(entity, User):
            with self._lock:
                return entity.name in self.users
        raise RBACEntityNotFound(f"Entity {entity} is not suported")


@dataclass
class RoleBinding:
    """ RoleBinding binds a role to a user """
    entity: Entity
    role: Role


class RBAC(metaclass=SingletonController):
    """
    RBAC is a singleton class that provides a generic RBAC interface.
    Class is threadsafe.
    Class does it's checks naivelly, it's up to the user to provide the correct data.
    """

    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._permissions: dict[str, Permission] = {}
        self._users: dict[str, User] = {}
        self._groups: dict[str, Group] = {}
        self._rbind_to_ent: dict[str, list[RoleBinding]] = {}
        self._rbind_to_role: dict[str, list[RoleBinding]] = {}
        self._lock: Lock = Lock()

    def _check_entity(self, entity: Entity | str) -> None:
        """ Checks if the entity exists """
        if isinstance(entity, Entity):
            entity = entity.name
        with self._lock:
            if entity not in self._users and entity not in self._groups:
                raise RBACEntityNotFound(f"Entity {entity} is not found")

    def _check_permission(self, permission: Permission | str) -> None:
        """ Checks if the permission exists """
        if isinstance(permission, Permission):
            permission = str(permission)
        with self._lock:
            if permission not in self._permissions:
                raise RBACPermissionNotFound(f"Permission {permission} is not found")

    def _check_role(self, role: Role | str) -> None:
        """ Checks if the role exists """
        if isinstance(role, Role):
            role = role.name
        with self._lock:
            if role not in self._roles:
                raise RBACRoleNotFound(f"Role {role} is not found")

    def add_user(self, uname: str) -> None:
        """ Adds a user to the system """
        with self._lock:
            self._users[uname] = User(name=uname)

    def add_group(self, gname: str) -> None:
        """ Adds a group to the system """
        with self._lock:
            self._groups[gname] = Group(name=gname)

    def get_entity(self, entity: Entity | str) -> Entity:
        """ Returns the entity """
        self._check_entity(entity)
        if isinstance(entity, str):
            with self._lock:
                return self._users[entity] if entity in self._users else self._groups[entity]
        return entity

    def add_user_to_group(self, user: str | User, group: str | Group) -> None:
        """ Adds a user to a group """
        self._check_entity(user)
        self._check_entity(group)
        with self._lock:
            user = user if isinstance(user, User) else self._users[user]
            group = group if isinstance(group, Group) else self._groups[group]
        group.add_user(user)

    def add_permission(self, pname: str, plevel: PermissionType) -> None:
        """ Adds a permission to the system """
        permission = Permission(name=pname, level=plevel)
        with self._lock:
            self._permissions[str(permission)] = permission

    def get_permission(self, permission: Permission | str) -> Permission:
        """ Returns the permission """
        self._check_permission(permission)
        if isinstance(permission, Permission):
            return permission
        with self._lock:
            return self._permissions[permission]

    def add_role(self, rname: str) -> None:
        """ Adds a role to the system """
        with self._lock:
            self._roles[rname] = Role(name=rname, permissions={})

    def get_role(self, role: Role | str) -> Role:
        """ Returns the role """
        self._check_role(role)
        if isinstance(role, Role):
            return role
        with self._lock:
            return self._roles[role]

    def add_permission_to_role(
        self, permission: Permission | str, role: Role | str
    ) -> None:
        """ Adds a permission to a role """
        permission = self.get_permission(permission)
        role = self.get_role(role)
        role.attach_permission(permission)

    def add_role_to_entity(self, role: Role | str, entity: Entity | str) -> None:
        """ Adds a role to an entity """
        entity = self.get_entity(entity)
        role = self.get_role(role)
        rbind = RoleBinding(entity=entity, role=role)

        with self._lock:
            if entity.name not in self._rbind_to_ent:
                self._rbind_to_ent[entity.name] = []
            self._rbind_to_ent[entity.name].append(rbind)
            if role.name not in self._rbind_to_role:
                self._rbind_to_role[role.name] = []
            self._rbind_to_role[role.name].append(rbind)

    def add_user_to_role(self, user: User | str, role: Role | str) -> None:
        """ Adds a user to a role """
        self.add_role_to_entity(role, user)

    def add_group_to_role(self, group: Group | str, role: Role | str) -> None:
        """ Adds a group to a role """
        self.add_role_to_entity(role, group)

    def _get_flattened_entities(self, entity: Entity) -> list[str]:
        """ Returns a list of entities that the entity is part of, including self """
        ent_reprs: list[str] = []

        if isinstance(entity, Group):
            ent_reprs = [entity.name]
        if isinstance(entity, User):
            with self._lock:
                ent_reprs = [gr.name for gr in self._groups.values() if gr.has_entity(entity)]
            ent_reprs.append(entity.name)

        return ent_reprs

    def get_entity_permissions(self, entity: Entity) -> list[Permission]:
        """ Returns a list of permissions for the entity """
        entity = self.get_entity(entity)
        permissions: list[Permission] = []
        ent_reprs: list[str] = self._get_flattened_entities(entity)

        for ent in ent_reprs:
            with self._lock:
                if ent in self._rbind_to_ent:
                    for rbind in self._rbind_to_ent[ent]:
                        permissions.extend(list(rbind.role.permissions.values()))
        return permissions

    def get_entity_roles(self, entity: Entity) -> list[Role]:
        """
        Returns a list of roles for the entity.
        If the entity is a group, it returns all the roles of the users in the group.
        """
        entity = self.get_entity(entity)
        roles: list[Role] = []
        ent_reprs: list[str] = self._get_flattened_entities(entity)

        for ent in ent_reprs:
            with self._lock:
                if ent in self._rbind_to_ent:
                    for rbind in self._rbind_to_ent[ent]:
                        roles.append(rbind.role)
        return roles

    def can_entity_do(self, entity: Entity | str, permission: Permission | str) -> bool:
        """
        Returns True if the entity has the permission to execute an action.
        If the permission level is NONE, returns True.
        """
        permission = self.get_permission(permission)
        if permission.level == PermissionType.NONE:
            return True
        return any(
            p == permission for p in self.get_entity_permissions(self.get_entity(entity))
        )


def rbac_set_permission(
    function: Callable, permission: Permission, populate_entity: bool | None = None
) -> Callable:
    """
    Sets the required permission to a function.
    If populate_entity is not None, RBAC will be instructed if it needs to pass down the entity.
    Note: populate_entity is added here to avoid having an endless list of decorators.
    """
    setattr(function, RBAC_PERMISSION_KEY, permission)
    if populate_entity is not None:
        setattr(function, RBAC_PASS_ENTITY_KEY, populate_entity)
    return function


def rbac_can_entity_do(
    fun: Callable, entity: Entity | str, permission: Permission | None = None
) -> bool:
    """ Check if entity has the permission to use this function """
    _rbac = RBAC()
    permission = permission or getattr(fun, RBAC_PERMISSION_KEY, None)
    if permission is None:
        raise RBACNotFound(f"Function {fun} has no RBAC permission set")
    if permission.level == PermissionType.NONE:
        return True
    entity = _rbac.get_entity(entity)  # type: ignore
    return _rbac.can_entity_do(entity, permission)  # type: ignore


def rbac_call_predicate(
    ent: Entity | str, fun: Callable, perm: Permission | None = None
) -> None:
    """ Predicate that checks if the entity has the permission to use this function """
    _rbac: RBAC = RBAC()  # type: ignore
    ent = _rbac.get_entity(ent)
    if not hasattr(fun, RBAC_PERMISSION_KEY) and perm is None:
        raise RBACNotFound(f"Function {fun} has no RBAC permission")
    if not rbac_can_entity_do(fun, ent, perm):
        raise AccessDenied(
            f"Entity {ent} can't perform {fun}{perm if perm else ''}",
            f"Entity {ent} permissions: {_rbac.get_entity_permissions(ent)}",
        )


def rbac_decorate_class(cls: type) -> type:
    """
    Decorator that sets the class permissions.
    It does so by looking for a dict variable, named `_rbac`.
    Variable has the type hint dict[str, Permission].
    Each public method in the class is decorated with the permission level from the dict.
    If a method is not in the dict, it gets the default permission (__rbac_default__).
    If there is no such attribute, it defaults to READ.
    If class variable `_rbac` is not found, it's generated and will lead to all-defaults.
    Function always generates and attaches an attribute __rbac_default__ to the class.
    """
    _rbac: dict[str, Permission] = getattr(cls, RBAC_CLASS_VAR, {})
    _rbac_pass: dict[str, bool] = getattr(cls, RBAC_CLASS_PASS_VAR, {})
    _rbac_default: Permission = _rbac.get(
        RBAC_PERMISSION_KEY, Permission(cls.__name__, PermissionType.READ)
    )
    _rbac_default_pass: bool = _rbac_pass.get(RBAC_PASS_ENTITY_KEY, True)
    _rbac[RBAC_PERMISSION_KEY] = _rbac_default
    _rbac_pass[RBAC_PASS_ENTITY_KEY] = _rbac_default_pass
    setattr(cls, RBAC_CLASS_VAR, _rbac)
    setattr(cls, RBAC_CLASS_PASS_VAR, _rbac_pass)

    # pylint: disable=too-few-public-methods
    class RABCWrapper(cls):
        """ Wrapper class that enforces RBAC """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for name, method in vars(cls).items():
                if callable(method) and not name.startswith("_"):
                    rbac_set_permission(
                        method,
                        _rbac.get(
                            name, _rbac[RBAC_PERMISSION_KEY]
                        ),
                        _rbac_pass.get(
                            name, _rbac_pass[RBAC_PASS_ENTITY_KEY]
                        )
                    )
                    setattr(self, name, rbac(method, obj=self))
    return RABCWrapper


def rbac_decorate_func(
    permission: Permission | str,
    populate_entity: bool = True
) -> Callable:
    """
    Decorator that configures the permission on a function.
    It will also optionally add instruction if entity should be passed
    down to the decorated function or removed from the arg list.
    """
    if isinstance(permission, str):
        permission = Permission.str_to_perm(permission)

    def rbac_decorate_func_wrapper(function: Callable, *args, **kwargs) -> Callable:
        return rbac_set_permission(function, permission, populate_entity)

    return rbac_decorate_func_wrapper


def rbac_execute(
    entity: Entity | str,
    fun: Callable,
    *args,
    obj: Any = None,
    **kwargs
) -> Any:
    """
    Executes the callable if the entity has the permission to do so,
    otherwise raises AccessDenied exception.
    If the callable has no rbac permission, raises RBACNotFound.
    """
    rbac_call_predicate(entity, fun)
    if hasattr(fun, RBAC_PASS_ENTITY_KEY) and getattr(fun, RBAC_PASS_ENTITY_KEY):
        kwargs["entity"] = entity
    if obj is not None:
        args = (obj,) + args
    return fun(*args, **kwargs)


def rbac(fun: Callable, obj: Any = None) -> Callable:
    """
    Decorator that checks if entity has the permission to use this function.
    If you want to use this decorator on function, you must use rbac_set_permissions first,
    as it relies on a dunder var __rbac_permission__.
    For class methods - use rbac_decorate_class.
    """
    def rbac_wrapper_fun(*args, **kwargs):
        if "entity" not in kwargs and len(args) == 0:
            raise RBACMissingEntity(
                f"Entity is missing in the arg list for {fun} ({args}, {kwargs})"
            )
        if "entity" in kwargs:
            entity = kwargs.pop("entity")
        else:
            entity = args[0]
            args = args[1:]
        return rbac_execute(entity, fun, *args, obj=obj, **kwargs)
    return rbac_wrapper_fun


def rbac_config(conf: dict[str, Any]) -> RBAC:
    """
    Configures the RBAC with a dict.
    The dict should have the following keys:
        - roles: list of roles
        - permissions: list of permissions
        - users: list of users
        - groups: list of groups
        - role_bindings: list of role bindings
        - user_to_group: list of user to group bindings
        - permissions_to_roles: list of permissions to roles bindings
    """
    _rbac: RBAC = RBAC()  # type: ignore
    for role in conf.get("roles", []):
        _rbac.add_role(role)
    for perm in conf.get("permissions", []):
        _rbac.add_permission(perm["name"], PermissionType[perm["level"]])
    for user in conf.get("users", []):
        _rbac.add_user(user)
    for group in conf.get("groups", []):
        _rbac.add_group(group)
    for rbind in conf.get("role_bindings", []):
        _rbac.add_role_to_entity(rbind["role"], rbind["entity"])
    for user_to_group in conf.get("user_to_group", []):
        _rbac.add_user_to_group(user_to_group["user"], user_to_group["group"])
    for perm_to_role in conf.get("permissions_to_roles", []):
        _rbac.add_permission_to_role(perm_to_role["permission"], perm_to_role["role"])
    return _rbac
