#! /usr/bin/env python3

"""
Module tests RBAC utils
"""

import unittest
from unittest.mock import MagicMock, patch

from gears.rbac import (
    RBAC,
    RBACNotFound,
    RBACEntityNotFound,
    RBACPermissionNotFound,
    RBACRoleNotFound,
    AccessDenied,
    PermissionType,
    Permission,
    Role,
    Entity,
    User,
    Group,
    rbac_execute,
    rbac_set_permission,
    rbac_can_entity_do,
    rbac_call_predicate,
    rbac_decorate_class,
    rbac_decorate_func,
    rbac,
    RBAC_PERMISSION_KEY,
    RBAC_PASS_ENTITY_KEY,
    RBAC_CLASS_PASS_VAR,
    RBAC_CLASS_VAR
)


class TestPermission(unittest.TestCase):
    """ Test the Permission class """

    def test_permission(self):
        """ Test creating a Permission """
        permission = Permission("test_permission", PermissionType.READ)
        self.assertEqual("test_permission:READ", permission)

    def test_permission_str(self):
        """ Test string representation of a Permission """
        permission = Permission("test_permission", PermissionType.READ)
        self.assertEqual("test_permission:READ", str(permission))

    def test_permission_eq(self):
        """ Test comparing Permissions """
        permission1 = Permission("test_permission", PermissionType.READ)
        permission2 = Permission("test_permission", PermissionType.READ)
        self.assertEqual(permission1, permission2)

    def test_permission_ne(self):
        """ Test comparing different Permissions """
        permission1 = Permission("test_permission1", PermissionType.READ)
        permission2 = Permission("test_permission1", PermissionType.WRITE)
        permission3 = Permission("test_permission2", PermissionType.READ)
        self.assertNotEqual(permission1, permission2)
        self.assertNotEqual(permission1, permission3)

    def test_str_to_permission(self):
        """ Test converting a string to a Permission """
        permission = Permission("test_permission", PermissionType.READ)
        self.assertEqual(permission, Permission.str_to_perm("test_permission:READ"))

    def test_in(self):
        """ Test checking if a permission is in a list """
        permission = Permission("test_permission", PermissionType.READ)
        permission_not_added = Permission("test_permission", PermissionType.WRITE)
        self.assertTrue(permission in [permission])
        self.assertTrue(permission_not_added not in [permission])


class TestGroup(unittest.TestCase):
    """ Test the Group class """

    def test_group(self):
        """ Test creating a Group """
        group = Group("test_group")
        user1 = User("test_user1")
        user2 = User("test_user2")
        user3 = User("test_user3")
        group.add_user(user1)
        group.add_user(user2)
        self.assertTrue(user1 in group.users.values())
        self.assertTrue(user2 in group.users.values())
        self.assertFalse(user3 in group.users.values())
        self.assertListEqual([user1, user2], group.get_users())
        self.assertListEqual(
            ["user:test_user1", "user:test_user2"], group.get_user_names()
        )
        self.assertTrue(group.has_entity(user1))
        with self.assertRaises(RBACEntityNotFound):
            group.has_entity(Entity("user:test_entity"))


class TestEntity(unittest.TestCase):
    """ Test the Entity class """

    def test_entity(self):
        """ Test creating an Entity """
        with self.assertRaises(ValueError):
            Entity("test_entity")
        Entity("user:test_user")
        Entity("group:test_group")


class TestRole(unittest.TestCase):
    """ Test the Role class """

    def test_role(self):
        """ Test creating a Role """
        role = Role("test_role")
        self.assertEqual("test_role", str(role))

    def test_role_permissions(self):
        """ Test adding permissions to a Role """
        role = Role("test_role")
        permission = Permission("test_permission", PermissionType.READ)
        role.attach_permission(permission)
        self.assertTrue(
            permission in role.permissions
        )

    def test_can_do(self):
        """ Test checking if a Role can do something """
        role = Role("test_role")
        permission = Permission("test_permission", PermissionType.READ)
        role.attach_permission(permission)
        self.assertTrue(role.can_do(permission))


