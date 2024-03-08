# pylint: disable=import-error
# pylint: disable=unused-import
import asyncio  # noqa: F401
import os

import aioredis
from aiohttp import web

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

redis = aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
app = web.Application()
routes = web.RouteTableDef()


@routes.get("/")
async def hello(request):  # pylint: disable=unused-argument
    counter = await redis.incr("mycounter")
    return web.Response(text=f"counter={counter}")


@routes.get("/hello.json")
async def hello_json(request):  # pylint: disable=unused-argument
    counter = await redis.incr("mycounter")
    data = {"counter": counter}
    return web.json_response(data)


app.add_routes(routes)


def main():
    web.run_app(app, port=8080)


if __name__ == "__main__":
    main()
