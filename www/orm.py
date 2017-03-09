__author__ = 'ggn'

#在一个Web App中，所有数据，包括用户信息、发布的日志、评论等，都存储在数据库中。在awesome-python3-webapp中，我们选择MySQL作为数据库。
#只能一行行操作，不可能做成一下子输入整张表的语句
import asyncio, logging
import aiomysql

def log(sql, args=()):
	# 记录sql语句
	logging.info('SQL: %s' % sql)

#类、实例的变量即属性
#数据库中行叫记录==>映射类的实例,列叫字段==>映射类的属性/方法
#ORM技术：Object-Relational Mapping，把关系数据库的表结构映射到对象上,数据库表中添加一行记录，可以视为添加一个对象
#异步编程的一个原则：一旦决定使用异步，则系统每一层都必须是异步，“开弓没有回头箭”。
# 下面创建连接池, 每个HTTP请求都可以从连接池中直接获取数据库连接。使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
@asyncio.coroutine
def create_pool(loop, **kw):
	#**kw:关键字参数，任意个含参数名的参数
	logging.info('create database connection pool...') #打印
	global __pool  #定义全局变量,存储连接池，从中获取数据库连接
	#你在函数定义中声明的变量，他们与在函数外使用的其它同名变量没有任何关系，即变量名称对函数来说是局部的。
	#我们使用global语句，声明__pool是全局变量，当我们在函数内给__pool赋值时，它的改变映射到我们在主块中使用的__pool的值。没有global语句赋值给一个在函数外定义的变量是不可能的。

	__pool = yield from aiomysql.create_pool(
		host=kw.get('host', 'localhost'),  
		#kw.get(): get() 函数返回字典中指定键的值，如果值'host'不在字典kw中则返回'localhost'。避免key不存在的错误。
		#字典dict例子：d = {'Michael': 95, 'Bob': 75, 'Tracy': 85}
		#**kw关键字参数在函数内部自动组装为dict，如参数city='Beijing'--->字典{'city': 'Beijing'}
		port=kw.get('port', 3306),
		#'port'不在字典中则返回3306。避免key不存在的错误
		user=kw['user'],
		password=kw['password'],
		db=kw['db'],
		charset=kw.get('charset','utf8'),
		autocommit=kw.get('autocommit', True),
		maxsize=kw.get('maxsize', 10),
		minsize=kw.get('minsize',  1),
		loop=loop
	)


#下面定义select函数，用于执行select语句 (封装select语句)
@asyncio.coroutine
def select(sql, args, size=None):
#传入:sql--sql语句和;args--sql参数,要搜索的参数；size：指定数量,是个默认参数，默认为none
	log(sql, args) #记录or输出信息
	global __pool #不声明而直接使用__pool会因未定义过而报错
	with (yield from __pool) as conn:
		#Python就内置了SQLite3,一个数据库连接称为Connection,连接到数据库后，需要打开游标，称之为Cursor，通过Cursor执行SQL语句，然后，获得执行结果。
		#example: conn = sqlite3.connect('test.db'), cursor = conn.cursor(), cursor.execute('create table user (id varchar(20) primary key, name varchar(20))')
		#本函数中.db文件在create_pool函数的参数kw中
		#yield from将调用一个子协程（也就是在一个协程中调用另一个协程）并直接获得子协程的返回结果。
		cur = yield from conn.cursor(aiomysql.DictCursor)
		yield from cur.execute(sql.replace('?', '%s'), args or ())
		#如果SQL语句带有参数，那么需要把参数按照位置传递给execute()方法，有几个?占位符就必须对应几个参数，例如：cursor.execute('select * from user where name=? and pwd=?', ('abc', 'password'))
		#类的实例/对象.方法.属性，使用‘XX.XX’不断调用
		#将'?'替换为'%s'---SQL语句的占位符是?，而MySQL的占位符是%s，select()函数在内部自动替换。
		#然后用args or () 替代占位符
		#注意要始终坚持使用带参数的SQL，而不是自己拼接SQL字符串，这样可以防止SQL注入攻击。
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from cur.fetchall()
			#使用Cursor对象执行select语句时，通过featchall()可以拿到结果集。结果集是一个list，每个元素都是一个tuple/dict，对应一行记录。
			#取得所有行的数据，作为列表返回，一行数据是一个字典
			#如果传入size参数，就通过fetchmany()获取最多指定数量的记录，否则，通过fetchall()获取所有记录。
		yield from cur.close() 
		#要确保打开的Connection对象和Cursor对象都正确地被关闭，否则，资源就会泄露。
		logging.info('rows returned: %s' % len(rs)) #打印记录数
		return rs #返回结果集


