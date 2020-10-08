from typing import Union

from core.storages._base import BaseStorage
from core.storages._in_memory import InMemoryStorage


# TODO(hvy): Should be possible to register storage string to class mappings to core.
# Then, `get_storage` could be moved to core.
def get_storage(storage: Union[None, str, BaseStorage]) -> BaseStorage:

    if storage is None:
        return InMemoryStorage()
    if isinstance(storage, str):
        raise NotImplementedError
    return storage
