
#类、实例的变量即属性
#数据库中行叫记录==>映射类的实例,列叫字段==>映射类的属性/方法
#ORM技术：Object-Relational Mapping，把关系数据库的表结构映射到对象上,数据库表中添加一行记录，可以视为添加一个对象
#异步编程的一个原则：一旦决定使用异步，则系统每一层都必须是异步，“开弓没有回头箭”。
# 下面创建连接池
@asyncio.coroutine
def create_pool(loop, **kw):
	#**kw:关键字参数，任意个含参数名的参数
	logging.info('create database connection pool...')
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
		charset=kw.get('charset','utf-8'),
		autocommit=kw.get('autocommit', True),
		maxsize=kw.get('maxsize', 10),
		minsize=kw.get('minsize',  1),
		loop=loop
	)


#下面定义select函数，用于执行select语句
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
		#注意要始终坚持使用带参数的SQL，而不是自己拼接SQL字符串，这样可以防止SQL注入攻击。
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from cur.fetchall()
			#使用Cursor对象执行select语句时，通过featchall()可以拿到结果集。结果集是一个list，每个元素都是一个tuple，对应一行记录。
			#如果传入size参数，就通过fetchmany()获取最多指定数量的记录，否则，通过fetchall()获取所有记录。
		yield from cur.close() 
		#要确保打开的Connection对象和Cursor对象都正确地被关闭，否则，资源就会泄露。
		logging.info('rows returned: %s' % len(rs)) #打印
		return rs #返回结果集

# 定义一个通用的execute()函数执行INSERT、UPDATE、DELETE语句(这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数)
@asynsio.coroutine
def execute(sql, args):
	#sql语句带有占位符，参数args带入到占位符中
	log(sql)
	with (yield from __pool) as conn:
		try:
			cur = yield from conn.cursor()
			yield from cur.execute(sql.replace('?', '%s'), args)
			affected = cur.rowcount
			yield from cur.close()
		except BaseException as e:
			raise
		return affected #通过rowcount返回结果数


#编写简单的ORM
#从上层调用者角度来设计。先考虑如何定义一个User对象，然后把数据库表users和它关联起来。
from orm import Model, StringField, IntegerField

#想定义一个User类来操作对应的数据库表User：
class User(Model):
	__table__ = 'users' 
	#两个下划线__，在Python中，实例的变量名如果以__开头，就变成了一个私有变量
	#变量名类似__xxx__的，也就是以双下划线开头，并且以双下划线结尾的，是特殊变量
	id = IntegerField(primary_key=True)  # 定义类的属性到列的映射：
	 #见下文Field类
	name = StringField()  # 定义类的属性到列的映射：
	#example: 
	#实例属性
	#class Student(object):
    	#def __init__(self, name):
        	#self.name = name
    #类属性：
    #class Student(object):
    	#name = 'Student'
	#定义在User类中的__table__、id和name是类的属性，类的所有实例都可以访问到
	#在类级别上定义的属性用来描述User对象和表的映射关系，而实例属性必须通过__init__()方法去初始化，所以两者互不干扰：
	#创建实例：
	user = User(id=123, name='Michael')
	#存入数据库：
	user.insert()
	#查询所有User对象：
	users = User.findAll()


#定义Model,首先要定义的是所有ORM映射的基类Model：
class Model(dict, metaclass=ModelMetaclass):
	#继承自dict类，使用ModelMetaclass来定制/修改类,隐式继承ModelMetaclass
	#在创建Model时，要通过ModelMetaclass.__new__()来创建,见下文
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)
		#super(B, self)首先找到B的父类（就是类A），然后把类B的对象self转换为类A的对象（通过某种方式），然后“被转换”的类A对象调用自己的__init__函数。
		#Model的self(对象）转换为父类dict的self（对象），再调用dict的__init__()
	def __getattr__(self, key):
		try:
			return self[key]
			#因为是个dict所以可以这样调用
		except keyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)
	def __setattr__(self, key, value):
		self[key] = value
	def getValue(self, key):
		return getattr(self, key, None)
		# example:getattr(obj, 'z', 404) # 获取属性'z'，如果不存在，返回默认值404
	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			#(结合下文ModelMetaclass,attrs['__mappings__'] = mappings)
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)
				# 不存在某个属性时创建该属性及赋值
		return value
    #往Model类添加class方法，就可以让所有子类调用class方法：
    @classmethod
    @asyncio.coroutine
    # 通过类方法实现主键查找:
    def find(cls, pk):
    	# 参数没有self，类方法，cls是个实例？
    	' find object by primary key.'
    	rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
    	if len(rs) == 0:
    		return None
    	return cls(**rs[0])

    #往Model类添加实例方法，就可以让所有子类调用实例方法：
    @asyncio.coroutine
    def save(self)：
    # 有self，实例方法
    	args = list(map(self.getValueOrDefault, self.__fields__))
    	# 非主键对应的值
    	args.append(self.getValueOrDefault(self.__primary_key__))
    	# 添加主键对应的值
    	rows = yield from execute(self.__insert__, args)
    	# 将值插入形成记录，返回影响结果数/行数
    	if rows != 1:
    		logging.warn('failed to insert record: affected rows: %s' % rows)


