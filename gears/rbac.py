#! /usr/vin/env python3

"""
This module provides somewhat generic RBAC wrappers
"""

import re
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Any, Callable
from gears.singleton_meta import SingletonController


class RBACError(Exception):
    """ Base class for RBAC errors """


class AccessDenied(RBACError):
    """ Raised when access is denied """


class RBACNotFound(RBACError):
    """ Raised when entity is not found """


class PermissionType(IntEnum):
    """
    Enum for the different types of permissions.
    Use NONE for no permission required. Don't set it on entities.
    All permission levels include the lower levels.
    """
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3


@dataclass(frozen=True)
class Permission:
    """
    Permission is a named permission with a level.
    All permissions are unique accross the system and are identified by name.
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
    """ Role typically has a set of permissions """
    name: str
    permissions: dict[str, Permission] = field(default_factory=dict)

    def can_do(self, permission: Permission) -> bool:
        """ Returns True if the role has the permission """
        pname = str(permission)
        return pname in self.permissions and self.permissions[pname] == permission


@dataclass
class Entity:
    """ Entity is a named entity. Entity names are unique accross the system """
    name: str

    def __post_init__(self):
        regex = r"^(user|group):[a-zA-Z0-9_]+$"
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

    def __post_init__(self):
        self.name = f"user:{self.name}"
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
        self.users[user.name] = user

    def get_users(self) -> list[User]:
        """ Returns a list of users in the group """
        return list(self.users.values())

    def get_user_names(self) -> list[str]:
        """ Returns a list of user names in the group """
        return list(self.users.keys())

    def has_user(self, user: User | str) -> bool:
        """ Returns True if the user is in the group """
        uname = user.name if isinstance(user, User) else user
        return uname in self.users


@dataclass
class RoleBinding:
    """ RoleBinding binds a role to a user """
    entity: Entity
    role: Role


class RBAC(metaclass=SingletonController):
    """
    RBAC is a singleton class that provides a generic RBAC interface
    Class is threadsafe.
    Class does it's checks naivelly.
    It's up to the user to provide the correct data.
    """

    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._permissions: dict[str, Permission] = {}
        self._users: dict[str, User] = {}
        self._groups: dict[str, Group] = {}
        self._rbind_to_ent: dict[str, list[RoleBinding]] = {}
        self._rbind_to_role: dict[str, list[RoleBinding]] = {}

    def add_user(self, uname: str) -> None:
        """ Adds a user to the system """
        self._users[uname] = User(name=uname)

    def add_group(self, gname: str) -> None:
        """ Adds a group to the system """
        self._groups[gname] = Group(name=gname)

    def get_entity(self, entity: User | Group | str) -> User | Group:
        """ Returns the entity """
        if isinstance(entity, str):
            return self._users[entity] if entity in self._users else self._groups[entity]
        return entity

    def add_user_to_group(self, user: str | User, group: str | Group) -> None:
        """ Adds a user to a group """
        user = user if isinstance(user, User) else self._users[user]
        group = group if isinstance(group, Group) else self._groups[group]
        group.add_user(user)

    def add_permission(self, pname: str, plevel: PermissionType) -> None:
        """ Adds a permission to the system """
        permission = Permission(name=pname, level=plevel)
        self._permissions[str(permission)] = permission

    def get_permission(self, permission: Permission | str) -> Permission:
        """ Returns the permission """
        return permission if isinstance(permission, Permission) else self._permissions[permission]

    def add_role(self, rname: str) -> None:
        """ Adds a role to the system """
        self._roles[rname] = Role(name=rname, permissions={})

    def get_role(self, role: Role | str) -> Role:
        """ Returns the role """
        return role if isinstance(role, Role) else self._roles[role]

    def add_permission_to_role(
        self, permission: Permission | str, role: Role | str
    ) -> None:
        """ Adds a permission to a role """
        permission = self.get_permission(permission)
        role = self.get_role(role)
        role.permissions[str(permission)] = permission

    def add_role_to_entity(self, role: Role | str, entity: User | Group | str) -> None:
        """ Adds a role to an entity """
        entity = self.get_entity(entity)
        role = self.get_role(role)
        rbind = RoleBinding(entity=entity, role=role)

        if entity.name not in self._rbind_to_ent:
            self._rbind_to_ent[entity.name] = []
        self._rbind_to_ent[entity.name].append(rbind)
        if role.name not in self._rbind_to_role:
            self._rbind_to_role[role.name] = []

    def add_user_to_role(self, user: User | str, role: Role | str) -> None:
        """ Adds a user to a role """
        self.add_role_to_entity(role, user)

    def add_group_to_role(self, group: Group | str, role: Role | str) -> None:
        """ Adds a group to a role """
        self.add_role_to_entity(role, group)

    def get_entity_permissions(self, entity: User | Group) -> list[Permission]:
        """ Returns a list of permissions for the entity """
        entity = self.get_entity(entity)
        permissions = []
        ent_reprs = [] if isinstance(entity, Group) else [
            gr.name for gr in self._groups.values() if gr.has_user(entity)
        ]
        ent_reprs.append(entity.name)
        for ent in ent_reprs:
            if ent in self._rbind_to_ent:
                for rbind in self._rbind_to_ent[ent]:
                    permissions.extend(list(rbind.role.permissions.values()))
        return permissions

    def can_entity_do(self, entity: User | Group | str, permission: Permission | str) -> bool:
        """
        Returns True if the entity has the permission to execute an action.
        If the permission level is NONE, returns True.
        """
        permission = self.get_permission(permission)
        if permission.level == PermissionType.NONE:
            return True
        entity = self.get_entity(entity)
        permissions = self.get_entity_permissions(entity)
        return any(p == permission for p in permissions)


def rbac_set_permission(fun: Callable, permission: Permission) -> Callable:
    """Sets the permission on fun. """
    setattr(fun, "__rbac_permission__", permission)
    return fun


def rbac_can_entity_do(
    fun: Callable, entity: User | Group | str, permission: Permission | None = None
) -> bool:
    """ Check if the entity has the permission to use this function """
    _rbac = RBAC()
    entity = _rbac.get_entity(entity)  # type: ignore
    permission = permission or getattr(fun, "__rbac_permission__")
    return _rbac.can_entity_do(entity, permission)  # type: ignore


def rbac_call_predicate(
    ent: User | Group | str, fun: Callable, perm: Permission | None = None
) -> None:
    """ Predicate that checks if the entity has the permission to use this function """
    if not hasattr(fun, "__rbac_permission__") and perm is None:
        raise RBACNotFound(f"Function {fun} has no RBAC permission")
    if not rbac_can_entity_do(fun, ent, perm):
        raise AccessDenied(f"Entity {ent} can't perform {fun}{perm if perm else ''}")


def rbac_set_class_permissions(cls: type) -> type:
    """
    Decorator that sets the class permissions.
    It does so by looking for a dict variable, named `_rbac`.
    Variable has the type hint dict[str, Permission].
    Each method in the class is decorated with the permission level from the dict.
    If a method is not in the dict, it gets a permission,
    named after the class and the default level of def_level.
    If class variable `_rbac` is not found, it's generated with def_level.
    Function always generates and attaches a dunder var __rbac_default__ to the class.
    """
    dkey: str = "__rbac_default__"

    def _gen_rbac() -> dict[str, Permission]:
        tmp_rbac_def = getattr(cls, "_rbac", {})
        if dkey in tmp_rbac_def:
            raise ValueError(f"You can't have a permission named {dkey}")
        return tmp_rbac_def | {
            dkey: Permission(cls.__name__, getattr(cls, dkey, PermissionType.READ))
        }

    _rbac = _gen_rbac()
    setattr(cls, dkey, _rbac[dkey])

    # pylint: disable=too-few-public-methods
    class Wrapper(cls):
        """ Wrapper class that enforces RBAC """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for name, method in vars(cls).items():
                if callable(method) and not name.startswith("_"):
                    rbac_set_permission(method, _rbac.get(name, _rbac[dkey]))
                    setattr(self, name, rbac(method, obj=self))
    return Wrapper


def rbac_execute(
    entity: User | Group | str,
    fun: Callable,
    *args,
    obj: Any = None,
    pass_entity: bool = True,
    **kwargs
) -> Any:
    """
    Executes the callable if the entity has the permission to do so.
    If the callable has no rbac permission, raises RBACNotFound.
    If it does not, raises AccessDenied.
    """
    rbac_call_predicate(entity, fun)
    if pass_entity:
        kwargs["entity"] = entity
    if obj is not None:
        args = (obj,) + args
    return fun(*args, **kwargs)


def rbac(fun: Callable, obj: Any = None, pass_entity: bool = True) -> Callable:
    """
    Decorator that checks if the entity has the permission to use this function.
    If you want to use this decorator on function, you must use rbac_set_permissions first,
    as it relies on a dunder var __rbac_permission__.
    For class methods you can just use rbac_set_class_permissions.
    """
    def wrapper(*args, **kwargs):
        if "entity" in kwargs:
            entity = kwargs.pop("entity")
        else:
            entity = args[0]
            args = args[1:]
        return rbac_execute(entity, fun, *args, obj=obj, pass_entity=pass_entity, **kwargs)
    return wrapper


def simple_rbac_execute(entity: User | Group, fun: Callable, perm: Permission) -> Any:
    """
    Simple RBAC wrapper intended to ease usecases
    where you don't want to pass entity to the called function.
    Example usage:
        @rbac_set_permissions(fun, permission)
        def my_fun():
            return "Hello"

        simple_rbac_execute(
            user,
            lambda: my_fun(),
            my_fun.__rbac_permission__
        )
    """
    rbac_call_predicate(entity, fun, perm)
    return fun()
