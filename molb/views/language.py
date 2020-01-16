from aiohttp.web import HTTPFound


async def language(request):
    path_items = request.path.split('/')
    if "en" in path_items:
        locale = "en"
    else:
        locale = "fr"

    url = request.headers.get("HTTP_REFERER")
    if url is None:
        url = request.app.router["home"].url_for()
    resp = HTTPFound(url)
    resp.set_cookie("locale", locale)
    return resp
