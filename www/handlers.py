__author__ = 'ggn'

# url处理函数
' url handlers '
import re, time, json, logging, hashlib, base64, asyncio

from models import User, Comment, Blog, next_id
 # Web App需要的3个表, User, Blog, Comment, 类到表的映射

from coroweb import get, post 
# 导入装饰器,这样就能很方便的生成request handler

# 此处所列所有的handler都会在app.py中通过add_routes自动注册到app.router上
# 因此,在此脚本尽情地书写request handle即可
# 在此处定义的函数即为url处理函数fn，通过handler = RequestHandler(app, fn)
# app.router.add_route(method, path, RequestHandler(app, fn))进行注册

# 通过Web框架的@get和ORM框架的Model支持，可以很容易地编写一个【处理首页URL的函数】：
# 对于首页的get请求的处理
@get('/') # 装饰上路径和方法，'/'表示主页
# @get 把一个函数映射为一个URL处理函数
# 一个函数通过@get()的装饰就附带了URL信息


def index(request):
	# summary用于在博客首页上显示的句子
	summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	# 这里只是手动写了blogs的list, 并没有真的将其存入数据库
	blogs = [
		Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
		Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
		Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
	]
	return {
		'__template__': 'blogs.html',
		'blogs': blogs
	}


# 用户信息接口,用于返回机器能识别的用户信息
@get('/api/users')
async def api_get_users():
	users = await User.findAll(orderBy='created_at desc') 
	#orderBy='created_at desc' 刚开始加上这句话会报错,原因是orm.py中sql.append('orderBy')语句错误，正确应为sql.append('order by'),已改正。
	for u in users:
		u.password = '******'
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




'''
def handler(request):
    return web.Response()
'''
	# 返回一个字典, 其指示了使用何种模板,模板的内容
	# app.py的response_factory将会对handler的返回值进行分类处理


	# '__template__'指定的模板文件是test.html，其他参数是传递给模板的数据
	# 我们在模板的根目录templates下创建test.html
	# 渲染模板,test.html见templates文件夹中

