__author__ = 'ggn'

# url处理函数
' url handlers '
import re, time, json, logging, hashlib, base64, asyncio

import markdown2
# Markdown是一个轻文本标记语言，它允许你在写的时候使用简单文本格式，然后转换为XHTML（HTML）。
# Python-markdown2是完全用Python实现的Markdown，与用Perl实现的 Markdown.pl非常接近，同时增加了一些扩展，包括语法高亮等。

from models import User, Comment, Blog, next_id
# Web App需要的3个表, User, Blog, Comment, 类到表的映射

from aiohttp import web 

from coroweb import get, post 
# 导入装饰器,这样就能很方便的生成request handler
from apis import Page, APIValueError, APIResourceNotFoundError, APIPermissionError
from config import configs # 配置

# 此处所列所有的handler都会在app.py中通过add_routes自动注册到app.router上
# 因此,在此脚本尽情地书写request handle即可
# 在此处定义的函数即为url处理函数fn，通过handler = RequestHandler(app, fn)
# app.router.add_route(method, path, RequestHandler(app, fn))进行注册

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret # config_default.py

def check_admin(request): # 验证用户身份
	# 检查用户是否管理员
	# 对于已登录的用户,检查其admin属性. 管理员的admin为真
	if request.__user__ is None or not request.__user__.admin:  
		raise APIPermissionError()
	# models.py--admin = BooleanField()
	# orm.py--BooleanField() default=False
	'''
	报错：'Request' object has no attribute '__user__'，解决方法：
	app.py中：from handlers import cookie2user, COOKIE_NAME,
	app.py中定义auth_factory(app, handler),  middlewares=[logger_factory, auth_factory, response_factory]
	本py导入 APIPermissionError，
	
	'''

def get_page_index(page_str): # 取得页码
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p 
	# 将传入的字符串转为页码信息, 实际只是对传入的字符串做了合法性检查
	# 页码不合法时跳转到第一页


# 通过用户信息计算加密cookie:
def user2cookie(user, max_age):
	'''
	Generate cookie str by user.
	'''
	# build cookie string by: id-expires(到期)-sha1
	expires = str(int(time.time() + max_age))
	# expires(失效时间)是当前时间加上cookie最大存活时间的字符串
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	# "用户id" + "过期时间" + SHA1("用户id" + "用户口令" + "过期时间" + "SecretKey")
	# 服务器可以拿到的信息包括：用户id 过期时间 SHA1值
	return '-'.join(L)

def text2html(text): # 文本转html
	lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
	# filter()函数接收一个函数 f 和一个list，这个函数 f 的作用是对每个元素进行判断，返回 True或 False，filter()根据判断结果自动过滤掉不符合条件的元素，返回由符合条件元素组成的新list。
	# 识别文本的\n换行，返回去掉换行后的字符串list及原每行的字符串，通过lambda判断并用filter()过滤掉空字符串/原空行，返回字符串list
	# replace(old，new) 用new替换old，对filter()返回的字符串list(原每行字符串组成)中每个元素进行替换，返回HTML格式的字符串，即使原每行字符串符合HTML格式
	# lines返回由HTML格式的段落（由原文本的每行转换）list
	return ''.join(lines) # '<p>原第1行</p><p>原第2行</p>...'


# 解密cookie:
@asyncio.coroutine
def cookie2user(cookie_str):
	'''
	Parse cookie and load user if cookie is valid.
	'''
	if not cookie_str: 
		# cookie_str = request.cookies.get(COOKIE_NAME)
		# cookie_str就是user2cookie函数的返回值？
		return None
	try:
		L = cookie_str.split('-')
		# 返回一个字符串中的所有单词的列表，使用'-'作为分隔符
		# 通过'-'拆分cookie,得到用户id,失效时间,以及加密字符串
		if len(L) != 3:
			return None
		uid, expires, sha1 = L 
		# uid, expires, sha1 = L[xx,xx,xx]
		if int(expires) < time.time():
			return None
			# 时间是浮点表示的时间戳,一直在增大.因此失效时间小于当前时间,说明cookie已失效
		user = yield from User.find(uid) # 由拆分得到的id在数据库中查找用户信息
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		#  利用用户id,加密后的密码,失效时间,加上cookie密钥,组合成待加密的原始字符串
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			# 再对其进行加密,与从cookie分解得到的sha1进行比较.若相等,则该cookie合法
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		return user 
	except Exception as e:
		logging.exception(e)
		return None

