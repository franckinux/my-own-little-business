from aiohttp_session import get_session


def remove_special_data(items):
    dico = dict(items)
    del dico["csrf_token"]
    del dico["submit"]
    return dico


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
