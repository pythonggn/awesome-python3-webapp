'''
应用程序读取配置文件需要优先从config_override.py读取。
为了简化读取配置文件，可以把所有配置读取到统一的config.py中：
'''

__author__ = 'ggn'

import config_default

class Dict(dict):
	'''
	Simple dict but support access as x.y style.
	'''
	def __init__(self, names=(), values=(), **kw):
		'''
        initial funcion.
        names: key in dict
        values: value in dict
        '''
		super(Dict, self).__init__(**kw)
		for k, v in zip(names, values):
			# zip函数接受任意多个（包括0个和1个）序列作为参数，返回一个tuple列表。
			# 返回[(names1,names2...), (values1,value2...)]
			self[k] = v #　self[names] = values

	def __getattr__(self, key): # 定义描述符,方便通过点标记法取值,即a.b
		# 执行a.b时在此处查找属性
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Dict' object has no attribute %s" % key)

	def __setattr__(self, key, value):  # 定义描述符,方便通过点标记法设值,即a.b=c
		## 执行a.b=c时在此处设置属性
		self[key] = value 

def merge(defaults, override):
	r = {}
	# 创建新的字典，拷贝配置文件进行融合,而不对原配置文件做修改
	for k, v in defaults.items():
		if k in override:
			if isinstance(v, dict):
				r[k] = merge(v, override[k])
			else:
				r[k] = override[k]
			# 优先用override覆盖
		else:
			r[k] = v
			# override没有的不用覆盖
	return r

def toDict(d):
	# 拷贝字典并转化为新类型Dict
	D = Dict()
	for k, v in d.items():
		D[k] = toDict(v) if isinstance(v, dict) else v
	return D
	# d = {'a': 1}   
	# d = {'a': {'b': 2}} => D[a] = toDict({'b': 2}) => return {'b': 2} => return {'a': {'b': 2}}

configs = config_default.configs

try:
	import config_override
	configs = merge(configs, config_override.configs) 
	# 覆盖后拷贝到新字典中
except ImportError:
	pass

configs = toDict(configs)
# 将拷贝混合好的配置字典转换成自定义Dict字典类型,方便取值与设值