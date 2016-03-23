import SocketServer
import SimpleHTTPServer
import base64
import urlparse
import cgi
import sys
import os.path
import uuid
import subprocess
import shutil

PORT = 27118
UPLOAD_DIR = sys.argv[1] 
WORK_DIR = sys.argv[2] 

def write_file(filename, file):
    if not os.path.exists(UPLOAD_DIR):
        os.mkdir(UPLOAD_DIR)
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, 'wb') as output_file:
        while True:
            chunk = file.read(1024)
            if not chunk:
                break
            output_file.write(chunk)

class Proxy(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        #self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_POST(self):
	print "in post method"
	parsed_url = urlparse.urlparse(self.path)
        path = parsed_url.path
        ctype, pdict = cgi.parse_header(self.headers['Content-Type']) 
        if ctype=='multipart/form-data':
            form = cgi.FieldStorage(self.rfile, self.headers, environ={'REQUEST_METHOD':'POST'})
            try:
                fileitem = form["blob"]
                if fileitem.file:
                    try:
                        write_file(fileitem.filename, fileitem.file)
                        refId = str(uuid.uuid4())
                        os.mkdir(os.path.join(WORK_DIR,refId))
                        os.mkdir(os.path.join(WORK_DIR,refId+"/in"))
                        os.mkdir(os.path.join(WORK_DIR,refId+"/out"))
                        os.environ["PYOPENGL_PLATFORM"] = "osmesa"
                        subprocess.call(["python", "chroma-backend-processor.py", os.path.join(WORK_DIR,refId+"/in/"), os.path.join(WORK_DIR,refId+"/out/"), os.path.join(UPLOAD_DIR,fileitem.filename),os.path.join(WORK_DIR,fileitem.filename)])
                        shutil.rmtree(os.path.join(WORK_DIR,refId))
                    except Exception as e:
                        print e
                        self.send_error(500)
                    else:
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write("OK")
                    return
            except KeyError:
                pass
        self.do_HEAD()

        

httpd = SocketServer.ForkingTCPServer(('', PORT), Proxy)
print "serving at port", PORT
httpd.serve_forever()