# 通过Web框架的@get和ORM框架的Model支持，可以很容易地编写一个【处理首页URL的函数】：
# 对于首页的get请求的处理
@get('/') # 装饰上路径和方法，'/'表示主页
# @get 把一个函数映射为一个URL处理函数
# 一个函数通过@get()的装饰就附带了URL信息
@asyncio.coroutine
def index(*, page='1'):
	# summary用于在博客首页上显示的句子
	summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	page_index = get_page_index(page) # 取得页码
	num = yield from Blog.findNumber('count(id)')
	page = Page(num) # 创建实例，博客总数为num，页码为1，每页最多显示博客数为10
	if num == 0:
		blogs = []
	else:
		blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))	
	return {
		'__template__': 'blogs.html',
		'page': page,
		'blogs': blogs # 参数blogs将在jinja2模板中被解析
	}

@get('/blog/{id}')
@asyncio.coroutine
def get_blog(id): # 按id查找显示博客
	blog = yield from Blog.find(id) # 从数据库中获取博客
	comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
	# 评论按博客id查找，按创建时间降序排列
	for c in comments:
		c.html_content = text2html(c.content) # 将评论转换为HTML格式内容
	blog.html_content = markdown2.markdown(blog.content) # 将博客从markdown格式转换为HTML格式内容
	return {
		'__template__': 'blog.html', 
		'blog': blog,
		'comments': comments
		# 返回的参数将在jinja2模板中被解析
	}


@get('/register') # 返回注册页面
def register():
	return {
		'__template__': 'register.html'
	}

@get('/signin') # 返回登录页面
def signin():
	return {
	'__template__': 'signin.html'
	}

# 用户信息接口,用于返回机器能识别的用户信息
@get('/api/users')
async def api_get_users():
	users = await User.findAll(orderBy='created_at desc') 
	#orderBy='created_at desc' 刚开始加上这句话会报错,原因是orm.py中sql.append('orderBy')语句错误，正确应为sql.append('order by'),已改正。
	for u in users:
		u.password = '******' # 重新赋值'******'，防止密码显示被看见
	return dict(users=users)
	# 以dict形式返回,并且未指定__template__,将被app.py的response factory处理为json

'''
@get('/api/users')
def api_get_users(*, page='1'):
	page_index = get_page_index(page)
	num = yield from User.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	for u in users():
		u.password = '******'
	return dict(page=p, users=users)
	# 只要返回一个dict，后续的response这个middleware就可以把结果序列化为JSON并返回。
'''

# 先通过API把用户注册这个功能实现
'''
正则表达式
用\d可以匹配一个数字，\w可以匹配一个字母或数字
.可以匹配任意字符
*表示任意个字符（包括0个），用+表示至少一个字符，用?表示0个或1个字符，
用{n}表示n个字符，用{n,m}表示n-m个字符
\s可以匹配一个空格（也包括Tab等空白符），所以\s+表示至少有一个空格，例如匹配' '，' '等
'-'是特殊字符，在正则表达式中，要用'\'转义，\-

\d{3}表示匹配3个数字，例如'010'；
\s可以匹配一个空格（也包括Tab等空白符），所以\s+表示至少有一个空格，例如匹配' '，' '等；
\d{3,8}表示3-8个数字，例如'1234567'。
如果要匹配'010-12345'这样的号码呢？由于'-'是特殊字符，在正则表达式中，要用'\'转义，所以，上面的正则是\d{3}\-\d{3,8}。

[]表示范围:
[0-9a-zA-Z\_]可以匹配一个数字、字母或者下划线；
[0-9a-zA-Z\_]+可以匹配至少由一个数字、字母或者下划线组成的字符串，比如'a100'，'0_Z'，'Py3000'等等；
[a-zA-Z\_][0-9a-zA-Z\_]*可以匹配由字母或下划线开头，后接任意个由一个数字、字母或者下划线组成的字符串，也就是Python合法的变量；
[a-zA-Z\_][0-9a-zA-Z\_]{0, 19}更精确地限制了变量的长度是1-20个字符（前面1个字符+后面最多19个字符）。

A|B可以匹配A或B，所以(P|p)ython可以匹配'Python'或者'python'。
^表示行的开头，^\d表示必须以数字开头。
$表示行的结束，\d$表示必须以数字结束。

使用Python的r前缀，不用考虑转义的问题

Python提供re模块，包含所有正则表达式的功能

'''
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
# re.compile 把正则表达式编译成一个正则表达式对象
# 【至少一个小写字母数字.-_ 】【@】【至少一个小写字母数字-_ 】【(1~4位.小写字母数字-_]+) 组】
# aaa103.b-z_f@163.com
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')
# 小写字母a~f或(及)数字组成的40位字符串

