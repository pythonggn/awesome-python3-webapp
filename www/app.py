__author__ = 'ggn'
'''
async web application
'''
import logging; logging.basicConfig(level=logging.INFO)
#配置日志输出方式与级别：INFO：普通信息;logging作用为输出信息
import asyncio, os, json, time
#异步IO，操作系统，json格式，时间
from datetime import datetime
from aiohttp import web
#http框架
from jinja2 import Environment, FileSystemLoader
# 从jinja2模板库导入环境与文件系统加载器
import orm
from coroweb import add_routes, add_static
import handlers

def init_jinja2(app, **kw): # 选择jinja2作为模板, 初始化模板
	logging.info('init jinja2...')
	# 设置jinja2的Environment参数:
	options = dict(
		autoescape = kw.get('autoescape', True),  # 自动转义xml/html的特殊字符
		#kw.get(): get() 函数返回字典中指定键的值,不存在则返回指定值
		block_start_string = kw.get('block_start_string', '{%'),  # 代码块开始标志
		block_end_string = kw.get('block_end_string', '%}'),  # 代码块结束标志
		variable_start_string = kw.get('variable_start_string', '{{'),  # 变量开始标志
		variable_end_string = kw.get('variable_end_string', '}}'),  # 变量结束标志
		auto_reload = kw.get('auto_reload', True) # 每当对模板发起请求,加载器首先检查模板是否发生改变.若是,则重载模板
	)
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
		# 当前脚本文件的绝对路径=》去掉文件名的目录路径=》路径末尾添加templates
		# 以上操作得到同目录的templates文件夹路径
	logging.info('set jinja2 template path: %s' % path)
	# 若路径不存在,则将当前目录下的templates(www/templates/)设为jinja2的目录
	# os.path.abspath(__file__), 返回当前脚本的绝对路径(包括文件名)
	# os.path.dirname(), 去掉文件名,返回目录路径
	# os.path.join(), 将分离的各部分组合成一个路径名
	env = Environment(loader=FileSystemLoader(path), **options)
	# 拷贝字典options，变成关键字参数传入
	# 初始化jinja2环境, options参数,之前已经进行过设置
	# 加载器负责从指定位置加载模板, 此处选择FileSystemLoader,顾名思义就是从文件系统加载模板,前面我们已经设置了path
	filters = kw.get('filters', None)
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f
	app['__templating__'] = env 
	# 设置过滤器,先通过filters关键字参数获取过滤字典,再通过建立env.filters的键值对建立过滤器
	# 将jinja环境赋给app的__templating__属性


# 创建应用时,通过指定命名关键字为一些"middle factory"的列表可创建中间件Middleware
# 一个middleware可以改变URL的输入、输出，甚至可以决定不继续处理而直接返回。middleware的用处就在于把通用的功能从每个URL处理函数中拿出来，集中放到一个地方。
# 每个middle factory接收2个参数,一个app实例,一个handler, 并返回一个新的handler
# 以下是一些middleware(中间件), 可以在url处理函数处理前后对url进行处理

# 在处理请求之前,先记录日志
@asyncio.coroutine
def logger_factory(app, handler):
	@asyncio.coroutine
	def logger(request):
		#记录日志，包括http method, 和path：
		logging.info('Request: %s %s' % (request.method, request.path))
		#调用传入的handler继续处理请求：
		return (yield from handler(request))
		# handler(request) => RequestHandler(app, fn)(request)
	return logger

# 解析数据:
async def data_factory(app, handler):
	async def parse_data(request):
		if request.method == 'POST':
		# 解析数据是针对post方法传来的数据,若http method非post,将跳过,直接调用handler处理请求
			if request.content_type.startwith('application/json'):
				request.__data__ = await request.json()
				logging.info('request json: %s' % str(request.__data__))
			# content_type字段表示post的消息主体的类型, 以application/json打头表示消息主体为json
			# request.json方法,读取消息主体,并以utf-8解码
			# 将消息主体存入请求的__data__属性
			elif request.content_type.startwith('application/x-www-form-urlencoded'):
				request.__data__ = await request.post()
				logging.info('request form: %s' % str(request.__data__))
			# content type字段以application/x-www-form-urlencodeed打头的,是浏览器表单
			# request.post方法读取post来的消息主体,即表单信息
		return (await handler(request))
		# 调用传入的handler继续处理请求
	return parse_data

