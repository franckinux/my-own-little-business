from aiohttp_session import get_session


def remove_special_data(items):
    dico = dict(items)
    del dico["csrf_token"]
    del dico["submit"]
    return dico


async def generate_csrf_meta(request):
    return {
        "csrf_context": await get_session(request),
        "csrf_secret": request.app["config"]["application"]["csrf_secret_key"].encode("ascii")
    }
