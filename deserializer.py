import struct
import logging
from typing import TypeVar, Type, List

T = TypeVar('T')


class DeserializationError(Exception):
    """Custom exception for errors during deserialization."""
    pass


def unpack_from(format: str, buffer: bytearray) -> tuple:
    """Unpacks data from the buffer and removes it."""
    size = struct.calcsize(f">{format}")
    if len(buffer) < size:
        raise DeserializationError(f"Buffer too short. Need {size} bytes, have {len(buffer)} for format '{format}'.")

    value = struct.unpack_from(f">{format}", buffer)
    del buffer[:size]
    return value


def unpack_primitive(format: str, buffer: bytearray):
    """Unpacks a single primitive value."""
    return unpack_from(format, buffer)


def unpack_string(buffer: bytearray, is_legacy: bool = False) -> str:
    """
    Unpacks a string from the buffer.
    - V2 strings are null-terminated and prefixed with their length (including null).
    - Legacy strings are not null-terminated and are prefixed with their length.
    """
    try:
        length = unpack_primitive("L", buffer)
        if len(buffer) < length:
            raise DeserializationError(f"Buffer too short for string. Need {length} bytes, have {len(buffer)}.")

        if is_legacy:
            # Legacy strings are not null-terminated
            value = buffer[:length].decode('utf-8', errors='replace')
        else:
            # V2 strings have a null terminator
            if length == 0 or buffer[length - 1] != 0:
                logging.warning(f"Malformed V2 string detected: length={length}, buffer does not end with null.")
                # Still try to decode what's there, assuming it might be a non-compliant string
                value = buffer[:length].decode('utf-8', errors='replace').rstrip('\x00')
            else:
                value = buffer[:length - 1].decode('utf-8', errors='replace')

        del buffer[:length]
        return value
    except (struct.error, IndexError) as e:
        raise DeserializationError(f"Failed to unpack string: {e}")


def unpack_list(buffer: bytearray, model_class: Type[T]) -> List[T]:
    """
    Unpacks a list of model objects from the buffer.
    Each model class must have a `from_buffer` class method.
    """
    items = []
    count, = unpack_primitive("L", buffer)
    for _ in range(count):
        if not hasattr(model_class, 'from_buffer'):
            raise NotImplementedError(f"The class {model_class.__name__} must have a 'from_buffer' class method.")
        item = model_class.from_buffer(buffer)
        items.append(item)
    return items