# 定义一个通用的execute()函数执行INSERT、UPDATE、DELETE语句(这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数)
@asyncio.coroutine
def execute(sql, args, autocommit=True):
	#sql语句带有占位符，参数args带入到占位符中
	log(sql)
	with (yield from __pool) as conn:
		if not autocommit:
			yield from conn.begin()
		try:
			cur = yield from conn.cursor(aiomysql.DictCursor)
			yield from cur.execute(sql.replace('?', '%s'), args)
			affected = cur.rowcount
			if not autocommit:
				yield from conn.commit()
			yield from cur.close()
		except BaseException as e:
			if not autocommit:
				yield from conn.rollback()
			raise
		finally:
			conn.close()
		return affected #通过rowcount返回结果数

def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return ', '.join(L)
	#返回num个用','连接的'?',用于下文的占位


#Field类（负责保存数据库表的字段名和字段类型等）和各种Field子类
#通过Field类将user类的属性映射到User表的列中，其中每一列的字段又有自己的一些属性，包括数据类型，列名，主键和默认值
class Field(object):
	#初始化：
	def __init__(self, name, column_type, primary_key, default):
		# 表的字段包含名字、类型、是否为表的主键和默认值
		self.name = name
		self.column_type = column_type
		# sql列类型
		self.primary_key = primary_key
		#PRIMARY KEY （主键约束）是在数据表上可以唯一标识一条记录的，具有非空和唯一性的性质，也就是说在插入数据时不允许这一列为空并且不能出现重复的
		# 定义标识列,为一列或多列---也就是说用一或多列来作为标识，比如id列为主键，name列非主键，则通过某个id来定位某个name
		# 'create table user (id varchar(20) primary key, name varchar(20))',则primarykey为id
		self.default = default 
	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)
		# a.__class__就等效于a的类A--->由实例a返回类A.
		# 类名/表名，字段（列）类型， 实例名/字段名

#映射varchar的StringField：
class StringField(Field):
	def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
		super().__init__(name, ddl, primary_key, default)
		# 调用父类Field的初始化，各参数一一对应

class BooleanField(Field):
	def __init__(self, name=None, default=False):
		super().__init__(name, 'boolean', False, default)
	
class IntegerField(Field):
	def __init__(self, name=None, primary_key=False, default=0):
		super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):
	def __init__(self, name=None, primary_key=False, default=0.0):
		super().__init__(name, 'real', primary_key, default)

class TextField(Field):
	def __init__(self, name=None, default=None):
		super().__init__(name, 'text', False, default)	


