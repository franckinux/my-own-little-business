import aiohttp_jinja2

@aiohttp_jinja2.template("page.html")
async def handler(request):
    return {"name": "Franck"}
