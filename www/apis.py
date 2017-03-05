__author__ = 'ggn'

'''JSON API definition'''

import json, logging, inspect, functools
'''
inspect: the module provides several useful functions to help get information about live objects, such as modules, classes, methods, functions.
functools: 该模块提供有用的高阶函数.总的来说,任何callable对象都可视为函数
'''

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