# metaclass,用于创建或修改类：先定义metaclass(ModelMetaclass)，就可以创建类Model，最后创建实例。
class ModelMetaclass(type):
	# metaclass是类的模板，所以必须从`type`类型派生：
	def __new__(cls, name, bases, attrs):
		# cls: 当前准备创建的类的对象,相当于self
        # name: 类名,比如User继承自Model,当使用该元类创建User类时,name=User
        # bases: 父类的元组
        # attrs: 类的属性(方法)的字典,比如User有__table__,id,等,就作为attrs的keys
		#__new__()方法接收到的参数是已【规定】好的，自动从Model类更下层的类和对象代入生成的
		#在此，我们可以修改类的定义，比如，加上新的方法，然后，返回修改后的定义
		#排除Model本身，排除掉对Model类的修改：
		if name=='Model':
			return type.__new__(cls, name, bases, attrs)
			#返回修改后的定义
		#获取table名称：
		tableName = attrs.get('__table__', None) or name 
		# dict.get(key, default=None) 
		# attrs是个字典，get()方法返回给定键的值。如果键不可用，则返回默认值None。
		# x or y: if x is false, then y, else x.
		#有表名属性则沿用表名，否则使用类名命名表名
		logging.info('found model: %s (table: %s)' % (name, tableName))
		#获取所有的Field和主键名：
		mappings = dict() #创建空字典储存映射
		fields = []
		primaryKey = None
		# 遍历类的属性,找出定义的域(如【StringField】,字符串域)内的值,建立映射关系
        # k是属性名,v其实是定义域!请看name=StringField(ddl="varchar50")
		for k, v in attrs.items():
			# k是类的一个属性，v是这个属性在数据库中对应的Field列表属性
			#attrs是User类的属性集合，是一个dict，需要通过items函数转换为[(k1,v1),(k2,v2)]这种形式，才能用for k, v in来循环
			''' >>> {'id': IntegerField(), 'name': StringField()}  
					k是'id', v是IntegerField  k是'name', v是StringField
				>>> d.items() 
				[('id', IntegerField()), ('name', StringField())] '''
			if isinstance(v, Field):
				logging.info(' found mapping: %s ==> %s' % (k, v))
				mappings[k] = v
				if v.primary_key: # v是Field类，实例属性
					#找到主键：
					if primaryKey:
						raise StandardError('Duplicate primary key for field: %s' % k)
						#主键重复/已存在
					primaryKey = k 
					#主键一般只有一个
				else:  # v.primary_key = False,区别主键和非主键
					fields.append(k)
		# primaryKey设置完毕
		if not primaryKey:  #primaryKey还是None，遍历attrs没找到
			raise StandardError('Primary key not found.')
		for k in mappings.keys():
			attrs.pop(k)
			##fields中的值都是字符串，下面这个匿名函数的作用是在字符串两边加上``生成一个新的字符串，为了后面生成sql语句做准备
			# 要删除一个key，用pop(key)方法，对应的value也会从dict中删除：
			# 删除已映射好的类的方法/属性
			#在当前类（比如User）中查找定义的类的所有属性，如果找到一个Field属性，就把它保存到一个dict中，同时从类属性中删除该Field属性，否则，容易造成运行时错误（实例的属性会遮盖类的同名属性）；
		escaped_fields = list(map(lambda f: '`%s`' % f, fields))
		# lambda语句冒号前是参数，可以有多个用逗号隔开，冒号右边是返回值
		# map()方法将fields中的元素分别代入lambda语句，返回结果的list
		# list()方法，形成列表
		# 收集非主键的属性/方法/列,加上``
		attrs['__mappings__'] = mappings # 保存属性和列的映射关系，属性映射到列，属性名-->列名
		# example:  {'__mappings__':{'name':StringField, 'score': StringField}}
		attrs['__table__'] = tableName 
		attrs['__primary_key__'] = primaryKey #主键属性名
		attrs['__fields__'] = fields #除主键外的属性名
		# 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ','.join(escaped_fields), tableName)
		# ','.join(escaped_fields)方法把escaped_fields的各个元素用','连起来
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields)+1))
		# 没有``的要加上；insert语句插入一行记录：'insert into user (id, name) values (\'1\', \'Michael\')'
		# create_args_string(len(escaped_fields)+1)，自己定义一个函数，将values(%s)内的%s用数个'?'来占位
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ','.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		#update `%s`表名；      where `%s`=?'通过主键来标识
		#把fields中的元素即非主键作为f代入lambda f: '`%s`=?' % (mappings.get(f).name or f)中，返回列名（非主键）的list，并用','连起来
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
		# attrs位于类的方法内，是属性，直接添加后直接调用
		return type.__new__(cls, name, bases, attrs)
		# 返回修改后类的定义
