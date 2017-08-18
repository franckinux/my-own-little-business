from aiohttp import web
from aiohttp_jinja2 import render_template
from aiohttp_session_flash import flash


async def error_middleware(app, handler):
    async def middleware_handler(request):
        try:
            response = await handler(request)
            if response.status in [400, 403, 404, 405]:
                if response.status == 400:
                    message = "Bad request"
                elif response.status == 403:
                    message = "Forbidden"
                elif response.status == 404:
                    message = "Not found"
                else:
                    message = "Method not allowed"
                flash(request, ("danger", message))
                return render_template( "error.html", request, {})
            return response
        except web.HTTPException as e:
            flash(request, ("danger", str(e)))
            return render_template("error.html", request, {})
    return middleware_handler
