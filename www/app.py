import logging; logging.basicConfig(level=logging.INFO)
#配置日志输出方式与级别：INFO：普通信息;logging作用为输出信息
import asyncio, os, json, time
#异步IO，操作系统，json格式，时间
from datetime import datetime
from aiohttp import web
#http框架
def index(request):
	return web.Response(body=b"<h1>Awesome</h1>",content_type='text/html')
#处理http请求的方法
# 首页返回b'<h1>Awesome</h1>' chrome浏览器得加上ontent_type='text/html'才能正常显示
@asyncio.coroutine
#把一个generator标记为coroutine类型，然后扔到EventLoop中执行。
def init(loop):
	app = web.Application(loop=loop)
	#封装的某个东西？？？？？不懂 往web对象中加入信息循环，生成一个支持异步IO的对象
	app.router.add_route('GET', '/', index)
	#GET：请求方式；/：根目录； index：上文定义的函数
	srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9002)
	#127.0.0.1为本机地址 端口可以是9000,9001...；进行监听
	logging.info('server started at http://127.0.0.1:9002...')
	return srv #持续监听

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()