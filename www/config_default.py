'''
通常，一个Web App在运行时都需要读取配置文件，
比如数据库的用户名、口令等，在不同的环境中运行时，
Web App可以通过读取不同的配置文件来获得正确的配置。
'''
# config_default.py

configs = {
	'db':{
		'host': '127.0.0.1',
		'port': 3306,
		'user': 'www-data',
		'password': 'www-data'
		'database': 'awesome'
	},
	'session': { # 定义会话信息
		'secret': 'AwEsOmE'
	}
}