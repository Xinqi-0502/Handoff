import os,sys,time
folder=sys.argv[1];grandchild=len(sys.argv)>2
name='grandchild_pid.json' if grandchild else 'child_pid.json'
with open(os.path.join(folder,name),'w') as f:f.write('{"pid":'+str(os.getpid())+'}')
if not grandchild:
    import subprocess
    subprocess.Popen([sys.executable,'-B',__file__,folder,'grandchild'],cwd=folder,creationflags=subprocess.CREATE_NO_WINDOW)
time.sleep(120)
