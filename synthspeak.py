#!python

import wx
import asyncio
import mido
from wxasync import AsyncBind, WxAsyncApp, StartCoroutine
import gui
from logger import Logger
import ctypes

nvda = ctypes.windll.LoadLibrary('./nvdaControllerClient64.dll')
def speak(text):
    nvda.nvdaController_speakText(text)

stop=nvda.nvdaController_cancelSpeech

def unpack_eight(data):
    out=[]
    for i in range(7):
        msb = (data[0]<<(7-i))&128
        out.append(msb|data[i+1])
    return out

def unpack(data):
    out=[]
    for i in range(0, len(data), 8):
        out = out + unpack_eight(data[i:i+8])
        print(out)
    return out

def make_stream():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    def callback(message):
        loop.call_soon_threadsafe(queue.put_nowait, message)
    async def stream():
        while True:
            yield await queue.get()
    return callback, stream()


class Synth: pass

class DeepMind (Synth) :

    def __init__(self, logger, frame):
        self.logger = logger
        self.frame = frame
        self.outname=[s for s in mido.get_output_names() if s.startswith('DeepMind12')][0]
        self.inname=[s for s in mido.get_input_names() if s.startswith('DeepMind12')][0]
        self.outport=mido.open_output(self.outname)
        self.inport=mido.open_input(self.inname)
        appmessage=mido.Message(type='sysex', data=[0x0, 0x20, 0x32, 0x20, 0x0, 0x0, 0x0])
        self.outport.send(appmessage)
        StartCoroutine(self.process_messages, self.frame)

    async def process_messages(self):
        cb, stream = make_stream()
        self.inport.callback = cb
        async for message in stream:
            methodname = "handle_"+message.type 
            getattr(self, methodname, self.handle_unknown) (message)

    def handle_unknown(self, message): pass

    def handle_control_change(self, message):
        methodname = "handle_cc_" + str(message.control)
        getattr(self, methodname, self.handle_unknown )(message)

    def handle_cc_32 (self, message):
        self.bank = message.value

    def handle_sysex(self, message) :
        if (message.data[5] == 0x0d):
            self.handle_program_name(message)

    def handle_program_name(self, message) :
        unpacked=unpack(message.data[9:])
        name="".join([chr(c) for c in unpacked if c>0])
        speak(name)
        print(name)

    def handle_program_change(self, message):
        stop()
        s = "bank "+("ABCDEFGH"[self.bank]) + " program " + str(message.program+1)
        speak(s)
        self.request_name(self.bank, message.program)

    def request_name(self, bank, program) :
        msg = mido.Message(type="sysex", data=[0x0,0x20,0x32,0x20,0x0, 0x0c, bank, program])
        self.outport.send(msg)


# main
app = WxAsyncApp()
frame = gui.MainFrame(None, wx.ID_ANY, "")
frame.Show()
app.SetTopWindow(frame)
logger = Logger(frame.log_text)
synth = DeepMind(logger, frame)
loop = asyncio.events.get_event_loop()
loop.run_until_complete(app.MainLoop())