#这样，任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系，并存储到自身的类属性如__table__、__mappings__中。

#定义所有ORM映射的基类Model：
class Model(dict, metaclass=ModelMetaclass):
	#继承自dict类，使用ModelMetaclass来定制/修改类,隐式继承ModelMetaclass
	#在创建Model时，要通过ModelMetaclass.__new__()来创建,见下文
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)
		#这里直接调用了Model的父类dict的初始化方法，把传入的关键字参数存入自身的dict中
		#super(B, self)首先找到B的父类（就是类A），然后把类B的对象self转换为类A的对象（通过某种方式），然后“被转换”的类A对象调用自己的__init__函数。
		#Model的self(对象）转换为父类dict的self（对象），再调用dict的__init__()
		# **kw: 类属性/字段/列=某值 **kw关键字参数在函数内部自动组装为dict
	def __getattr__(self, key):
		#没有这个方法，获取dict的值需要通过d[k]的方式，有这个方法就可以通过属性来获取值，也就是d.k
		try:
			return self[key]
			#因为是个dict所以可以这样调用
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)
	def __setattr__(self, key, value):
		 #和上面一样，不过这个是用来设置dict的值，通过d.k=v的方式
		self[key] = value
	#Model从dict继承，所以具备所有dict的功能，同时又实现了特殊方法__getattr__()和__setattr__()，因此又可以像引用普通字段那样写：
	#user['id'] or user.id
	#上面两个方法是用来获取和设置**kw转换而来的dict的值，而下面的getattr是用来获取当前实例的属性值，不要搞混了
	def getValue(self, key):
		return getattr(self, key, None) # 会去调用__getattr__
		# example:getattr(obj, 'z', 404) # 获取属性'z'，如果不存在，返回默认值404
	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			#属性不存在
			#该对象的该属性还没有赋值，就去获取它对应的列的默认值
			field = self.__mappings__[key] #对应的列 # field是一个定义域!比如StringField
			#(结合上文ModelMetaclass,attrs['__mappings__'] = mappings)
			if field.default is not None:
				#field.default见继承自Model的更下层类的具体对象的定义,如User的对象
				# 看models.py中的例子就懂了
                # id的StringField.default=next_id,因此调用该函数生成独立id
                # FloatField.default=time.time数,因此调用time.time函数返回当前时间
                # 普通属性的StringField默认为None,因此还是返回None
				value = field.default() if callable(field.default) else field.default
				#类是可调用的，而类的实例实现了__call__()方法才可调用
				#如果field的default是个方法，value就是default()被调用后返回的值，如果不是，value就是default本身。
				#这里是说字段的默认值可能是个值，也可能是个函数，如果默认值是个值，就取这个值，如果是个函数，就调用它，去调用后返回的结果。
				logging.debug('using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)# 会去调用__setattr__
				# 不存在某个属性时创建该属性及赋值
		return value
    #往Model类添加class方法，就可以让所有子类调用class方法：
    # 类方法有类变量cls传入（相当于self，调用时自动传入），从而可以用cls做一些相关的处理。并且有子类继承时，调用该类方法时，传入的类变量cls是子类，而非父类。
	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
		' find objects by where cause' #根据WHERE条件查找
		sql = [cls.__select__]
    	#定义在ModelMetaclass中的select语句'select `%s`, %s from `%s`'--->['select `%s`, %s from `%s`']
		if where:
			sql.append('where')
			sql.append(where)      #['select `%s`, %s from `%s`', 'where', where语句]
		if args is None:
			args = []
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)      #['select `%s`, %s from `%s`', 'where', where语句, 'order by', orderBy语句]
		limit = kw.get('limit', None)
		if limit is not None:
			sql.append('limit')      #['select `%s`, %s from `%s`', 'where', where语句, 'order by', orderBy语句, 'limit']
			if isinstance(limit, int):
				sql.append('?')      #['select `%s`, %s from `%s`', 'where', where语句, 'order by', orderBy语句, 'limit', '?']
				args.append(limit)		#[limit，是个int]
			elif isinstance(limit, tuple) and len(limit) == 2:
				
				sql.append('?,?')		#['select `%s`, %s from `%s`', 'where', where语句, 'orderBy', orderBy语句, 'limit', '?,?']
				args.extend(limit)		#[limit，是个tuple, (a, b)]
				#extend() 函数用于在列表末尾一次性追加另一个序列中的多个值（用新列表扩展原来的列表）
			else:
				raise ValueError('Invalid limit value: %s' % str(limit))
		rs = await select(' '.join(sql), args)
	#select(' '.join(sql), args)-->调用方法select()-->select(select `%s`, %s from `%s` where where语句 orderBy orderBy语句 limit ?/?,?, [a]/[(a,b)])
	#用空格连接sql[]形成语句，将限制条件limit代入占位符?(%s在ModelMetaclass中已被替代)
	# mysql> SELECT * FROM table LIMIT 5;     //检索前 5 个记录行  SELECT * FROM table LIMIT 5,10; //检索记录行6-15 
	#结果集是一个list，每个元素都是一个tuple/dict，对应一行记录rs = [{'id':'1','name':'a'}, {'id':'2','name':'b'}]
		return [cls(**r) for r in rs]
    	#**r表示把r这个dict的所有key-value用关键字参数传入到函数的**kw参数，kw将获得一个dict，注意kw获得的dict是r的一份拷贝，对kw的改动不会影响到函数外的r。
    	#cls(id=1, name='a')

	@classmethod
	@asyncio.coroutine
	# 通过类方法实现主键查找:
	def find(cls, pk):
		# 参数没有self，类方法，cls是个实例？
		#pk: primarykey
		' find object by primary key.'
		rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		#调用select('select `primaryKey`, 非primaryKey from `tablename` where primaryKey=?', [pk/primarykey],1/返回记录数)
		if len(rs) == 0:
			return None
		return cls(**rs[0])
		# 1.将rs[0]转换成关键字参数元组，rs[0]为dict
		# 2.通过<class '__main__.User'>(位置参数元组)，产生一个实例对象


	@classmethod
	async def findNumber(cls, selectField, where=None, args=None):
		' find number by select and where'
		#根据WHERE条件查找，但返回的是整数，适用于select count(*)类型的SQL。
		sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where) 
			#['select selectField语句 _num_ from `cls.__table__`', 'where', where语句]
		rs = await select(' '.join(sql), args, 1)
		#select(select selectField语句 _num_ from `表名`, args, 1) 1条记录 _num_统计记录数？
		if len(rs) == 0:
			return None
		return rs[0]['_num_'] 




	#往Model类添加实例方法，就可以让所有子类调用实例方法：
	@asyncio.coroutine
	def save(self):
	# 有self，实例方法
		args = list(map(self.getValueOrDefault, self.__fields__))
		# 非主键对应的值
		args.append(self.getValueOrDefault(self.__primary_key__))
		# 添加主键对应的值
		rows = yield from execute(self.__insert__, args)
		# 将值插入形成记录，返回影响结果数/行数
		if rows != 1:
			logging.warn('failed to insert record: affected rows: %s' % rows)

	async def update(self):
		args = list(map(self.getValue, self.__fields__))
		#update基于原有数据，不用orDefault
		args.append(self.getValue(self.__primary_key__))
		#获得各个值
		rows = await execute(self.__update__, args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows: %s' % rows)


	async def remove(self):
		args = [self.getValue(self.__primary_key__)]
		# primarykey标识列，可以看作一个列名
		#获取主键对应值
		rows = await execute(self.__delete__, args)
		if rows != 1:
			logging.warn('failed to remove by primarykey: affected rows: %s' % rows)

	









