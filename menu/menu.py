import os,signal

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

font = ImageFont.load_default()

class Menu:
  def __init__(self,navigatable=True,firstEntry=0,width=128,height=64):
    self.lines=[]
    self.selectable=[]
    self.firstEntry=firstEntry
    self.currentLine=firstEntry
    self.navigatable=navigatable
    self.img = Image.new('1', (width,height))
    self.width = width
    self.height = height
  def size(self,width,height):
    self.width = width
    self.height = height
    self.img = Image.new('1', (width,height))
    for line in self.lines:
      line.size(width,height);
  def reset(self):
    self.currentLine=self.firstEntry
  def addLine(self,line,selectable=True):
    line.size(self.width,self.height)
    self.lines.append(line)
    self.selectable.append(selectable)
  def down(self):
    if not self.navigatable:
      return
    self.currentLine+=1
    if self.currentLine>len(self.lines)-1:
      self.currentLine=0
    if not self.selectable[self.currentLine]:
      self.down()
  def up(self):
    if not self.navigatable:
      return
    self.currentLine-=1
    if self.currentLine<0:
      self.currentLine=len(self.lines)-1
    if not self.selectable[self.currentLine]:
      self.up()
  def enter(self,ctl):
    line = self.lines[self.currentLine]
    if isinstance(line,MenuLine):
      line.execute(ctl)
  def render(self):
    draw = ImageDraw.Draw(self.img)
    draw.rectangle((0,0,self.width,self.height), outline=0, fill=0)
    for i,line in enumerate(self.lines):
      if self.currentLine==i:
        box=255
        text=0
      else:
        box=0
        text=255
      if isinstance(line,MenuLine):
        image=line.render(self.currentLine==i)
        mask = Image.new('1',(self.width,self.height))
        maskDraw = ImageDraw.Draw(mask)
        maskDraw.rectangle((0,(i*10),self.width,(i*10)+10), outline=0, fill=255)
        self.img.paste(image,(0,(i*10)))
      else:
        draw.rectangle((0,(i*10),self.width,(i*10)+10), outline=0, fill=box)
        draw.text((3, i*10), str(line), font=font, fill=text)
    return self.img
  def getPos(self):
    return self.currentLine
  def setPos(self,line):
    self.currentLine=line

class MenuLine:
  def __init__(self,label,cb):
    self.label = label
    self.cb = cb
  def execute(self,ctl):
    self.cb()
  def size(self,width,height):
    self.width = width
    self.height = height
  def render(self,current):
    img = Image.new('1', (self.width,10))
    if current:
      box=255
      text=0
    else:
      box=0
      text=255
    draw = ImageDraw.Draw(img)
    draw.rectangle((0,0,self.width,10), outline=0, fill=0)
    draw.rectangle((0,0,self.width,10), outline=0, fill=box)
    draw.text((3, 0), str(self.label), font=font, fill=text)
    return img

class MenuEntry(MenuLine):
  def __init__(self,label,menu):
    self.label = label
    self.nextMenu = menu
  def execute(self,ctl):
    self.next(ctl)
  def next(self,ctl):
    ctl.changeMenu(self.nextMenu)

class MenuBack(MenuEntry):
    def __init__(self,label):
        self.label=label
    def next(self,ctl):
        ctl.back()

class MenuText(MenuLine):
  def __init__(self,label):
    MenuLine.__init__(self,label,None)
  def execute(self,ctl):
    pass

class MenuCustom(MenuLine):
    def __init__(self,renderer):
        self.label = renderer()
        self.renderer = renderer
    def render(self,current):
        self.label = self.renderer()
        return MenuLine.render(self,current)
    def execute(self,ctl):
        pass;

class Controller:
    def __init__(self,menu,width=128,height=64):
        self.pause=False
        menu.size(width,height)
        self.menu = menu
        self.rootMenu = menu
        menu.reset()
        self.menuImg = menu.img
        self.menuTree = []
        self.width = width
        self.height = height
    def loop(self):
        pass
    def changeMenu(self,menu):
        if menu is self.rootMenu:
            self.menuTree = []
        else:
            self.menuTree.append(self.menu)
        self.menu = menu
        menu.reset()
        self.menuImg = menu.img
    def up(self,_=None):
        self.menu.up()
    def down(self,_=None):
        self.menu.down()
    def enter(self,_=None):
        self.menu.enter(self)
    def back(self,_=None):
        if len(self.menuTree) > 0:
            self.menu = self.menuTree.pop()
            self.menu.reset()
            self.menuImg = self.menu.img
    def pause(self,toPause):
        self.pause=toPause

class PyGameMenuController(Controller):
    def __init__(self,menu,width=128,height=64):
        self.pygame = __import__('pygame')
        Controller.__init__(self,menu,width,height)
        self.size = width,height
        self.display = self.pygame.display
        self.screen = self.display.set_mode(self.size)
    def loop(self):
        if self.pause:
            return
        eventList = self.pygame.event.get()
        for key in eventList:
            if key.type == self.pygame.KEYDOWN:
              if key.key == self.pygame.K_UP:
                  self.up()
              if key.key == self.pygame.K_DOWN:
                  self.down()
              if key.key == self.pygame.K_BACKSPACE:
                  self.back()
              if key.key == self.pygame.K_RETURN:
                  self.enter()
            if key.type == self.pygame.QUIT:
              os.kill(os.getpid(),signal.SIGTERM)
        menuImage = self.menu.render().convert('RGB')
        image = self.pygame.image.fromstring(menuImage.tobytes("raw",'RGB'),menuImage.size,'RGB')
        self.screen.blit(image,[0,0])
        self.display.flip()

class OledMenuController(Controller):
    def __init__(self,menu,display,upin,dpin,epin,bpin):
        from RPi import GPIO
        self.Adafruit_SSD1306 = __import__('Adafruit_SSD1306')
        RST = None
        self.disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)
        Controller.__init__(self,menu,self.disp.width,self.disp.height)
        GPIO.add_event_detect(upin, edge=GPIO.RISING, callback=self.up, bouncetime=200)
        GPIO.add_event_detect(dpin, edge=GPIO.RISING, callback=self.down, bouncetime=200)
        GPIO.add_event_detect(epin, edge=GPIO.RISING, callback=self.enter, bouncetime=200)
        GPIO.add_event_detect(bpin, edge=GPIO.RISING, callback=self.back, bouncetime=200)
    def loop(self):
        if self.pause:
            return
        self.disp.image(self.menu.render())
        self.disp.display()
