from TK import TrackerGUI
import OpenSkyAPIHandler
import tkinter as tk

root = tk.Tk()
api = OpenSkyAPIHandler.Flight_API()

app = TrackerGUI.TrackerMainGUI(root, api)

root.mainloop()
