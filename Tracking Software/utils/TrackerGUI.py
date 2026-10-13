import logging
import tkinter as tk
from tkinter import Menu
from tkinter import ttk
from tkinter import *
from tkinter.ttk import *
import OpenSkyAPIHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler("FlightTracker.log"), 
              logging.StreamHandler()]
)
logger_main = logging.getLogger("Tracker.GUI")
logger_main.setLevel(logging.DEBUG)
logger_main.info("GUI is Live")

class TrackerMainGUI:

    def __init__(self, root, tracker:OpenSkyAPIHandler.Flight_API):

        self.tracker = tracker
        self.root = root
        root.title("Tracker")
        self.latest_state = ()
        self.craftlist = []
        self.target_craft = None

        mainframe = Frame(root, padding=(3,3,12,12))
        mainframe.grid(column=0,row=0, sticky=(N,S,E,W))

        fr_canvas = Frame(mainframe, padding=(3,3,12,12))
        fr_canvas.columnconfigure(0,weight=0)
        sz_canvas = 600
        rings_canvas = (0.02, 0.125, 0.25, .4)
        self.canvas = Canvas(fr_canvas, background="#023800", width=600, height=600)
        for ring in rings_canvas:
            self.canvas.create_oval(ring*sz_canvas,ring*sz_canvas,(1-ring)*sz_canvas,(1-ring)*sz_canvas, outline="#11FF00")
        self.canvas.create_line(300,0,300,600,fill="#11FF00")
        self.canvas.create_line(0,300,600,300,fill="#11FF00")
        self.canvas.grid(column=0,row=0, sticky=N+S+W+E)
        fr_canvas.grid(column=1, row=0, columnspan=5, sticky=N+S+E+W)

        panel_l = Frame(mainframe, padding=(3,3,12,12))
        panel_l.grid(column=0,row=0, sticky=N)
        label_panel_l = Label(panel_l, text="Some Text Here") 
        label_panel_l.grid(column=0,row=0)
        self.lpStart = Button(panel_l, text="Start API", command=self.api_start)
        self.lpStart.grid(column=0,row=1)
        self.lpStop = Button(panel_l, text="Stop API", command=self.api_stop)
        self.lpStop.grid(column=0,row=2)


        craftPanel = Frame(mainframe, padding=(3,3,12,12))
        craftPanel.grid(column=6,row=0, sticky=N)
        self.craftstrval = StringVar(value=self.craftlist)
        self.cpList = Listbox(craftPanel, listvariable=self.craftstrval, height=int(sz_canvas/15.789), selectmode=SINGLE) 
        self.cpList.grid(column=0,row=0, sticky=N)        
        
        StatusBar = Frame(mainframe, padding=(3,3,12,12))
        StatusBar.grid(column=0,row=1, columnspan=7, sticky=(S,W))
        self.sbQueueSize = Label(StatusBar, text="Placeholder")
        self.sbQueueSize.grid(column=0,row=0)
        self.sbCount = Label(StatusBar, text = "Placeholder")
        self.sbCount.grid(column=1,row=0)
        self.sbBase = Label(StatusBar, text = "Placeholder")
        self.sbBase.grid(column=2,row=0)

        self.update_status()
        self.monitor_crafts()

    def update_status(self): 
        self.root.after(10,self.sbQueueSize.config(text=str(self.tracker.queue_size()) + " in queue\t\t"))
        self.root.after(10,self.sbBase.config(text="Center: " + str(self.tracker._base) + "Radius: " + str(self.tracker._radius)))
        if self.tracker.queue_size():
            self.latest_state = self.tracker.pull_data()
        self.root.after(10,self.sbCount.config(text = "API Calls: " + str(self.tracker.call_count()) + "\t\t"))
        self.root.after(200, self.update_status)

    def monitor_crafts(self):
        if len(self.latest_state) > 0:
            if self.cpList.curselection():
                self.target_craft = str(self.cpList.get(self.cpList.curselection()[0]))
            self.canvas.itemconfig("craft", fill="#222222", outline="#222222")
            if self.target_craft: 
                self.canvas.itemconfig(self.target_craft, fill="#FF00DD", outline="#FF00DD")
            for item in self.latest_state: 
                if str(item.callsign) == "":
                    pass
                cx,cy = item.latitude, item.longitude
                bx,by = self.tracker._base
                iy,ix = 400*(bx-cx)+300, 400*(cy-by)+300
                self.canvas.create_rectangle(ix-2,iy-2,ix+2,iy+2,fill="#FFFFFF",outline="#FFFFFF", tags=("craft", str(item.callsign)))
                if str(item.callsign) not in self.craftlist and str(item.callsign) != "":
                    self.craftlist.append(str(item.callsign))
                    self.craftstrval.set(self.craftlist)
                    self.canvas.create_text(ix,iy,text=item.callsign)
        self.root.after(1000, self.monitor_crafts)

    def api_start(self):
        self.tracker.start()

    def api_stop(self):
        self.tracker.stop()