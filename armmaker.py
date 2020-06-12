from tkinter import *
from tkinter import ttk
from tkinter import simpledialog

import collections
from threading import Timer

ARMObject = collections.namedtuple(
    'ARMObjet', ['deployment', 'classes', 'name', 'content']
)

class ARMModel():
    def __init__(self):
        self._observers = set()
        self._objects = {
            'ring-size': ARMObject('<default>', ('Parameter',), 'ring-size', None),
            'cassandra-vnet': ARMObject('<default>', ('Resource', 'VNet'), 'cassandra-vnet', None),
            'cassandra-nsg': ARMObject('<default>', ('Resource', 'Network Security Group'), 'cassandra-nsg', None),
            'data-subnet': ARMObject('stress-set', ('Parameter',), 'data-subnet', None),
        }
        self._deployments = sorted({obj.deployment for obj in self._objects.values()})

        
    def filename(self):
        return None
    
    def deployments(self):
        return sorted(self._deployments)

    def add_deployment(self, name):
        if name in self._deployments:
            raise ValueError(f'There is already a deployment named {name}.')
        self._deployments = sorted(self._deployments + [name])
        self.update()
    
    def subscribe(self, observer):
        self._observers.add(observer)
        
    def update(self):
        for observer in self._observers:
            observer.update()

    def kinds(self):
        return {
            "Parameter": {},
            "Variable": {},
            "Function": {},
            "Resource": {
                "VNet": {},
                "Network Security Group": {},
            },
        }

    def add_object(self, deployment, kind, name):
        if name in self._objects:
            raise ValueError(f'Template already has an object named {name}.')
        if kind == 'Resource':
            raise ValueError(f'Select a specific kind of resource to create.')
        if kind not in ['Parameter', 'Variable', 'Function']:
            classes = (kind, 'Resource')
        else:
            classes = (kind,)
            
        self._objects[name] = ARMObject(
            deployment=deployment,
            classes=classes,
            name=name,
            content=None
        )
        self.update()

    def objects(self, selected_deployments, selected_kinds, filter_text):
        def matches(object):
            return (object.deployment in selected_deployments) \
                   and any(kind in selected_kinds for kind in object.classes) \
                   and (filter_text in object.name)
        return sorted(object.name for object in self._objects.values() if matches(object))
           

class AutoScrollbar(ttk.Scrollbar):
    # a scrollbar that hides itself if it's not needed.  only
    # works if you use the grid geometry manager.
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            # grid_remove is currently missing from Tkinter!
            self.tk.call("grid", "remove", self)
        else:
            self.grid()
        Scrollbar.set(self, lo, hi)

