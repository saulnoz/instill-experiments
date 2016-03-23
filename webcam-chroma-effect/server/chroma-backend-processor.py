import numpy
from OpenGL import GL as gl, GLUT as glut, GLU as glu, arrays
from OpenGL.GL.shaders import *
from OpenGL.raw.osmesa import mesa
from PIL import Image
from os import listdir
from os.path import isfile, join
import sys
import subprocess

width, height = 0,0
model = None
splashTex = None;

MainVertexData = None;
FullWindowVertices = None;
BaseProgram = None;

# vertex shader
strVS = """
attribute vec2 position;

varying vec2 texcoord;

uniform float yLowerThreshold;
uniform float yUpperThreshold;
varying float v_yLowerThreshold;
varying float v_yUpperThreshold;

void main()
{
    gl_Position = vec4(position, 0.0, 1.0);
    texcoord = position * vec2(0.5,-0.5) + vec2(0.5);
    v_yLowerThreshold = yLowerThreshold;
    v_yUpperThreshold = yUpperThreshold;
}
"""

# fragment shader
strFS = """
uniform sampler2D texture;

varying vec2 texcoord;
varying float v_yUpperThreshold;
varying float v_yLowerThreshold;

void main()
{
    vec4 pixel= texture2D(texture, texcoord);
    float alpha = 1.0;
    float r = pixel[0];
    float g = pixel[1];
    float b = pixel[2];
    float y =  0.299*r + 0.587*g + 0.114*b;
    float u = -0.147*r - 0.289*g + 0.436*b;
    float v =  0.615*r - 0.515*g - 0.100*b;
    if (y > v_yLowerThreshold && y < v_yUpperThreshold){
        alpha = (v+u)*40.0 +2.0;
    }
    pixel = vec4(pixel[0], pixel[1], pixel[2], alpha);
    if(pixel.a<0.1){
        gl_FragColor = vec4(0, 0, 0, 0.0);
    }else{
        gl_FragColor = pixel;
    }
}
"""


def TexFromPNG(filename):
  img = Image.open(filename) # .jpg, .bmp, etc. also work
  img_data = numpy.array(list(img.getdata()))
  texture = gl.glGenTextures(1)
  gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT,1)
  gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
  gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
  gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
  gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
  gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
  gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, img.size[0], img.size[1], 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, img_data)
  return texture

def makeBuffer(target, data, size):
  TempBuffer = gl.glGenBuffers(1)
  gl.glBindBuffer(target, TempBuffer)
  gl.glBufferData(target, size, data, gl.GL_STATIC_DRAW)
  return TempBuffer

def teardown(ctx):
  mesa.OSMesaDestroyContext(ctx)


def render():
  def scene():
    glut.glutInitDisplayMode(glut.GLUT_RGBA | glut.GLUT_ALPHA);
    gl.glViewport(0, 0, width, height)        
    gl.glClearDepth(1)
    gl.glClearColor(0,0,0,0)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glUseProgram(BaseProgram)
    pos = glGetAttribLocation(BaseProgram, "position")
    
    #Could vary to adapt the best green factor
    yLowerThreshold = gl.glGetUniformLocation(BaseProgram, "yLowerThreshold");
    gl.glUniform1f(yLowerThreshold,0.2);

    #Could vary to adapt the best green factor
    yUpperThreshold = gl.glGetUniformLocation(BaseProgram, "yUpperThreshold");
    gl.glUniform1f (yUpperThreshold,0.8);
    
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, splashTex)
    gl.glUniform1i(gl.glGetUniformLocation(BaseProgram,"texture"), 0)
    
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER,MainVertexData)
    gl.glVertexAttribPointer(pos,
                          2,
                          gl.GL_FLOAT,
                          gl.GL_FALSE,
                          0,
                          None)
    gl.glEnableVertexAttribArray(pos)
    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER,FullWindowVertices)
    gl.glDrawElements(gl.GL_TRIANGLE_STRIP,
                   4,
                   gl.GL_UNSIGNED_SHORT,
                   None)
    gl.glDisableVertexAttribArray(pos)

  gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
  scene()
  gl.glFinish()

def save_render(filename):
  screenshot = gl.glReadPixels(0,0,width, height,gl.GL_RGBA,gl.GL_UNSIGNED_BYTE)
  snapshot = Image.frombuffer("RGBA",(width, height),screenshot,"raw","RGBA",0,0)
  snapshot.save(filename)


#Open the first image and get dimensions
inputdir = sys.argv[1]
outputdir = sys.argv[2]
invideofile = sys.argv[3]
outvideofile = sys.argv[4]

#explode the video 
subprocess.call(["/opt/ffmpeg/bin/ffmpeg", "-i", invideofile, "-r", "24", "-f", "image2", "-q:v", "1", inputdir+"%d_vid.png"])

filesToProcess = [f for f in listdir(inputdir) if isfile(join(inputdir, f))]
first_img = Image.open(inputdir+filesToProcess[0])
width = first_img.size[0]
height = first_img.size[1]

ctx = mesa.OSMesaCreateContext(gl.GL_RGBA, None) # requires PYOPENGL_PLATFORM=osmesa
buf = arrays.GLubyteArray.zeros((height, width, 4))
p = arrays.ArrayDatatype.dataPointer(buf)
assert(mesa.OSMesaMakeCurrent(ctx, buf, gl.GL_UNSIGNED_BYTE, width, height))
#assert(mesa.CurrentContextIsValid())
MainVertexData = numpy.array([-1,-1,1,-1,-1,1,1,1],numpy.float32)
FullWindowVertices = numpy.array([0,1,2,3],numpy.ushort)
MainVertexData = makeBuffer(gl.GL_ARRAY_BUFFER,MainVertexData,4*len(MainVertexData))
FullWindowVertices = makeBuffer(gl.GL_ELEMENT_ARRAY_BUFFER,FullWindowVertices,2*len(FullWindowVertices))
BaseProgram = compileProgram(compileShader(strVS,
                                                  gl.GL_VERTEX_SHADER),
                                    compileShader(strFS,
                                                  gl.GL_FRAGMENT_SHADER))
                                                  
for f in listdir(inputdir) :
    if isfile(join(inputdir, f)):
        splashTex = TexFromPNG(inputdir + f)
        render()
        save_render(outputdir + f)

teardown(ctx)
#reassemble video 
subprocess.call(["/opt/ffmpeg/bin/ffmpeg","-r", "24", "-i", outputdir+"%d_vid.png", "-c:v", "libvpx", "-pix_fmt", "yuva420p", outvideofile])