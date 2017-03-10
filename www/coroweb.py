__author__ = 'ggn'

# 'web 框架'

import asyncio, os, inspect, logging, functools
#functools 高阶函数模块, 提供常用的高阶函数, 如wraps
from urllib import parse
# 从urllib导入解析模块
from aiohttp import web

from apis import APIError
# 导入自定义的api错误模块
# 把一个函数映射为一个URL处理函数
def get(path): 
	'''
	Define decorator @get('/path')
	@get('/path')
	def now()
	now = get('/path')(now)
	执行now(*args, **kw)
	now(*args, **kw) = get('/path')(now)()= 
	decorator(now)(*args, **kw)=wrapper(*args, **kw)
	=func(*args, **kw)=装饰后的now(*args, **kw)
	'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET' #定义wrapper函数后定义其属性
		wrapper.__route__ = path
		return wrapper
	return decorator
# 一个函数通过@get()的装饰就附带了URL信息
# 定义了一个装饰器
# 将一个函数【映射(装饰)为一个URL处理函数】
def post(path):
	'''
	Define decorator @post('/path')
	'''
	def decorator(func):    #为函数func装饰
		@functools.wraps(func) 
		# 该装饰器的作用是解决一些函数签名的问题
        # 比如若没有该装饰器,wrapper.__name__将为"wrapper"
        # 加了装饰器,wrapper.__name__就等于func.__name__
		# 把原始函数的__name__等属性复制到wrapper()函数中，否则，有些依赖函数签名的代码执行就会出错。
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		# 通过装饰器加上__method__属性,用于表示http method
		wrapper.__route__ = path
		# 通过装饰器加上__route__属性,用于表示path
		return wrapper
	return decorator

def get_required_kw_args(fn):
	# 如果要限制关键字参数的名字，就可以用命名关键字参数
	# 获取无默认值的命名关键字参数名
	args = []
	params = inspect.signature(fn).parameters
	'''
