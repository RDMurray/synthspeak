import wx
import asyncio

class Logger:
    def __init__(self, text_ctrl):
        self.text_ctrl = text_ctrl

    def log(self, text):
        self.text_ctrl.AppendText(text)
        self.text_ctrl.AppendText('\n')


