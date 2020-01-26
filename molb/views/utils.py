from aiohttp_babel.middlewares import _
from aiohttp_session_flash import flash as original_flash
from aiohttp_session import get_session
from babel.support import LazyProxy


DAYS = ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday")


class RollbackTransactionException(Exception):
    pass


def remove_special_data(dico):
    del dico["csrf_token"]
    del dico["submit"]
    return dico


def array_to_days(data):
    days = data.pop("days", [False] * 7)
    data.update(dict(zip(DAYS, days)))
    return data


def days_to_array(data):
    days = []
    for d in DAYS:
        days.append(data.pop(d, False))
    data["days"] = days
    return data


async def generate_csrf_meta(request):
    return {
        "csrf_context": await get_session(request),
        "csrf_secret": request.app["config"]["application"]["secret_key"].encode("ascii")
    }


def field_list(data):
    return ", ".join(data.keys())


def place_holders(data):
    """Returns "$1, $2, ..., $n"""
    return ", ".join(['$' + str(i + 1) for i in range(len(data))])


def settings(data):
    """Return field1 = $1, ..., fieldn = $n"""
    return ", ".join([k + " = $" + str(i + 1) for i, k in enumerate(data.keys())])


def lazy_gettext(s):
    return LazyProxy(_, s, enable_cache=False)


_l = lazy_gettext


# convert lazy string to string as it cannot be stored in a session as is
def flash(request, msg):
    msg_ = (msg[0], str(msg[1]))
    return original_flash(request, msg_)
