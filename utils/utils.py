def bool_from_str(text: str) -> bool:
    if text.lower() == 'true':
        return True
    if text.lower() == 'false':
        return False
    return False

class Serializer(object):
    @property
    def value(self):
        dict_values = {k: v for k, v in self.__dict__.items() if v is not None}
        if not dict_values:
            return None
        return dict_values