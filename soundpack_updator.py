import wx
import gui
from logger import log

def main():
    log.info("Application starting.")
    app = wx.App(False)
    frame = gui.MainFrame(None)
    frame.Show()
    app.MainLoop()
    log.info("Application shutting down.")

if __name__ == '__main__':
    main()