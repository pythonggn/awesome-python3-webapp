'''
利用watchdog接收文件变化的通知，如果是.py文件，就自动重启wsgiapp.py进程。
用该脚本启动app.py,则当前目录下任意.py文件被修改后,服务器将自动重启
利用Python自带的subprocess实现进程的启动和终止，并把输入输出重定向到当前进程的输入输出中：
'''
__author__ = 'ggn'

import os, sys, time, subprocess
# subprocess模块提供了派生新进程的能力

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def log(s): # 打印日志信息
	print('[Monitor] %s' % s)

class MyFileSystemEventHandler(FileSystemEventHandler): # 自定义的文件系统事件处理器
	def __init__(self, fn):  # 初始化函数,将指定函数绑定到处理器的restart属性上
		super(MyFileSystemEventHandler, self).__init__()
		self.restart = fn 
	def on_any_event(self, event):  # on_any_event(event)捕获所有事件, 文件或目录的创建, 删除, 修改等
		if event.src_path.endswith('.py'): # 此处只处理python脚本的事件
			log('Python source file change: %s' % event.src_path)
			self.restart()

command = ['echo', 'ok']
process = None

def kill_process(): # 杀死进程函数
	global process 
	if process:
		log('kill process [%s]...' % process.pid)
		process.kill()
		process.wait()
		'''
		process指向一个Popen对象,在start_process函数中被创建
        通过发送一个SIGKILL给子程序, 来杀死子程序. SIGKILL信号将不会储存数据, 此处也不需要
        wait(timeout=None),等待进程终止,并返回一个结果码. 该方法只是单纯地等待, 并不会调用方法来终止进程, 因此需要kill()方法
		'''
		log('Process ended with code %s.' % process.returncode)
		process = None

def start_process():
	global process, command # 用到全局变量的都要声明
	log('Start process %s...' % ' '.join(command))
	process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
	# subprocess.Popen是一个构造器, 它将在一个新的进程中执行子程序
	# command是一个list, 即sequence. 此时, 将被执行的程序应为序列的第一个元素, 此处为python3/python

def restart_process(): # 重启程序
	kill_process()
	start_process() # 在一个新的进程中执行子程序

def start_watch(path, callback): # 启动看门狗
	observer = Observer() # 创建监视器对像
	observer.schedule(MyFileSystemEventHandler(restart_process), path, recursive=True)
	# MyFileSystemEventHandler(restart_process)创建实例并封装在本函数内部
	# restart_process(重启进程函数)绑定到该处理器的restart实例属性上
	# recursive=True表示递归, 即当前目录的子目录也在被监视范围内
	observer.start() # 启动监视器
	log('Watching directory %s...' % path)
	start_process() # 在一个新的进程中通过调用subprocess.Popen方法启动一个python子程序
	try:
		while True:
			time.sleep(0.5) # 执行程序后休眠0.5s
	except KeyboardInterrupt:
		observer.stop()
	observer.join() # wait until the thread terminates

if __name__ == '__main__':
	argv = sys.argv[1:] # sys.argv[0]表示当前被执行的脚本,sys.argv[1:]为此外的脚本
	if not argv: # 只启动了此脚本,没有其他脚本--直接退出
		print('Usage: ./pymonitor your-script.py')
		exit(0)
	if argv[0] != 'python': # 检查输入参数, 若第一个参数非python/python3，则添加
		argv.insert(0, 'python') # 如python app.py
	command = argv # 将输入参数赋给command, 之后将用command构建shell 命令
	path = os.path.abspath('.')  # 获取当前目录的绝对路径表示.'.'表示当前目录
	start_watch(path, None)