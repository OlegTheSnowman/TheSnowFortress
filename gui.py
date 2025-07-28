import wx
import os
import threading
import config_manager
from soundpack_manager import SoundpackManager
import settings_dialog
from logger import log

class MainFrame(wx.Frame):
    # ... (the rest of the __init__ and InitUI code is the same as the previous step) ...
    # ... (I'm omitting it here for brevity, but make sure you replace the whole file) ...
    def __init__(self, parent):
        super(MainFrame, self).__init__(parent)
        log.debug("MainFrame initializing.")
        self.is_running = False
        self.worker_thread = None
        self.cancellation_event = threading.Event()
        self.configs = config_manager.load_configs()
        self.current_client_name = self.configs.get('last_selected_client', 'MUSHclient')
        self.InitUI()
        self.MakeMenu()
        self.SetSize((600, 450))
        self.SetTitle("Soundpack Updater")
        self.Centre()
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def InitUI(self):
        # This code is unchanged from the previous working accessibility version
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        client_sizer = wx.BoxSizer(wx.HORIZONTAL)
        client_label = wx.StaticText(panel, label="&Client:")
        client_choices = list(self.configs.get('clients', {}).keys())
        self.client_combo = wx.ComboBox(panel, choices=client_choices, style=wx.CB_READONLY)
        if self.current_client_name in client_choices: self.client_combo.SetValue(self.current_client_name)
        client_sizer.Add(client_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        client_sizer.Add(self.client_combo, 1, wx.EXPAND | wx.ALL, 5)
        vbox.Add(client_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_label = wx.StaticText(panel, label="Soundpack &Path:")
        self.path_text = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_MULTILINE)
        path_sizer.Add(path_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        path_sizer.Add(self.path_text, 1, wx.EXPAND | wx.ALL, 5)
        self.locate_button = wx.Button(panel, label="&Locate...")
        path_sizer.Add(self.locate_button, 0, wx.ALL, 5)
        vbox.Add(path_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.install_button = wx.Button(panel, label="&Install")
        self.update_button = wx.Button(panel, label="&Update")
        self.cancel_button = wx.Button(panel, label="&Cancel")
        self.cancel_button.Hide()
        self.button_sizer.Add(self.install_button, 1, wx.EXPAND | wx.RIGHT, 5)
        self.button_sizer.Add(self.update_button, 1, wx.EXPAND | wx.LEFT, 5)
        self.button_sizer.Add(self.cancel_button, 1, wx.EXPAND)
        vbox.Add(self.button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.progress_bar = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)
        vbox.Add(self.progress_bar, 0, wx.EXPAND | wx.ALL, 10)
        log_label = wx.StaticText(panel, label="Log:")
        self.log_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vbox.Add(log_label, 0, wx.LEFT, 15)
        vbox.Add(self.log_text, 1, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(vbox)
        self.client_combo.Bind(wx.EVT_COMBOBOX, self.OnClientChange)
        self.locate_button.Bind(wx.EVT_BUTTON, self.OnLocate)
        self.install_button.Bind(wx.EVT_BUTTON, self.OnInstall)
        self.update_button.Bind(wx.EVT_BUTTON, self.OnUpdate)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.UpdatePathFromConfig()

    def MakeMenu(self):
        # Unchanged
        fileMenu = wx.Menu()
        settings_item = fileMenu.Append(-1, "&Settings...\tCtrl+,", "Open client settings")
        reset_item = fileMenu.Append(-1, "&Reset All Settings", "Reset all configurations to factory defaults")
        fileMenu.AppendSeparator()
        exit_item = fileMenu.Append(wx.ID_EXIT)
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, "&File")
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.OnOpenSettings, settings_item)
        self.Bind(wx.EVT_MENU, self.OnResetSettings, reset_item)
        self.Bind(wx.EVT_MENU, self.OnExit, exit_item)

    def SetUIMode(self, mode):
        log.info(f"Setting UI mode to: {mode}")
        self.is_running = (mode == 'running')
        self.install_button.Show(not self.is_running)
        self.update_button.Show(not self.is_running)
        self.cancel_button.Show(self.is_running)
        self.locate_button.Enable(not self.is_running)
        self.client_combo.Enable(not self.is_running)
        self.GetMenuBar().EnableTop(0, not self.is_running)
        self.button_sizer.Layout()

    def OnTaskFinished(self):
        log.info("Worker thread has finished.")
        self.SetUIMode('idle')
        self.worker_thread = None
        self.progress_bar.SetValue(0)
        self.cancel_button.Enable(True)

    def worker_target(self, manager):
        log.debug("Worker thread target started.")
        try:
            manager.run_update_or_install()
        finally:
            wx.CallAfter(self.OnTaskFinished)

    def PerformAction(self):
        log.info("PerformAction called.")
        client_config = config_manager.get_client_config(self.current_client_name)
        if not client_config.get('soundpack_path') or not os.path.isdir(client_config.get('soundpack_path')):
            wx.MessageBox("Please locate a valid soundpack directory first.", "Error", wx.OK | wx.ICON_ERROR)
            return

        self.SetUIMode('running')
        self.log_text.Clear()
        self.cancellation_event.clear()

        manager = SoundpackManager(client_config, self.cancellation_event, self.ProgressUpdate)
        self.worker_thread = threading.Thread(target=self.worker_target, args=(manager,))
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def ProgressUpdate(self, data): wx.CallAfter(self._ProgressUpdateUI, data)

    def _ProgressUpdateUI(self, data):
        if 'message' in data and data['message']: self.log_text.AppendText(data['message'] + '\n')
        if data.get('total') and data.get('total') > 0:
            self.progress_bar.SetValue(int((data.get('value', 0) / data.get('total')) * 100))
        else:
            self.progress_bar.Pulse()

    def OnClose(self, event):
        log.debug("OnClose event triggered.")
        if self.is_running:
            with wx.MessageDialog(self, "A process is currently running. Are you sure you want to exit?", "Confirm Exit", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING) as dlg:
                if dlg.ShowModal() == wx.ID_NO:
                    event.Veto()
                    return
            self.cancellation_event.set()
        self.Destroy()

    def OnExit(self, event): self.Close()
    def OnInstall(self, event): self.PerformAction()
    def OnUpdate(self, event): self.PerformAction()

    def OnCancel(self, event):
        if self.is_running:
            log.info("Cancel button clicked by user.")
            self.log_text.AppendText("--- CANCELLATION SIGNAL SENT ---\n")
            self.cancellation_event.set()
            self.cancel_button.Enable(False)

    def OnOpenSettings(self, event):
        log.debug("Opening settings dialog.")
        self.configs = config_manager.load_configs()
        dlg = settings_dialog.SettingsDialog(self, self.current_client_name)
        dlg.ShowModal()
        dlg.Destroy()
        self.configs = config_manager.load_configs()
        self.UpdatePathFromConfig()

    def OnResetSettings(self, event):
        log.warning("User initiated a settings reset.")
        with wx.MessageDialog(self, "This will erase all custom paths and settings. Are you sure?", "Confirm Reset", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING) as dlg:
            if dlg.ShowModal() == wx.ID_YES:
                log.warning("Settings reset confirmed.")
                self.configs = config_manager.reset_to_defaults()
                wx.CallAfter(self.log_text.AppendText, "All settings have been reset to factory defaults.\n")
                self.current_client_name = self.configs.get('last_selected_client', '')
                self.client_combo.SetValue(self.current_client_name)
                self.UpdatePathFromConfig()

    def OnClientChange(self, event):
        self.current_client_name = self.client_combo.GetValue()
        log.info(f"Client changed to: {self.current_client_name}")
        config_manager.set_last_selected_client(self.current_client_name)
        self.UpdatePathFromConfig()

    def OnLocate(self, event):
        log.debug("Locate button clicked.")
        current_path = self.path_text.GetValue()
        dlg = wx.DirDialog(self, "Choose the soundpack directory", defaultPath=current_path if os.path.isdir(current_path) else '', style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            log.info(f"New path located: {path}")
            config_manager.update_config_value(self.current_client_name, 'soundpack_path', path)
            self.UpdatePathFromConfig()
        dlg.Destroy()

    def UpdatePathFromConfig(self):
        client_config = config_manager.get_client_config(self.current_client_name)
        path = client_config.get('soundpack_path', 'Not set')
        self.path_text.SetValue(path)
        is_path_set = os.path.isdir(path)
        self.install_button.Enable(is_path_set)
        self.update_button.Enable(is_path_set)