#Field类（负责保存数据库表的字段名和字段类型等）和各种Field子类
class Field(object):
	#初始化：
	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		# sql列类型
		self.primary_key = primary_key
		#PRIMARY KEY （主键约束）是在数据表上可以唯一标识一条记录的，具有非空和唯一性的性质，也就是说在插入数据时不允许这一列为空并且不能出现重复的
		# 定义标识列,为一列或多列---也就是说用一或多列来作为标识，比如id列为主键，name列非主键，则通过某个id来定位某个name
		self.default = default 
	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

#映射varchar的StringField：
class StringField(Field):
	def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
		super().__init__(name, ddl, primary_key, default)
		# 调用父类Field的初始化，各参数一一对应

# metaclass,用于创建或修改类：先定义metaclass(ModelMetaclass)，就可以创建类Model，最后创建实例。
class ModelMetaclass(type):
	# metaclass是类的模板，所以必须从`type`类型派生：
	def __new__(cls, name, bases, attrs):
		#__new__()方法接收到的参数依次是：当前准备创建的类的对象；类的名字；类继承的父类集合；类的属性方法集合。
		#在此，我们可以修改类的定义，比如，加上新的方法，然后，返回修改后的定义
		#排除Model本身，排除掉对Model类的修改：
		if name=='Model':
			return type.__new__(cls, name, bases, attrs)
			#返回修改后的定义
		#获取table名称：
		tableName = attrs.get('__table__', None) or name 
		# dict.get(key, default=None) 
		# attrs是个字典，get()方法返回给定键的值。如果键不可用，则返回默认值None。
		#有表名属性则沿用表名，否则使用类名命名表名
		logging.info('found model: %s (table: %s)' % (name, tableName))
		#获取所有的Field和主键名：
		mappings = dict() #创建空字典储存映射
		fields = []
		primaryKey = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				logging.info(' found mapping: %s ==> %s' % (k, v))
				mappings[k] = v
				if v.primary_key: # v是Field类，实例属性
					#找到主键：
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field: %s' % k)
						#主键重复/已存在
					primaryKey = k 
				else:  # v.primary_key = False,区别主键和非主键
					fields.append(k)
		# primaryKey设置完毕
		if not primaryKey:  #primaryKey还是None
			raise RuntimeError('Primary key not found.')
		for k in mappings.keys():
			attrs.pop(k)
			# 要删除一个key，用pop(key)方法，对应的value也会从dict中删除：
			# 删除已映射好的类的方法/属性
			#在当前类（比如User）中查找定义的类的所有属性，如果找到一个Field属性，就把它保存到一个dict中，同时从类属性中删除该Field属性，否则，容易造成运行时错误（实例的属性会遮盖类的同名属性）；
		escaped_fields = list(map(lambda f: '`%s`' % f, fields))
		# lambda语句冒号前是参数，可以有多个用逗号隔开，冒号右边是返回值
		# map()方法将fields中的元素分别代入lambda语句，返回结果的list
		# list()方法，形成列表
		# 收集非主键的属性/方法/列
		attrs['__mappings__'] = mappings # 保存属性和列的映射关系，属性映射到列
		# example:  {'__mappings__':{'name':'name', 'score': 'score'}}
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
		# attrs位于类的方法内，是属性
		return type.__new__(cls, name, bases, attrs)
		# 返回修改后类的定义
#这样，任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系，并存储到自身的类属性如__table__、__mappings__中。



