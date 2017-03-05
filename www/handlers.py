__author__ = 'ggn'

# url处理函数

import models # Web App需要的3个表, User, Blog, Comment, 类到表的映射

from coroweb import get, post 
# 导入装饰器,这样就能很方便的生成request handler
# 此处所列所有的handler都会在app.py中通过add_routes自动注册到app.router上
# 因此,在此脚本尽情地书写request handle即可
# 猜测：在此处定义的函数即为url处理函数fn，通过handler = RequestHandler(app, fn)
# app.router.add_route(method, path, RequestHandler(app, fn))进行注册

# 通过Web框架的@get和ORM框架的Model支持，可以很容易地编写一个处理首页URL的函数：
# 对于首页的get请求的处理
@get('/') # 装饰上路径和方法，'/'表示主页
async def index(request):
	users = await models.User.findAll()
	# 列出所有记录
	return {
		'__template__': 'test.html',
		'users': users
	}
	# '__template__'指定的模板文件是test.html，其他参数是传递给模板的数据
	# 我们在模板的根目录templates下创建test.html
	# 渲染模板,test.html见templates文件夹中