# 匹配邮箱与加密后密码的正则表达式

@post('/api/users')
# 实现用户注册的api,注册到/api/users路径上,http method为post
# 猜测：get('/register')，register()返回注册页面register.html，之后通过交互点击提交按钮之类的，调用post('/api/users')，api_register_user(*, email, name, passwd)提交注册信息，实现用户注册

async def api_register_user(*, email, name, passwd):
	# 命名关键字参数，限制关键字参数的传入
	if not name or not name.strip(): # strip() 方法用于移除字符串头尾指定的字符（默认为空格）
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email): # 传入的email参数不匹配正则表达式
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd): # 传入的passwd参数不匹配正则表达式
		raise APIValueError('password')
	users = await User.findAll('email=?', [email])
	# 'select `%s`, %s from `%s`', 'where', email=?'  [email]  见orm.py
	# 按邮箱查找用户,返回一个字典
	if len(users) > 0:
		# 根据邮箱能够查找到用户，该邮箱已被使用
		raise APIError('register:failed', 'email', 'Email is already in use.')
		# __init__(self, error, data='', message='')
	uid = next_id() # 利用当前时间与随机生成的uuid生成user id
	sha1_passwd = '%s:%s' % (uid, passwd) # 'uid:passwd'
	user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
	
	'''
	# 创建用户对象, 其中密码并不是用户输入的密码,而是经过复杂处理后的保密字符串
    # unicode对象在进行哈希运算之前必须先编码
    # sha1(secure hash algorithm),是一种不可逆的安全算法.这在一定程度上保证了安全性,因为用户密码只有用户一个人知道
    # hexdigest()函数将hash对象转换成16进制表示的字符串
    # md5是另一种安全算法
    # Gravatar(Globally Recognized Avatar)是一项用于提供在全球范围内使用的头像服务。只要在Gravatar的服务器上上传了你自己的头像，便可以在其他任何支持Gravatar的博客、论坛等地方使用它。此处image就是一个根据用户email生成的头像
	Python的hashlib提供了常见的摘要算法，如MD5，SHA1等等。它通过一个函数，把任意长度的数据转换为一个长度固定的数据串（通常用16进制的字符串表示）.
	hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest() 计算出sha1_passwd字符串的sha1值
	用户口令是客户端传递的经过SHA1计算后的40位Hash字符串，所以服务器端并不知道用户的原始口令。
	hashlib.md5(email.encode('utf-8')).hexdigest() 计算出email字符串的MD5值
	http://www.gravatar.com/  个人全球统一标识,制作头像
	'''
	await user.save()
	# 将用户信息储存到数据库中,save()方法封装的实际是数据库的insert操作
	# make session cookie: 创建会话跟踪
	r = web.Response() # 返回的response是带有cookie的响应
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	'''
	# 刚创建的的用户设置cookie(网站为了辨别用户身份而储存在用户本地终端的数据)
    # http协议是一种无状态的协议,即服务器并不知道用户上一次做了什么.
    # 因此服务器可以通过设置或读取Cookies中包含信息,借此维护用户跟服务器会话中的状态
    # user2cookie设置的是cookie的值
    # max_age是cookie的最大存活周期,单位是秒.当时间结束时,客户端将抛弃该cookie.之后需要重新登录
	'''
	user.passwd = '******' # 修改密码的外部显示为*
	r.content_type = 'application/json' # 设置content_type,将在data_factory中间件中继续处理
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8') # json.dumps()方法返回一个str，内容就是标准的JSON
	return r
	# 经@post装饰的用于注册的url处理函数fn，经RequestHandler封装调用，从request中获取参数信息，返回json格式的response(coroweb.py)，由response_factory这个middleware处理成web.Response对象返回