class ARMBrowser(Toplevel):
    def __init__(self, master, model, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky=(N,S,E,W))
        for row in [0, 1]:
            frame.grid_rowconfigure(row, weight=1)
        for column in [0, 1, 2]:
            frame.grid_columnconfigure(column, weight=1)

        self.status_var = StringVar()
        self.deployments_var = Variable()
        self.objects_var = Variable()
        self.filter_var = StringVar()
        
        deployments, self.deployments_listbox = self.deployments_widget(frame, self.deployments_var)
        deployments.grid(row=0, column=0, sticky=(N,S,E,W))

        kinds, self.classes_treeview = self.kinds_widget(frame)
        kinds.grid(row=0, column=1, sticky=(N,S,E,W))

        objects = self.items_widget(frame, self.objects_var, self.filter_var)
        objects.grid(row=0, column=2, sticky=(N,S,E,W))

        content = self.content_widget(frame)
        content.grid(row=1, column=0, columnspan=3, sticky=(N,S,E,W))

        statusBar = ttk.Label(frame, textvariable=self.status_var)
        statusBar.grid(row=2, column=0, columnspan=3, sticky=W)
        
        self.model = model
        model.subscribe(self)
        model.update()

    def deployments_widget(self, master, viewmodel):
        frame = ttk.Frame(master)
        for row, weight in [(0, 0), (1, 1), (2, 0), (3,0)]:
            frame.grid_rowconfigure(row, weight=weight)
        for column, weight in [(0, 1), (1, 0)]:
            frame.grid_columnconfigure(column, weight=weight)
            
        label = ttk.Label(frame, text="Deployments")
        label.grid(row=0, column=0, columnspan=2)

        xscrollbar = AutoScrollbar(frame, orient=HORIZONTAL)
        xscrollbar.grid(row=2, column=0, sticky=(N,S,E,W))
        yscrollbar = AutoScrollbar(frame)
        yscrollbar.grid(row=1, column=1, sticky=(N,S,E,W))
        
        listbox = Listbox(
            frame, listvariable=viewmodel,
            xscrollcommand=xscrollbar.set,
            yscrollcommand=yscrollbar.set,
            selectmode='single',
            exportselection=False,
        )
        listbox.grid(row=1, column=0, sticky=(N,S,E,W))
        listbox.bind('<<ListboxSelect>>', self.update)

        xscrollbar.config(command=listbox.xview)
        yscrollbar.config(command=listbox.yview)

        def new_deployment():
            name = simpledialog.askstring('New Deployment', 'Name for deployment')
            if name is not None:
                try:
                    self.model.add_deployment(name)
                except ValueError as ve:
                    self.status_var.set('Error: ' + str(ve))
        
        button = ttk.Button(frame, text="New...", command=new_deployment)
        button.grid(row=3, column=0, columnspan=2, sticky=(E, W))

        return frame, listbox

    def kinds_widget(self, master):
        frame = ttk.Frame(master)
        for row, weight in [(0, 0), (1, 1), (2, 0), (3,0)]:
            frame.grid_rowconfigure(row, weight=weight)
        for column, weight in [(0, 1), (1, 0)]:
            frame.grid_columnconfigure(column, weight=weight)
            
        label = ttk.Label(frame, text="Classes")
        label.grid(row=0, column=0, columnspan=2)

        xscrollbar = AutoScrollbar(frame, orient=HORIZONTAL)
        xscrollbar.grid(row=2, column=0, sticky=(N,S,E,W))
        yscrollbar = AutoScrollbar(frame)
        yscrollbar.grid(row=1, column=1, sticky=(N,S,E,W))
        
        treeview = ttk.Treeview(
            frame,
            xscrollcommand=xscrollbar.set,
            yscrollcommand=yscrollbar.set,
            selectmode='extended',
            show='tree',
        )
        treeview.grid(row=1, column=0, sticky=(N,S,E,W))
        treeview.bind('<<TreeviewSelect>>', self.update)

        xscrollbar.config(command=treeview.xview)
        yscrollbar.config(command=treeview.yview)

        def new_item():
            if len(treeview.selection()) != 1:
                self.status_var.set(f'Select exactly one class to create an object of.')
                return
            if len(self.deployments_listbox.curselection()) != 1:
                self.status_var.set(f'Select exactly one deployment to create an object in.')
                return
            
            name = simpledialog.askstring('New Deployment', 'Name for deployment')
            kind = treeview.selection()[0]
            deployment = self.deployments_var.get()[self.deployments_listbox.curselection()[0]]

            try:
                self.model.add_object(deployment, kind, name)
            except ValueError as ve:
                self.status_var.set(str(ve))
        
        button = ttk.Button(frame, text="New...", command=new_item)
        button.grid(row=3, column=0, columnspan=2, sticky=(E, W))

        return frame, treeview

    def items_widget(self, master, listvar, entryvar):
        frame = ttk.Frame(master)
        for row, weight in [(0, 0), (1, 1), (2, 0), (3,0)]:
            frame.grid_rowconfigure(row, weight=weight)
        for column, weight in [(0, 1), (1, 0)]:
            frame.grid_columnconfigure(column, weight=weight)
            
        label = ttk.Label(frame, text="Objects")
        label.grid(row=0, column=0, columnspan=2)

        xscrollbar = AutoScrollbar(frame, orient=HORIZONTAL)
        xscrollbar.grid(row=2, column=0, sticky=(N,S,E,W))
        yscrollbar = AutoScrollbar(frame)
        yscrollbar.grid(row=1, column=1, sticky=(N,S,E,W))
        
        listbox = Listbox(
            frame, listvariable=listvar,
            xscrollcommand=xscrollbar.set,
            yscrollcommand=yscrollbar.set,
            selectmode='extended',
            exportselection=False,
        )
        listbox.grid(row=1, column=0, sticky=(N,S,E,W))

        xscrollbar.config(command=listbox.xview)
        yscrollbar.config(command=listbox.yview)

        entry = ttk.Entry(frame, textvariable=entryvar)
        entry.grid(row=3, column=0, columnspan=2, sticky=(E, W))
        def filter_changed(e):
            try:
                filter_changed.t.cancel()
            except AttributeError:
                pass
            filter_changed.t = Timer(0.1, self.update)
            filter_changed.t.start()
        entry.bind('<Key>', filter_changed)

        return frame

    def content_widget(self, master):
        frame = ttk.Frame(master)

        label = ttk.Label(frame, text='Name:')
        label.grid(row=0, column=0, sticky=(E,))

        entry = ttk.Entry(frame, textvariable=name_var)
        label.grid(row=0, column=1, sticky=(W,))

        return frame

    def selected_deployments(self):
        deployments = self.deployments_var.get()
        return [deployments[i] for i in self.deployments_listbox.curselection()]

    def update(self, *args, **kwargs):
        name = self.model.filename()
        self.title(f'ARM Maker - {name or "Untitled"}')
        self.deployments_var.set(list(self.model.deployments()))
        if not self.deployments_listbox.curselection():
            self.deployments_listbox.selection_set(0)

        to_insert = collections.deque()
        for i, (k, v) in enumerate(self.model.kinds().items()):
            to_insert.append((i, k, "", v))
        try:
            while True:
                (i, name, parent, children) = to_insert.popleft()
                if not self.classes_treeview.exists(name):
                    self.classes_treeview.insert(parent, i, name, text=name)
                for j, (k, v) in enumerate(children.items()):
                    to_insert.append((i, k, name, v))
        except IndexError:
            pass
        if not self.classes_treeview.selection():
            self.classes_treeview.selection_add('Resource')

        selected_kinds = self.classes_treeview.selection()
        filter_text = self.filter_var.get()
        items = self.model.objects(self.selected_deployments(), selected_kinds, filter_text)
        self.objects_var.set(items)




root = Tk()
# Don't use the root window that Tk() created,
# since we will have one window per file.
root.overrideredirect(1)
root.withdraw()

model = ARMModel()
browser = ARMBrowser(root, model)
root.mainloop()
