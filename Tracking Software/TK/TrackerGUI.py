import logging
import tkinter as tk
from tkinter import Menu
from tkinter import ttk
from tkinter import *
from tkinter.ttk import *
import TrackingSupport.OpenSkyAPIHandler as OpenSkyAPIHandler

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
        self.cpTableSort = ""
        self.cpTableSort2 = True
        self.apiGroundFilter = BooleanVar(value=False)

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
        label_panel_l.grid(column=0,row=0, columnspan=2)
        self.lpStart = Button(panel_l, text="Start API", command=self.api_start)
        self.lpStart.grid(column=0,row=1, columnspan=2)
        self.lpStop = Button(panel_l, text="Stop API", command=self.api_stop)
        self.lpStop.grid(column=0,row=2, columnspan=2)
        self.lpGroundChk = Checkbutton(panel_l, text="Hide ground", variable=self.apiGroundFilter)
        self.lpGroundChk.grid(column=0,row=3, columnspan=2)


        craftPanel = Frame(mainframe, padding=(3,3,12,12))
        craftPanel.grid(column=6,row=0, sticky=N)
        self.craftstrval = StringVar(value=self.craftlist)    
        self.cpTable = Treeview(craftPanel, columns=("ICAO","Callsign","LAT","LON","Squawk"), show="headings",height=30)
        self.cpTable.column("ICAO", width=50, stretch=tk.NO)
        self.cpTable.heading("ICAO", text="ICAO24", command=lambda: self.treeview_sort(self.cpTable, "ICAO", False))
        self.cpTable.column("Callsign", width=65, stretch=tk.NO)
        self.cpTable.heading("Callsign", text="Callsign", command=lambda: self.treeview_sort(self.cpTable, "Callsign", False))
        self.cpTable.column("LAT", width=65, stretch=tk.NO)
        self.cpTable.heading("LAT", text="LAT")
        self.cpTable.column("LON", width=65, stretch=tk.NO)
        self.cpTable.heading("LON", text="LON")
        self.cpTable.column("Squawk", width=50, stretch=tk.NO)
        self.cpTable.heading("Squawk", text="Squawk", command=lambda: self.treeview_sort(self.cpTable, "Squawk", False))
        self.cpTable.grid(column=0, row=1)
        
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
        
        ### New data
        if len(self.latest_state) > 0:

            ### Hide old data for all crafts and callsigns
            for box in self.canvas.find_withtag("latest"):
                curr = self.canvas.gettags(box)
                new_tags = [tag if tag != "latest" else "historical" for tag in curr]
                self.canvas.itemconfig(box, tags = tuple(new_tags))
            self.canvas.itemconfig("historical", state="hidden")
 
            for item in self.latest_state: 
                ### Ignore empty callsigns or grounded planes
                if str(item.callsign) == "":
                    continue
                if item.on_ground and self.apiGroundFilter.get():
                    continue

                ### Have we seen it before? If not, add to table 
                if str(item.callsign) not in self.craftlist and str(item.callsign) != "":
                    self.craftlist.append(str(item.callsign))
                    self.craftstrval.set(self.craftlist)
                    self.cpTable.insert("",tk.END,values=(item.icao24, str(item.callsign), item.latitude, item.longitude, item.squawk))
                
                
                ### Adding latest indications into the canvas
                cx,cy = item.latitude, item.longitude
                bx,by = self.tracker._base
                iy,ix = 400*(bx-cx)+300, 400*(cy-by)+300
                self.canvas.create_rectangle(ix-2,iy-2,ix+2,iy+2,fill="#FFFFFF",outline="#FFFFFF", tags=(f"craft{str(item.callsign)}", "latest", "craft"))
                self.canvas.create_text(ix+30,iy,text=item.callsign, tags=(f"callsign{str(item.callsign)}", "callsign", "latest"))
        
        ###Every cycle confirm if target is selected and change to pink and make all visible
        if self.cpTable.selection():
            for target in self.cpTable.selection():
                data = self.cpTable.item(target)
                temp_target = data["values"][1]
                self.canvas.itemconfig(f"craft{str(temp_target)}", fill="#042912", outline="#042912", state="normal")
                self.canvas.tag_raise(f"craft{str(temp_target)}")
                self.canvas.itemconfig(f"craft{str(temp_target)}&&latest", fill="#FFFF00", outline="#FFFF00", state="normal")

        ### sort table again after all the new data has been entered.
        if self.cpTableSort:
            self.treeview_sort(self.cpTable, self.cpTableSort, self.cpTableSort2)
        ### Recheck after some time (this is "loop")
        self.root.after(500, self.monitor_crafts)

    def dump_canvas(self):
        self.data_dump = []
        all_ids = self.canvas.find_all()
        for obj in all_ids:
            self.data_dump.append((obj, self.canvas.type(obj), self.canvas.gettags(obj)))
        print("hello")

    def api_start(self):
        self.tracker.start()

    def api_stop(self):
        self.tracker.stop()

    def treeview_sort(self, tree, col, descending):
        self.cpTableSort = col
        self.cpTableSort2 = descending
        data = [(tree.set(item_id, col), item_id) for item_id in tree.get_children('')]
        data.sort(reverse=descending)
        for index, (val, item_id) in enumerate(data):
            tree.move(item_id, '', index)
        tree.heading(col, command=lambda: self.treeview_sort(tree, col, not descending))