'''
用户登录比用户注册复杂。由于HTTP协议是一种无状态协议，而服务器要跟踪用户状态，就只能通过cookie实现。大多数Web框架提供了Session功能来封装保存用户状态的cookie。
Session的优点是简单易用，可以直接从Session中取出用户登录信息。
Session的缺点是服务器需要在内存中维护一个映射表来存储用户登录信息，如果有两台以上服务器，就需要对Session做集群，因此，使用Session的Web App很难扩展。
采用直接读取cookie的方式来验证用户登录，每次用户访问任意URL，都会对cookie进行验证，这种方式的好处是保证服务器处理任意的URL都是无状态的，可以扩展到多台服务器。

'''
@post('/api/authenticate') # 用户登录的验证api
@asyncio.coroutine
def authenticate(*, email, passwd): # 通过邮箱与密码验证登录
	if not email:
		raise APIValueError('email', 'Invalid email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid passwd.')
	users = yield from User.findAll('email=?', [email])
	# 在数据库中查找email,将以list形式返回
	if len(users) == 0: # 查询结果为空,即数据库中没有相应的email记录,说明用户不存在
		raise APIValueError('email', 'Email not exist.')
	user = users[0]
	# check passwd:
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':') # 见api_register_user
	sha1.update(passwd.encode('utf-8'))
	'''
	# 数据库中存储的并非原始的用户密码,而是加密的字符串
    # 我们对此时用户输入的密码做相同的加密操作,将结果与数据库中储存的密码比较,来验证密码的正确性
    # 合成为一步就是:sha1 = hashlib.sha1((user.id+":"+passwd).encode("utf-8"))
    # 对照用户时对原始密码的操作(见api_register_user),操作完全一样
	'''
	if user.passwd != sha1.hexdigest(): 
	# 数据库中储存的用户passwd与根据用户输入的passwd计算出的摘要不匹配
		raise APIValueError('passwd', 'Invalid password.')
	# authenticate ok, set cookie:
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	# 用户登录之后,同样的设置一个cookie,与注册用户部分的代码完全一样
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
	logging.info('user signed out.')
	return r 

@get('/manage/blogs') # 管理博客的页面
def manage_blogs(*, page='1'):
	return {
		'__template__': 'manage_blogs.html',
		'page_index': get_page_index(page) #通过page_index来显示分页
	}

@get('/manage/blogs/create') # 识别路径
def manage_create_blog(): # 返回创建编辑博客页面
	return {
		'__template__': 'manage_blog_edit.html',
		'id': '',
		'action': '/api/blogs'
	}
	'''
	id的值将传给js变量I
	action的值也将传给js变量action
	在用户提交博客的时候,将数据post到action指定的路径,此处即为创建博客的api
	'''
@get('/api/blogs') # 数据都是通过API操作
@asyncio.coroutine
def api_blogs(*, page='1'):
	page_index = get_page_index(page) 
	# 将传入的字符串转为页码信息, 实际只是对传入的字符串做了合法性检查
	# 页码不合法时跳转到第一页
	num = yield from Blog.findNumber('count(id)')
	p = Page(num, page_index) # 博客总数 当前页数
	if num == 0: # 若博客数为0,返回字典,将被app.py的response middleware再处理
		return dict(page=p, blogs=())
	blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	# 降序，limit=(前页为止博客数，每页限制博客数),即显示当页博客。 SELECT * FROM table LIMIT 5,10;  检索记录行 6-15
	return dict(page=p, blogs=blogs) # 返回字典,将被app.py的response middleware处理



@get('/api/blogs/{id}') # API方式获取单条博客，机器处理的数据
@asyncio.coroutine
def api_get_blog(*, id):
	blog = yield from Blog.find(id)
	return blog 

@post('/api/blogs') # API: 创建blog
@asyncio.coroutine
def api_creat_blog(request, *, name, summary, content):
	check_admin(request) # 验证用户身份是否为管理员，不是则报错

	'''
	#设置管理员权限：windows系统，只要在cmd下用mysql命令给其中一个user的admin值更改为1就可以了：update users set admin=1 where name=某user
	或进入mysql输入use awesome;     UPDATE users SET admin=TRUE Where email='XXX@XX.COM';
	'''
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
	yield from blog.save()
	return blog