class TestRBAC(unittest.TestCase):
    """ Test the RBAC module """

    def setUp(self):
        with patch("gears.rbac.SingletonController", autospec=True):
            self.rbac: RBAC = RBAC()  # type: ignore

    def test_add_user(self):
        """ Test adding a user to the RBAC """

        self.rbac.add_user("test_user")
        self.assertTrue("test_user" in self.rbac.get_user_names())

    def test_add_group(self):
        """ Test adding a group to the RBAC """

        self.rbac.add_group("test_group")
        self.assertTrue("test_group" in self.rbac.get_group_names())

    def test_add_permission(self):
        """ Test adding a permission to the RBAC """

        self.rbac.add_permission("test_permission", PermissionType.READ)
        permission = self.rbac.get_permission("test_permission:READ")
        self.assertEqual(permission.name, "test_permission")
        self.assertEqual(permission.level, PermissionType.READ)

    def test_add_role(self):
        """ Test adding a role to the RBAC """

        self.rbac.add_role("test_role")
        self.assertEqual("test_role", str(self.rbac.get_role('test_role')))

    def test_add_permission_to_role(self):
        """ Test adding a permission to a role """

        self.rbac.add_role("test_role")
        self.rbac.add_permission("test_permission", PermissionType.READ)
        self.rbac.add_permission_to_role("test_permission:READ", "test_role")
        role = self.rbac.get_role("test_role")
        self.assertTrue("test_permission:READ" in role.permissions)

    def test_add_user_to_role(self):
        """ Test adding a user to a role """

        self.rbac.add_role("test_role")
        self.rbac.add_user("test_user")
        self.rbac.add_user_to_role("user:test_user", "test_role")
        user = self.rbac.get_entity(User("test_user"))
        self.assertTrue("user:test_user" in self.rbac._rbind_to_ent)
        self.assertTrue(user.name in self.rbac._rbind_to_ent)

    def test_add_group_to_role(self):
        """ Test adding a group to a role """

        self.rbac.add_role("test_role")
        self.rbac.add_group("test_group")
        self.rbac.add_group_to_role("group:test_group", "test_role")
        group = self.rbac.get_entity(Group("test_group"))
        self.assertTrue("group:test_group" in self.rbac._rbind_to_ent)
        self.assertTrue(group.name in self.rbac._rbind_to_ent)

    def test_get_entity_permissions(self):
        """ Test getting entity permissions """

        self.rbac.add_permission("test_permission", PermissionType.READ)
        self.rbac.add_role("test_role")
        self.rbac.add_permission_to_role("test_permission:READ", "test_role")
        self.rbac.add_user("test_user")
        self.rbac.add_user_to_role(User("test_user"), "test_role")
        permissions = self.rbac.get_entity_permissions("user:test_user")
        self.assertTrue(
            Permission(name="test_permission", level=PermissionType.READ) in permissions
        )

    def test_get_entity_roles(self):
        """ Test getting entity roles """

        self.rbac.add_role("test_role")
        self.rbac.add_user("test_user")
        self.rbac.add_user_to_role("user:test_user", "test_role")
        roles = self.rbac.get_entity_roles(User("test_user"))
        self.assertTrue(Role(name="test_role") in roles)

    def test_can_entity_do(self):
        """ Test checking if an entity can do something """

        self.rbac.add_permission("test_permission", PermissionType.WRITE)
        self.rbac.add_permission("test_permission", PermissionType.READ)
        self.rbac.add_permission("test_permission", PermissionType.NONE)
        self.rbac.add_role("test_role")
        self.rbac.add_permission_to_role("test_permission:READ", "test_role")
        self.rbac.add_user("test_user")
        self.rbac.add_user_to_role("user:test_user", "test_role")
        self.assertTrue(self.rbac.can_entity_do("user:test_user", "test_permission:READ"))
        self.assertTrue(
            self.rbac.can_entity_do("everything_will_pass", "test_permission:NONE")
        )
        self.assertFalse(
            self.rbac.can_entity_do("user:test_user", "test_permission:WRITE")
        )

    def test_entity_inheritance(self):
        """ Test entity inheritance """

        self.rbac.add_permission("test_permission", PermissionType.READ)
        self.rbac.add_role("test_role")
        self.rbac.add_permission_to_role("test_permission:READ", "test_role")
        self.rbac.add_user("test_user")
        self.rbac.add_group("test_group")
        self.rbac.add_user_to_group("test_user", "test_group")
        self.rbac.add_group_to_role("group:test_group", "test_role")
        self.assertTrue(
            self.rbac.can_entity_do(User("test_user"), "test_permission:READ")
        )

    def test_invalid_entity_name(self):
        """ Test invalid entity name """

        with self.assertRaises(ValueError):
            self.rbac.add_user("invalid:user")

    def test_entity_not_found(self):
        """ Test entity not found """

        with self.assertRaises(RBACEntityNotFound):
            self.rbac.get_entity("non_existing_entity")

    def test_permission_not_found(self):
        with self.assertRaises(RBACPermissionNotFound):
            self.rbac.get_permission("non_existing_permission")

    def test_role_not_found(self):
        """ Test role not found """

        with self.assertRaises(RBACRoleNotFound):
            self.rbac.get_role("non_existing_role")

    def test_get_entity(self) -> None:
        """ Test getting an entity """

        self.rbac.add_user("test_user")
        self.assertTrue(isinstance(self.rbac.get_entity("user:test_user"), User))
        self.rbac.add_group("test_group")
        self.assertTrue(isinstance(self.rbac.get_entity(Group("test_group")), Group))
        with self.assertRaises(RBACEntityNotFound):
            self.rbac.get_entity("non_existing_entity")
        with self.assertRaises(RBACEntityNotFound):
            self.rbac.get_entity(User("nonexisting_user"))
        with self.assertRaises(RBACEntityNotFound):
            self.rbac.get_entity(Group("nonexisting_group"))
        with self.assertRaises(RBACEntityNotFound):
            self.rbac.get_entity(MagicMock(name=""))

    def test_get_permission(self) -> None:
        """ Test getting a permission """

        self.rbac.add_permission("test_permission", PermissionType.READ)
        self.assertTrue(
            isinstance(self.rbac.get_permission("test_permission:READ"), Permission)
        )
        with self.assertRaises(RBACPermissionNotFound):
            self.rbac.get_permission("non_existing_permission")
        self.assertEqual(
            self.rbac.get_permission(
                Permission(name="test_permission", level=PermissionType.READ)
            ),
            Permission(name="test_permission", level=PermissionType.READ)

        )

    def test_get_users(self) -> None:
        """ Test getting users """
        user = User("test_user")
        self.rbac.add_user("test_user")
        self.assertTrue("test_user" in self.rbac.get_user_names())
        self.assertListEqual([user], self.rbac.get_users())

    def test_get_groups(self) -> None:
        """ Test getting groups """
        group = Group("test_group")
        self.rbac.add_group("test_group")
        self.assertTrue("test_group" in self.rbac.get_group_names())
        self.assertListEqual([group], self.rbac.get_groups())

    def test_get_role(self) -> None:
        """ Test getting roles """
        role = Role("test_role")
        self.rbac.add_role("test_role")
        self.assertEqual(
            role, self.rbac.get_role(role)
        )