# 上面2个middle factory是在url处理函数之前先对请求进行了处理,以下则在url处理函数之后进行处理
# 其将request handler的返回值(返回的response)转换为web.Response对象,以保证满足aiohttp的要求
async def response_factory(app, handler):
	async def response(request):
		logging.info('Response handler...')
		r = await handler(request) # 调用handler调用url处理函数fn处理,并返回response响应结果
		# handler(request) => RequestHandler(app, fn)(request)
		if isinstance(r, web.StreamResponse):
			return r
		# 若响应结果为StreamResponse,直接返回
		# StreamResponse是aiohttp定义response的基类,即所有响应类型都继承自该类
		# StreamResponse主要为流式数据而设计
		if isinstance(r, bytes):
			resp = web.Response(body=r)
			resp.content_type = 'application/octet-stream'
			return resp 
		# 若响应结果为字节流,则将其作为应答的body部分,并设置响应类型为流型
		if isinstance(r, str):
			if r.startwith('redirect:'):
			# 若响应结果为字符串，判断响应结果是否为重定向.若是,则返回重定向的地址
				return web.HTTPFound(r[9:]) 
				# r[9:]--'redirect:'后面的字符串
			resp = web.Response(body=r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			# 响应结果不是重定向,则以utf-8对字符串进行编码,作为body.设置相应的响应类型
			return resp 
		if isinstance(r, dict):
			template = r.get('__template__')
			# 若响应结果为字典,则获取它的模板属性
			if template is None:
				resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
				#dumps()方法返回一个str，内容就是标准的JSON
				resp.content_type = 'application/json;charset=utf-8'
				# 若不存在对应模板,则将字典调整为json格式返回,并设置响应类型为json 
				return resp 
			else:
				resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				#app['__templating__'] = env jinja环境
				#存在对应模板的,则将套用模板,用request handler的结果r进行渲染
				resp.content_type = 'text/html;charset=utf-8'
				return resp 
		if isinstance(r, int) and r >= 100 and r < 600:
			return web.Response(r)
		#响应结果为整型,此时r为状态码,即404,500等

		if isinstance(r, tuple) and len(r) == 2: #若响应结果为元组,并且长度为2
			t, m = r 
			# 将r元组的两个元素赋给t和m
			# t为http状态码,m为错误描述
			# 判断t是否满足100~600的条件
			if isinstance(t, int) and t >= 100 and t < 600:
				return web.Response(t, str(m))
				# 返回状态码与错误描述
		# default：
		resp = web.Response(body=str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp 
		# 默认以字符串形式返回响应结果,设置类型为普通文本
	return response

# 时间过滤器
def datetime_filter(t):
	delta = int(time.time() - t) 
	# delta => 秒数
	if delta < 60: # 一分
		return u'1分钟前'
	if delta < 3600: # 一小时
		return u'%s分钟前' % (delta // 60)
	if delta < 86400: # 一天
		return u'%s小时前' % (delta // 3600)
	if delta < 604800: # 一周
		return u'%s天前' % (delta // 86400)
	dt = datetime.fromtimestamp(t)
	return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)
	# 通过jinja2的filter（过滤器），把一个浮点数转换成日期字符串



# 初始化协程
# 把一个generator标记为coroutine类型，然后扔到EventLoop中执行:
async def init(loop):
	await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='www-data', password='www-data', db='awesome')
	# 创建全局数据库连接池
	app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
	# 创建web应用对象,循环类型是消息循环
	init_jinja2(app, filters=dict(datetime=datetime_filter))
	# 设置模板为jiaja2, 并以时间为过滤器
	# init_jinja2(app, **kw)
	'''
	filters={'datetime':datetime_filter}
	filters = kw.get('filters', None) => {'datetime':datetime_filter}
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f
	app['__templating__'] = env 
	'''
	add_routes(app, 'handlers')
	# 将handlers模块的url处理函数注册
	# 最终执行到app.router.add_route(method, path, RequestHandler(app, fn))
	add_static(app) # 将本文件同目录下的static目录(即www/static/)加入到应用的路由管理器中
	srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9004)
	# make_handler()--Creates HTTP protocol factory for handling requests.
	# 调用子协程:创建一个TCP服务器,绑定到"127.0.0.1:9000"socket,并返回一个服务器对象
	# 127.0.0.1为本机地址 端口可以是9000,9001...；进行监听
	logging.info('server started at http://127.0.0.1:9004...')
	return srv #持续监听

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()