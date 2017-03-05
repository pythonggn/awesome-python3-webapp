__author__ = 'ggn'

#有了ORM，我们就可以把Web App需要的3个表用Model表示出来：

import time, uuid 
# UUID: 通用唯一标识符 ( Universally Unique Identifier )
from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
	return '%015d%s000' % (int(time.time()*1000), uuid.uuid4().hex)

class User(Model):
	__table__ = 'users'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	email = StringField(ddl='varchar(50)')
	passwd = StringField(ddl='varchar(50)')
	# varchar:可变长字符串
	admin = BooleanField()
	name = StringField(ddl='varchar(50)')
	image = StringField(ddl='varchar500)')
	created_at = FloatField(default=time.time)

class Blog(Model):
	__table__ = 'blogs'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	user_name = StringField(ddl='varchar(50)')
	user_image = StringField(ddl='varchar(500)')
	name = StringField(ddl='varchar(50)')
	summary = StringField(ddl='varchar(200)')
	content = TextField()
	created_at = FloatField(default=time.time)

class Comment(Model):
	__table__ = 'comments'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	blog_id = StringField(ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	user_name = StringField(ddl='varchar(50)')
	user_image = StringField(ddl='varchar(500)')
	content = TextField()
	created_at = FloatField(default=time.time)

'''在编写ORM时，给一个Field增加一个default参数可以让ORM自己填入缺省值，非常方便。
并且，缺省值可以作为函数对象传入，在调用save()时自动计算。
例如，主键id的缺省值是函数next_id，创建时间created_at的缺省值是函数time.time，
可以自动设置当前日期和时间。

#初始化数据库表:如果表的数量很少，可以手写创建表的SQL脚本：schema.sql
执行sql脚本,可以有2种方法:
  第一种方法:
 在命令行下(未连接数据库),输入 mysql -h localhost -u root -p123456 < F:\hello world\niuzi.sql (注意路径不用加引号的!!) 回车即可.
  第二种方法:
 在命令行下(已连接数据库,此时的提示符为 mysql> ),输入 source F:\hello world\niuzi.sql (注意路径不用加引号的) 
 或者 \. F:\hello world\niuzi.sql (注意路径不用加引号的) 回车即可  
 source C:\work\awesome-python3-webapp\www\schema.sql

mysql命令：
show databases;
use 数据库名;
show tables;
select * from 表名；----显示所有内容
delete from 表名；-----删除所有内容
delete from MyClass where id=1; -----删除部分内容
'''
