__author__ = 'ggn'

'''JSON API definition'''

import json, logging, inspect, functools
'''
inspect: the module provides several useful functions to help get information about live objects, such as modules, classes, methods, functions.
functools: 该模块提供有用的高阶函数.总的来说,任何callable对象都可视为函数
'''

class Page(object): # page对象,用于储存分页信息
	'''
	Page object for display ages.
	'''
	def __init__(self, item_count, page_index=1, page_size=10): # page_index, page_size使用默认参数
		'''
		item_count - 博客总数  page_index - 页码 
		page_size - 每页最多显示博客数
		Init Pagination(页码标注) by item_count, page_index and page_size.
		>>> p1 = Page(100, 1)
		>>> p1.page_count
		10
		>>> p1.offset
		0
		>>> p1.limit
		10
		>>> p2 = Page(90, 9, 10)
		>>> p2.page_count
		9
		>>> p2.offset
		80
		>>> p2.limit
		10
		>>> p3 = Page(91, 10, 10)
		>>> p3.page_count
		10
		>>> p3.offset
		90
		>>> p3.limit
		10	
		'''
		self.item_count = item_count # 从数据库中查询博客的总数获得
		self.page_size = page_size
		self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
		#  博客总数除以每页最多显示博客数并加上余数，计算博客页数
		if (item_count == 0) or (page_index > self.page_count):
			# 没有博客,或页码超出
			self.offset = 0
			self.limit = 0
			self.page_index = 1 # 页码设置为1
		else:
			#  有博客,且指定页码并未超出页面总数的
			self.page_index = page_index # 页码置为指定的页码
			self.offset = self.page_size * (page_index - 1) # 设置页面偏移量，到前一页的博客总数
			self.limit = self.page_size # 页面的博客限制数与页面大小一致
		self.has_next = self.page_index < self.page_count # 页码小于页面总数,说有有下页
		self.has_previous = self.page_index > 1 # 若页码大于1,说明有前页

	def __str__(self):
		return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)
		# 总博客数 总页数 当前页数 每页博客数 偏移量(到前一页的博客总数) 每页限制博客数
	__repr__ = __str__






class APIError(Exception):
	'''
	the base APIError which contains error(required), data(optional) and message(optional).
	'''
	def __init__(self, error, data='', message=''):
		super(APIError, self).__init__(message)
		self.error = error
		self.data = data
		self.message = message

class APIValueError(APIError):
	'''
	Indicate the input value has error or invalid. The data specifies 指定，详细说明 the error field of input form.
	定义APIValueError类
    表明输入的值错误或不合法.
    data属性指定为输入表单的错误域
	'''
	def __init__(self, field, message=''):
		super(APIValueError, self).__init__('value:invalid', field, message)

class APIResourceNotFoundError(APIError):
	'''
	Indicate the resource was not found. The data specifies the resource name.
	定义APIResourceNotFoundError类
    表明找不到指定资源.
    data属性指定为资源名
	'''
	def __init__(self, field, message=''):
		super(APIResourceNotFoundError, self).__init('value:notfound', field, message)

class APIPermissionError(APIError):
	'''
	Indicate the api has no permission.
	'''
	def __init__(self, message=''):
		super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)