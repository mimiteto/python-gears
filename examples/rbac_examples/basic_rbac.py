#! /usr/bin/env python3

# type: ignore

"""
This is the most basic example of RBAC usage.
We will generate our RBAC model and then use it to wrap a class and a function.
At the end we will check if a user has the required permissions to execute the wrapped function.
"""

from gears import rbac


RBAC = rbac.RBAC()
RBAC.add_user("user1")
RBAC.add_user("user2")
RBAC.add_user("user3")  # This user will not have any access
RBAC.add_role("admin")
RBAC.add_role("reader")
RBAC.add_role("function_writer")
RBAC.add_role("function_reader")
RBAC.add_permission("MyClass", rbac.PermissionType.READ)
RBAC.add_permission("MyClass", rbac.PermissionType.EXECUTE)
RBAC.add_permission("MyOtherClass", rbac.PermissionType.NONE)
RBAC.add_permission("MyOtherClass", rbac.PermissionType.WRITE)
RBAC.add_permission("my_function", rbac.PermissionType.WRITE)
RBAC.add_permission("my_function", rbac.PermissionType.READ)
RBAC.add_permission_to_role("MyClass:EXECUTE", "admin")
RBAC.add_permission_to_role("MyClass:READ", "reader")
RBAC.add_permission_to_role("MyOtherClass:WRITE", "admin")
RBAC.add_permission_to_role("my_function:READ", "function_reader")
RBAC.add_permission_to_role("my_function:WRITE", "function_writer")
RBAC.add_user_to_role("user1", "admin")
RBAC.add_user_to_role("user2", "reader")
RBAC.add_user_to_role("user1", "function_reader")
RBAC.add_user_to_role("user2", "function_writer")


# This is the most basic example of RBAC usage.
# We have our methods with set permission and the read method will fall back to the default value.
#
# One thing to note - when going default-all, public methods need to accept `entity` argument
# as one of their arguments.
# The rbac wrapper looks specifically for an argument named `entity` in the keyworded arguments.
# If there is none - first argument will be used as entity. There is no type check performed.
# This is chosen by default to allow passing down users and enforcing nested access controls.
@rbac.rbac_decorate_class
class MyClass:
    """
    This is our basic class.
    We are defining custom access levels for two methods - write and execute.
    read method will default to the default access level - READ.
    One thing to note - it's not necessary to name your permission after the class name,
    although default permissions are generated like that.
    """
    _rbac: dict[str, rbac.Permission] = {
        "write": rbac.Permission("MyClass", rbac.PermissionType.WRITE),
        "execute": rbac.Permission("MyClass", rbac.PermissionType.EXECUTE),
    }

    def __init__(self):
        self._data: str = "Some data"

    def read(self, entity: rbac.User | rbac.Group) -> str:
        """
        This method defaults to permissions with read level, named after the class.
        You can use entity to call other functions with the permission that was passed
        """
        return self._data

    def write(self, entity: rbac.User | rbac.Group, data) -> None:
        self._data = f"{data} - written by {str(entity)}"

    def execute(self, entity: rbac.User | rbac.Group) -> str:
        return f"Executed by {str(entity)}"


my_obj = MyClass()
# user1 can read this data
# as they have higher access level than required
print(my_obj.read(entity=rbac.User('user1')))


# In this next example we will make all methods usable without any access level required
# except for the `write` method, which will required 'MyOtherClass:write'
# We will configure the wrapper to not pass the entity to the class functions.
# This has the downside that linterrs will raise warnings that the entity argument is not expected.
@rbac.rbac_decorate_class
class MyOtherClass:
    """
    This class doesn't have enforced rback on most methods.
    It also don't accept entites as arguments.
    """
    _rback_pass = {
        rbac.RBAC_PASS_ENTITY_KEY: False
    }
    _rbac: dict[str, rbac.Permission] = {
        "__rbac_permission__": RBAC.get_permission("MyOtherClass:NONE"),
        "write": RBAC.get_permission("MyOtherClass:WRITE")
    }

    def hello(self) -> str:
        """ This method is public and can be called by anyone """
        return "Hello"

    def write(self, data):
        """ This method requires 'MyOtherClass:WRITE' permission """
        return data


# pylint: disable=unexpected-keyword-arg
my_other_obj = MyOtherClass()
# Because permission level is at the lowest, we can supply None as entity
print(my_other_obj.hello(entity=None))
# or user without any permission on this level
print(my_other_obj.hello(entity=rbac.User('user3')))
try:
    my_other_obj.write(entity=rbac.User('user2'), data="Some data")  # user2 is not available
except rbac.AccessDenied as e:
    print(e)


# Here is how to wrap your function with RBAC
@ rbac.rbac
@ rbac.rbac_decorate_func(permission="my_function:WRITE")
def my_function_writer(entity: rbac.User | rbac.Group, data: str) -> str:
    """ This function requires 'my_function:WRITE' permission """
    return f"In my_function_writer, {str(entity)} is writer. Data written: {data}"


try:
    my_function_writer(entity=rbac.User('user1'), data="Some data")  # user1 can't write here.
except rbac.AccessDenied as e:
    print(e)

print(my_function_writer(entity=rbac.User('user2'), data="Succesfull execution!"))


# Here decoreated function will not be able to access the entity
@ rbac.rbac
@ rbac.rbac_decorate_func(permission="my_function:READ", populate_entity=False)
def my_reader(*args, **kwargs) -> str:
    """ This function requires 'my_function:READ' permission """
    return f"Reader is reading {args}, {kwargs}"


try:
    print(my_reader(entity=rbac.User('user3'), my_data="Some data"))
except rbac.AccessDenied as e:
    print(f"Access was rejected and entity is unknows for the function. Error is {e}")

print(my_reader(entity=rbac.User('user1'), my_data="Some data"))
