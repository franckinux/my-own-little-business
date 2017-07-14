from aiohttp import web
from aiohttp_jinja2 import render_template
from aiohttp_session_flash import flash


async def error_middleware(app, handler):
    async def middleware_handler(request):
        try:
            response = await handler(request)
            if response.status in [403, 404]:
                if response.status == 403:
                    message = "Forbidden"
                else:
                    message = "Not found"
                flash(request, ("danger", message))
                return render_template( "error.html", request, {})
            return response
        except web.HTTPException as e:
            flash(request, ("danger", str(e)))
            return render_template("error.html", request, {})
    return middleware_handler
