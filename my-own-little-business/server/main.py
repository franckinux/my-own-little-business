#!/usr/bin/env python3

# import asyncio
from aiohttp import web
import pathlib
from yaml import safe_load


app = web.Application()

conf = safe_load(str(pathlib.Path('.')/"config"/"my-own-little-business.yaml"))
app["config"] = conf

web.run_app(app, host="127.0.0.1", port=8080)