inspect.signature（fn)将返回一个inspect.Signature类型的对象，值为fn这个函数的所有参数
inspect.Signature对象的paramerters属性是一个mappingproxy（映射）类型的对象，值为一个有序字典（Orderdict)。
这个字典里的key是即为参数名，str类型这个字典里的value是一个inspect.Parameter类型的对象，根据我的理解，这个对象里包含的一个参数的各种信息
inspect.Parameter对象的kind属性是一个_ParameterKind枚举类型的对象，值为这个参数的类型（可变参数，关键词参数，etc）
inspect.Parameter对象的default属性：如果这个参数有默认值，即返回这个默认值，如果没有，返回一个inspect._empty类。
# 获得函数fn的全部参数
    # inspect.signature: return a signature object for the given callable(fn or cls..)
    # a signature(签名,特征值) object represents the call signature of a function and it return annotation(注释).
    # 即一个signature对象表示一个函数或方法的调用签名,我们说两个函数的函数名,参数完全一样的,他们就是一个函数,大概call signature(调用签名)就是指这些吧
    # signature.parameters属性,返回一个参数名的有序映射
	'''
	#params为与参数相关的字典
	for name, param in params.items(): #key, value
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)
			#获取参数名，要求参数类型为KEYWORD_ONLY（命名关键字）且没有默认值
	return tuple(args) #变成tuple
	# 警告！此处return多打了个tab，导致后续严重错误，已改正。

def get_named_kw_args(fn): # 获取命名关键字参数名
	#named_kw_args 命名 关键字 参数
	args = []
	params = inspect.signature(fn).parameters		
	for name, param in params.items():  #key, value
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
		# KEYWORD_ONLY, 表示命名关键字参数.
        # 因此下面的操作就是获得命名关键字参数名
			args.append(name)
	return tuple(args) #变成tuple
	# 警告！此处return多打了个tab，导致后续严重错误，已改正。

def has_named_kw_args(fn): # 判断函数fn是否带有命名关键字参数
	params = inspect.signature(fn).parameters 
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

def has_var_kw_arg(fn): # 判断函数fn是否带有(变长)关键字参数
	params = inspect.signature(fn).parameters 
	for name, param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			# VAR_KEYWORD, 表示关键字参数, 匹配**kw
			return True

def has_request_arg(fn): # 函数fn是否有请求关键字
	sig = inspect.signature(fn) 
	#inspect.signature（fn)将返回一个inspect.Signature类型的对象，值为fn这个函数的所有参数
	params = sig.parameters 
	found = False
	for name, param in params.items():
		#对每组key-value(name, param)扫描
		if name == 'request':
			found = True
			continue
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
		# 函数的参数不是可变参数、命名关键字参数和关键字参数
		# VAR_POSITIONAL,表示可选参数,匹配*args
			raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
			# 若已经找到"request"关键字,但其不是函数的最后一个参数,将报错
        	# 大概类似于fn(xx, xx, *args, xx, **kw),request若不位于可变参数、命名关键字参数和关键字参数中则位于前面，不是最后一个命名参数
        	# 参数定义的顺序必须是：必选参数（位置参数）、默认参数、可变参数、命名关键字参数和关键字参数。
        	# request参数必须是最后一个命名参数
	return found

# 定义RequestHandler类,【封装】url处理函数,即handler=>fn,如handles.py中定义的index(request)
# RequestHandler的目的是从url函数中分析需要提取的参数,从request中获取必要的参数
# 调用url函数,将结果转换为web.response
class RequestHandler(object):
	def __init__(self, app, fn):
		#实例属性
		# _xx--“虽然我可以被访问，但是，请把我视为私有变量，不要随意访问”:
		self._app = app # web application
		self._func = fn # handler
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		# 获取命名关键字参数名：
		self._named_kw_args = get_named_kw_args(fn)
		# 获取无默认值的命名关键字参数名：
		self._required_kw_args = get_required_kw_args(fn) 

	async def __call__(self, request): # RequestHandler(app, fn)(request),如此调用时执行
		# 定义了__call__,则其实例可以被视为函数
    	# 此处参数为request
    	# request参数为aiohttp.web.Request类的实例（aiohttp.web已导入）
    	# You should never create the Request instance manually – aiohttp.web does it for you. 
    	# request参数根据url自动生成
    	# 具有Request类中定义的方法及其父类BaseRequest中定义的方法
		# http://aiohttp.readthedocs.io/en/stable/web_reference.html#aiohttp.web.Request
		# http://aiohttp.readthedocs.io/en/stable/_modules/aiohttp/web_reqrep.html#BaseRequest
		kw = None # 设不存在关键字参数
		if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
			# 存在关键字参数/命名关键字参数
			if request.method == 'POST':
				if not request.content_type:
					# 父类BaseRequest中定义的方法
					return web.HTTPBadRequest('Missing Content-Type')
					# http method 为post, 但request的content type为空, 返回丢失信息
				ct = request.content_type.lower() # 获得content type字段
				# lower() 返回将字符串中所有大写字符转换为小写后生成的字符串。
				# 以下为检查post请求的content type字段
                # application/json表示消息主体是序列化后的json字符串
				if ct.startswith('application/json'):
					params = await request.json()
					# 父类BaseRequest中定义的方法
					# request.json方法的作用是读取request body, 并以json格式解码
					if not isinstance(params, dict):
						return HTTPBadRequest('JSON must be object.')
						# 解码得到的参数不是字典类型, 返回提示信息
					kw = params # post, content type字段指定的消息主体是json字符串,且解码得到参数为字典类型的,将其赋给变量kw
				# 以下2种content type都表示消息主体是表单:
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params = await request.post()
					# 把@asyncio.coroutine替换为async,把yield from替换为await。
					# yield from/await语法可以让我们方便地调用另一个generator
					# 一边循环一边计算的机制，称为生成器：generator.
					# 在for循环的过程中不断计算出下一个元素，并在适当的条件结束for循环
					# 变成generator的函数，在每次调用next()的时候执行，遇到yield语句返回，再次执行时从上次返回的yield语句处继续执行。
					kw = dict(**params)
					# request.post方法从request body读取POST参数,即表单信息,并包装成字典赋给kw变量
					# **params表示把params这个dict的所有key-value用关键字参数传入到函数的**kw参数，kw将获得一个dict，注意kw获得的dict是params的一份拷贝，对kw的改动不会影响到函数外的params。
				else:
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
					# 此处我们只处理以上三种post 提交数据方式
			if request.method == 'GET':
				# 方法：GET还是POST，GET仅请求资源，POST会附带用户数据
				qs = request.query_string 
				# request.query_string表示url中的查询字符串
				# 比如"https://www.google.com/#newwindow=1&q=google",最后的q=google就是query_string
				if qs:
					kw = dict() # 原来为None的kw变成字典
					for k, v in parse.parse_qs(qs, True).items():
						# dict通过items函数转换为[(k1,v1),(k2,v2)]这种形式，才能用for k, v in来循环
						# dict.items()结果是一个列表，列表的每一个值都是一个包含两个元素的元组
						# for遍历的是一个元组对象，k和v是元组里的参数。所以(k,v)是一个整体，一次取两个数分别给k和v
						kw[k] = v[0] # 猜测value是一个list或tuple
					# 解析query_string,以字典的形式储存到kw变量中
		if kw is None:
			kw = dict(**request.match_info)
			# match_info:Read-only property with AbstractMatchInfo instance for result of route resolving.
		else:
			if not self._has_var_kw_arg and self._named_kw_args:
				# remove all unamed kw:
				# kw 不为空,且requesthandler没有变长关键字参数只存在命名关键字的,则只取命名关键字参数名放入kw
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy 
			# check named arg:
			for k, v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicated arg name in named arg and kw args: %s' % k)
				# 遍历request.match_info, 若其key又存在于kw中,发出重复参数警告
				kw[k] = v 
		if self._has_request_arg:
			kw['request'] = request  # 若存在"request"关键字, 则添加
		# check required kw:
		if self._required_kw_args:
			# 存在无默认值的命名关键字参数
			# 命名关键字参数可以有缺省值/默认值，调用时，可不传入该参数
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest('Missing argument: %s' % name)
					# 前面self._named_kw_args中copy过了，这里用子集self._required_kw_args再检查一遍
		logging.info('call with args: %s' % str(kw))
		

		# 以上通过request.json()/request.post()/request.query_string/request.match_info从request中获得必要的参数

		
		# 以下调用handler处理,并返回response:
		
		try:
			r = await self._func(**kw) # yield调用生成器(函数fn)
			return r
		except APIError as e:
			return dict(error=e.error, data=e.data, message=e.message)
			# 当错误发生时，后续语句不会被执行，except若捕获到APIError（已导入），则被执行。
			# 若错误（是一种类or实例，本身带有信息如error,data,message）符合APIError类的定义，则判定属于APIError，捕获到APIError

def add_static(app):
	'''比方C盘ABC文件夹有个1文件,还有一个DEF文件夹,而DEF文件下有个2文件.
	那1和2的文件路径分别为:(都是绝对路径)
	C:\ABC\1
	C:\ABC\DEF\2
	如果让1文件来表示2文件的路径
	绝对路径: C:\ABC\DEF\2
	相对路径: DEF\2 (因为1和2文件前面的C:\ABC这段路径相同就不用写出来了)。
	'''
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	app.router.add_static('/static/', path)
	# http://aiohttp.readthedocs.io/en/stable/web_reference.html#aiohttp.web.Application
	logging.info('add static: %s => %s' % ('/static/', path))
	# os.path.abspath(__file__), 返回当前脚本的绝对路径(包括文件名)
    # os.path.dirname(), 去掉文件名,返回目录路径
    # os.path.join(), 将分离的各部分组合成一个路径名
    # 因此以下操作就是将本文件同目录下的static目录(即www/static/)加入到应用的路由管理器中 
    # app:An Application( aiohttp.web.Application) instance used to call request handler, Read-only property
    # http://aiohttp.readthedocs.io/en/stable/web_reference.html#aiohttp.web.Request

# 编写一个add_route函数，用来注册一个URL处理函数fn(经由RequestHandler(app, fn)封装),如index(request)：
# 将处理函数注册fn到app上
# 处理将针对http method 和path进行
def add_route(app, fn):
	# add_route不等于app.router.add_route
	method = getattr(fn, '__method__', None) # 获取fn.__method__属性,若不存在将返回None
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
		# r = await self._func(**kw) 要求fn是协程或生成器
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
	# inspect.Signature对象的paramerters属性是一个mappingproxy（映射）类型的对象，值为一个有序字典（Orderdict)。这个字典里的key是即为参数名
	app.router.add_route(method, path, RequestHandler(app, fn))
	# 注册request handler
	# RequestHandler(app, fn)是一个实例，可被视为函数，属性__call__的参数request由aiohttp.web（根据fn？）自动生成
	# handler = RequestHandler(app, fn)
	# http://aiohttp.readthedocs.io/en/stable/web_reference.html#aiohttp.web.Application

# 自动注册所有请求处理函数,如
def add_routes(app, module_name):
	# 自动把module_name模块的所有符合条件的函数注册了
	n = module_name.rfind('.')
	# 返回字符串最后一次出现的位置，如果没有匹配项则返回-1。
	# n记录模块名中最后一个.的位置
	if n== (-1):
		# -1 表示未找到,即module_name表示的模块直接导入,如xx
		mod = __import__(module_name, globals(), locals())
		# __import__()的作用同import语句,python官网说强烈不建议这么做
        # __import__(name, globals=None, locals=None, fromlist=(), level=0)
        # name -- 模块名
        # globals, locals -- determine how to interpret the name in package context
        # fromlist -- name表示的模块的子模块或对象名列表
        # level -- 绝对导入还是相对导入,默认值为0, 即使用绝对导入,正数值表示相对导入时,导入目录的父目录的层数
	else:
		name = module_name[n+1:] #.后面的字符串赋给name,如xx.yy, name = yy
		mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
		#__import__在别处定义，name是个字符串，mod为模板名
		# 先用__import__表达式导入模块以及子模块
		# __import__(name, globals=None, locals=None, fromlist=(), level=0) => __import__(xx, globals(), locals(), [yy])
        # 再通过getattr()方法取得子模块名, 如mod = datetime.datetime, mod = xx.yy
	for attr in dir(mod):
		# 举个例子，经过以上处理，mod = datetime 或 mod = datetime.datetime
		# dir()不带参数时，返回当前范围内的变量、方法和定义的类型列表
		# 带参数时，返回参数的属性、方法列表。如果参数包含方法__dir__()，该方法将被调用。如果参数不包含__dir__()，该方法将最大限度地收集参数信息。
		if attr.startswith('_'):
			continue # 作用为跳出for循环，即以_开头的属性与方法不进行for循环
		# _xx或__xx指示方法或属性为私有的,__xx__指示为特殊变量
        # 私有的,能引用(python并不存在真正私有),但不应引用;特殊的,可以直接应用,但一般有特殊用途
		fn = getattr(mod, attr) 
		# 得到属性对应值
		# 获得模块的属性或方法, 如datetime.datetime.now 
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			# 获取fn的__method__属性与__route__属性，获得http method与path信息
            # 此脚本开头的@get与@post装饰器就为fn加上了__method__与__route__
			if method and path:
				add_route(app, fn)
				# 注册request handler, handler = RequestHandler(app, fn)
				# app.router.add_route(method, path, RequestHandler(app, fn))
