import sys

from typing import (
        Callable,
        Any,
        Union,
        TypedDict,
        TypeVar,
        Type,
        Protocol,
        NoReturn,
    )


class _FieldsDict(TypedDict):
    type_hint: Any
    default_value: Union[str, Any]


class FrozenError(Exception):
    pass


_FIELDS_TYPE_HINT = Union[dict[str, _FieldsDict], dict]
_FUNC_SIGNATURE_TEMPLATE: str = 'def {} (self, '
_T = TypeVar('_T')


class SupportsDatacls(Protocol):

    @property
    def fields(self) -> _FIELDS_TYPE_HINT:
        pass


_X = TypeVar('_X', bound=SupportsDatacls)


def asdict(datacls_instance: _X) -> dict[str, Any]:
    # Create dict from fields in datacls_instance

    result: dict[str, Any] = {}

    for field in datacls_instance.fields:

        result[field] = getattr(datacls_instance, field)

    return result


def _repr(self) -> str:

    cls_name = self.__class__.__name__

    constructor = f'{cls_name}('

    template = '{} = {}, '

    for field in self._fields:

        constructor += template.format(field, getattr(self, field))

    else:

        constructor += ')'

    return constructor


def _eq(self, other: _X) -> bool:

    return asdict(self) == asdict(other)


def _setattr(self, field, value) -> NoReturn:

    raise FrozenError('Fields in datacls instance is frozen')


def _create_func_signature(func_name: str, args: _FIELDS_TYPE_HINT) -> str:
    # create function signature from args and func_name: def {func_name}({args}):

    args_value: dict[str, list[str]] = {'with_default_value': [], 'no_default_value': []}

    for arg_name, arg_value in args.items():

        arg_template = '{} = {}'

        if arg_value['default_value'] == '_NotDefaultValue':

            arg_template = arg_template[:-5]

            args_value['no_default_value'].append(arg_template.format(arg_name))

        else:

            args_value['with_default_value'].append(arg_template.format(arg_name,
                                                                        arg_value['default_value']))

    signature = (_FUNC_SIGNATURE_TEMPLATE.format(func_name) + ', '.join(args_value['no_default_value']
                                                                        + args_value['with_default_value']) + '):')

    return signature


def _create_property(attr_name: str) -> property:

    def getter(self) -> Any:
        return getattr(self, attr_name)

    return property(getter)


def _create_fn(*, func_name: str, signature: str, body: str, cls: type) -> Callable[[Any], Any]:
    # create function from signature and body

    # get the globals of the module in which the class is declared
    cls_module_globals = sys.modules.get(cls.__module__).__dict__

    function: dict[str, Callable] = {}

    # create function
    exec(signature + body, cls_module_globals, function)

    return function[func_name]


def _create_and_add_init(post_init: bool, cls: Type[_T]) -> None:
    # create __init__ for decorated class

    # create __init__ signature
    signature = _create_func_signature('__init__', cls._fields)

    # example: self.attr = attr
    instance_attr_template = 'object.__setattr__(self, "{}", {})'

    init_body = '\n'

    for field in cls._fields:
        init_body += '\t' + instance_attr_template.format(field, field) + '\n'

    # call post_init from class
    if post_init:
        init_body += '\tself.__post_init__()'

    init = _create_fn(func_name='__init__', signature=signature, body=init_body, cls=cls)

    setattr(cls, '__init__', init)


def _read_annotations(cls: Type[_T]) -> _FIELDS_TYPE_HINT:
    # read elements in __annotations__ from the class

    fields = {}

    # create fields from class annotations
    for name, type_hint in cls.__annotations__.items():
        fields[name] = _FieldsDict(
            type_hint=type_hint,
            default_value=getattr(cls, name, '_NotDefaultValue')
        )

    return fields


def _create_and_add_repr(cls: Type[_T]) -> None:
    # add __repr__ in cls

    setattr(cls, '__repr__', _repr)


def _create_and_add_eq(cls: Type[_T]) -> None:
    # add __eq__ in cls

    setattr(cls, '__eq__', _eq)


def _make_frozen(cls: Type[_T]) -> None:
    # make class instances immutable

    setattr(cls, '__setattr__', _setattr)


def _add_slots(cls: Type[_T]) -> None:

    fields = cls._fields

    slots = tuple(fields.keys())

    setattr(cls, '__slots__', slots)


def _make_datacls(cls: Type[_T], init: bool, repr: bool,
                  eq: bool, frozen: bool) -> Type[_T]:

    # create fields
    setattr(cls, '_fields', _read_annotations(cls))

    # create property for fields
    setattr(cls, 'fields', _create_property('_fields'))

    # if slots:
    #
    #     _add_slots(cls)

    if init:
        # True if class have _post_init_
        # at the moment you should not add any argumentsAPI
        # to __post_init__ other than self
        post_init = getattr(cls, '__post_init__', False)

        # add __init__ in class
        _create_and_add_init(post_init, cls)

    if repr:

        # add __repr__ in class
        _create_and_add_repr(cls)

    if eq:

        # add __eq__ in class
        _create_and_add_eq(cls)

    if frozen:

        _make_frozen(cls)

    return cls


def datacls(cls: Union[Type[_T], None] = None, /, *, init: bool = True, repr: bool = True,
            eq: bool = True, frozen: bool = False) -> Union[Type[_T], Callable[[Any], Callable]]:
    # Signature is identical to dataclasses

    if cls is None:

        def wrap(_cls):

            return _make_datacls(_cls, init, repr, eq, frozen)

        return wrap

    else:

        return _make_datacls(cls, init, repr, eq, frozen)


# TEST
if __name__ == '__main__':

    @datacls(frozen=True)
    class TestUser:
        Name: str
        Age: int

        def __post_init__(self):

            print(f'Call __post_init__ for {self}')

    user_list = [TestUser('Antonio', 23), TestUser('Jeyson', 49)]

    print(asdict(user_list[0]))
    print('test')