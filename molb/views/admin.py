import aiohttp_jinja2
from auth import require


@aiohttp_jinja2.template("admin.html")
@require("admin")
async def admin_menu(request):
    return