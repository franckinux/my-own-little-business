from functools import wraps

from aiohttp.web import HTTPForbidden
from aiohttp_security import permits


def require(permission):
    def wrapper(f):
        @wraps(f)
        async def wrapped(request):
            has_perm = await permits(request, permission)
            if not has_perm:
                message = "User has no permission \"{}\"".format(permission)
                raise HTTPForbidden(body=message)
            return await f(request)
        return wrapped
    return wrapper
