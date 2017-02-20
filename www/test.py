import asyncio
import logging;logging.basicConfig(level=logging.INFO)
import orm
from models import User, Blog, Comment



@asyncio.coroutine
def test():
	yield from orm.create_pool(loop=loop, user='www-data', password='www-data', db='awesome')
	# 创建连接池，连接schema.sql
	u = User(id=1, name='Test', email='test@example.com', passwd='1234567890', image='about:blank')
	u1 = User(id=2, name='Test1', email='test1@example.com', passwd='12345678901', image='about:blank')
	u2 = User(id=3, name='Test2', email='test2@example.com', passwd='12345678902', image='about:blank')
	yield from u.save()
	yield from u1.save()
	yield from u2.save()
	print('=====================================================================================================')
	logging.info('test began...')
	#测试findAll()：
	users = yield from User.findAll()
	for user in users:
		logging.info('  findAll--->name: %s, password: %s' % (user.name, user.passwd))
	#测试update()：
	u.name = 'jbjbj'
	yield from u.update()
	print('     update---->name: %s' % u.name)
	#测试find()
	users2 = yield from User.find(2)
	print('find----->id= %s, name= %s' % (users2.id, users2.name))
	#测试remove()
	yield from u1.remove()

	logging.info('test finished...')
	print('=====================================================================================================')
	


loop = asyncio.get_event_loop()
loop.run_until_complete(test())

loop.close()

'''初始化数据库表:如果表的数量很少，可以手写创建表的SQL脚本：schema.sql
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