class TestRBACDecorators(unittest.TestCase):
    """ Test the RBAC decorators and wrappers """

    def test_rbac_set_permission(self):
        """ Test the rbac_set_permission decorator """
        def fun(args, kwargs):
            return True

        f = rbac_set_permission(fun, Permission.str_to_perm("test_permission:READ"))
        self.assertTrue(hasattr(f, RBAC_PERMISSION_KEY))

    def test_rbac_set_permission_pass_attr(self):
        """ Test the rbac_set_permission decorator with pass_attr """
        def fun():
            return True

        with self.subTest("No pass_attr"):
            f = rbac_set_permission(fun, Permission.str_to_perm("test_permission:READ"))
            self.assertTrue(hasattr(f, RBAC_PERMISSION_KEY))
            self.assertFalse(hasattr(f, RBAC_PASS_ENTITY_KEY))

        with self.subTest("With pass_attr"):
            f = rbac_set_permission(
                fun, Permission.str_to_perm("test_permission:READ"), populate_entity=True
            )
            self.assertTrue(hasattr(f, RBAC_PERMISSION_KEY))
            self.assertTrue(hasattr(f, RBAC_PASS_ENTITY_KEY))
            self.assertTrue(getattr(f, RBAC_PASS_ENTITY_KEY))

        with self.subTest("With pass_attr False"):
            f = rbac_set_permission(
                fun, Permission.str_to_perm("test_permission:READ"), populate_entity=False
            )
            self.assertTrue(hasattr(f, RBAC_PERMISSION_KEY))
            self.assertTrue(hasattr(f, RBAC_PASS_ENTITY_KEY))
            self.assertFalse(getattr(f, RBAC_PASS_ENTITY_KEY))

    def test_rbac_can_entity_do(self):
        """ Test the rbac_can_entity_do decorator """

        def _rbac_test_wrp(is_true: bool, perm: str) -> bool:
            """ Helper for test wrapper """
            _rbac = MagicMock()
            setattr(
                fun, RBAC_PERMISSION_KEY, Permission.str_to_perm(perm)
            )
            _rbac.can_entity_do.return_value = is_true
            _rbac.get_entity = MagicMock()
            _rbac.get_entity.return_value = MagicMock()
            with patch("gears.rbac.RBAC", return_value=_rbac):
                return rbac_can_entity_do(fun, "user:user")

        def fun(*args, **kwargs):
            return True

        with self.subTest("No permission assigned"):
            with self.assertRaises(RBACNotFound):
                rbac_can_entity_do(fun, "user:user")

        with self.subTest("Permission assigned, access good"):
            self.assertTrue(_rbac_test_wrp(True, "test_permission:READ"))

        with self.subTest("Permission assigned, access bad"):
            self.assertFalse(_rbac_test_wrp(False, "test_permission:READ"))

        with self.subTest("Permission does not need to be checked"):
            self.assertTrue(_rbac_test_wrp(False, "test_permission:NONE"))

    def test_rbac_call_predicate(self):
        """ Test the rbac_call_predicate decorator """

        def fun(*args, **kwargs):
            return True

        with patch("gears.rbac.RBAC") as _rbac:
            _rbac.get_entity = MagicMock()
            _rbac.get_entity.return_value = MagicMock()

            with self.subTest("No permission assigned"):
                with self.assertRaises(RBACNotFound):
                    rbac_call_predicate("user:user", fun)

            with self.subTest("Permission assigned, acess denied"):
                setattr(
                    fun, RBAC_PERMISSION_KEY, Permission.str_to_perm("test_permission:READ")
                )
                with patch("gears.rbac.rbac_can_entity_do", return_value=False):
                    with self.assertRaises(AccessDenied):
                        rbac_call_predicate("user:user", fun)

            with self.subTest("Permission assigned, acess granted"):
                setattr(
                    fun, RBAC_PERMISSION_KEY, Permission.str_to_perm("test_permission:READ")
                )
                with patch("gears.rbac.rbac_can_entity_do", return_value=True):
                    rbac_call_predicate("user:user", fun)

    def test_rbac_decorate_class(self):
        """ Test the rbac_decorate_class decorator """

        with self.subTest("All defaults"):
            perm = Permission.str_to_perm("TestClass:READ")

            @rbac_decorate_class
            class TestClass:
                """ TestClass """

                def __init__(self):
                    pass

                def method1(self):
                    "M2"

                def method2(self):
                    "M2"

            self.assertTrue(hasattr(TestClass, RBAC_CLASS_VAR))
            self.assertTrue(hasattr(TestClass, RBAC_CLASS_PASS_VAR))
            self.assertDictEqual(
                getattr(TestClass, RBAC_CLASS_VAR),
                {RBAC_PERMISSION_KEY: perm}
            )
            for m in [TestClass.method1, TestClass.method2]:
                self.assertEqual(
                    getattr(m, RBAC_PERMISSION_KEY),
                    perm
                )


if __name__ == '__main__':
    unittest.main(verbosity=2)
