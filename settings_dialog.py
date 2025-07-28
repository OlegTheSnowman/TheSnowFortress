import wx
import config_manager
from logger import log

class SettingsDialog(wx.Dialog):
    # This file remains mostly the same, just adding log messages
    # ... (rest of the code is unchanged from the last working version) ...
    def __init__(self, parent, client_name):
        super(SettingsDialog, self).__init__(parent, title=f"Settings for {client_name}")
        log.debug(f"SettingsDialog initialized for client: {client_name}")
        self.client_name = client_name
        self.all_configs = config_manager.load_configs()
        self.client_config = self.all_configs.get('clients', {}).get(client_name, {})
        self.InitUI()
        self.SetSizerAndFit(self.main_sizer)
        self.Centre()

    def OnSave(self, event):
        log.info(f"Saving settings for client: {self.client_name}")
        for key, control in self.general_controls.items():
            self.client_config[key] = control.GetValue()
        self.client_config["exclusions"] = [line.strip() for line in self.exclusions_control.GetValue().split('\n') if line.strip()]
        adv_settings = {
            "advanced_enabled": self.enable_checkbox.IsChecked(),
            "scan_workers": self.scan_workers_spin.GetValue(),
            "download_workers": self.dl_workers_spin.GetValue()
        }
        self.client_config["advanced_settings"] = adv_settings
        self.all_configs['clients'][self.client_name] = self.client_config
        config_manager.save_configs(self.all_configs)
        self.EndModal(wx.ID_OK)

    # The rest of this file (InitUI, CreateGeneralTab, etc.) is unchanged.
    # I am omitting it for brevity but you should replace the entire file.
    def InitUI(self):
        # Unchanged
        self.main_sizer=wx.BoxSizer(wx.VERTICAL);panel=wx.Panel(self);notebook=wx.Notebook(panel);self.CreateGeneralTab(notebook);self.CreateAdvancedTab(notebook);sizer=wx.BoxSizer(wx.VERTICAL);sizer.Add(notebook,1,wx.EXPAND|wx.ALL,5);panel.SetSizer(sizer);self.main_sizer.Add(panel,1,wx.EXPAND|wx.ALL,10);btn_sizer=self.CreateButtonSizer(wx.OK|wx.CANCEL);save_button=self.FindWindowById(wx.ID_OK);save_button.SetLabel("Save");self.main_sizer.Add(btn_sizer,0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,10);self.Bind(wx.EVT_BUTTON,self.OnSave,id=wx.ID_OK)
    def CreateGeneralTab(self,notebook):
        # Unchanged
        panel=wx.Panel(notebook);grid=wx.FlexGridSizer(5,2,10,10);fields={"scripts_repo_url":"Scripts Repo URL:","sounds_repo_url":"Sounds Repo URL:","scripts_target_subdir":"Scripts Target Subdirectory:","sounds_target_subdir":"Sounds Target Subdirectory:","sounds_subfolder":"Repo Sounds Subfolder (e.g., ogg):"};self.general_controls={};[self.general_controls.update({key:wx.TextCtrl(panel,value=str(self.client_config.get(key,"")),name=text)})or grid.Add(wx.StaticText(panel,label=text),0,wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)or grid.Add(self.general_controls[key],1,wx.EXPAND)for key,text in fields.items()];label=wx.StaticText(panel,label="Exclusions (one per line):");value="\n".join(self.client_config.get("exclusions",[]));control=wx.TextCtrl(panel,value=value,style=wx.TE_MULTILINE);self.exclusions_control=control;main_sizer=wx.BoxSizer(wx.VERTICAL);main_sizer.Add(grid,0,wx.EXPAND|wx.ALL,10);main_sizer.Add(label,0,wx.LEFT|wx.RIGHT|wx.TOP,10);main_sizer.Add(control,1,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,10);grid.AddGrowableCol(1,1);panel.SetSizer(main_sizer);notebook.AddPage(panel,"General")
    def CreateAdvancedTab(self,notebook):
        # Unchanged
        panel=wx.Panel(notebook);adv_settings=self.client_config.get("advanced_settings",{});warning_text="WARNING: Modifying these settings can significantly increase CPU, memory, and network usage. Proceed with caution.";warning_field=wx.TextCtrl(panel,value=warning_text,style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_NO_VSCROLL);warning_field.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK));self.enable_checkbox=wx.CheckBox(panel,label="I understand the risks and wish to change advanced settings.");self.enable_checkbox.SetValue(adv_settings.get("advanced_enabled",False));grid=wx.FlexGridSizer(2,2,10,10);scan_label=wx.StaticText(panel,label="File Scan Workers:");self.scan_workers_spin=wx.SpinCtrl(panel,value=str(adv_settings.get("scan_workers",4)),min=1,max=16);dl_label=wx.StaticText(panel,label="Parallel Download Workers:");self.dl_workers_spin=wx.SpinCtrl(panel,value=str(adv_settings.get("download_workers",8)),min=1,max=32);grid.Add(scan_label,0,wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL);grid.Add(self.scan_workers_spin,0);grid.Add(dl_label,0,wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL);grid.Add(self.dl_workers_spin,0);main_sizer=wx.BoxSizer(wx.VERTICAL);main_sizer.Add(warning_field,0,wx.EXPAND|wx.ALL,10);main_sizer.Add(self.enable_checkbox,0,wx.ALL,10);main_sizer.Add(grid,0,wx.ALL,10);panel.SetSizer(main_sizer);notebook.AddPage(panel,"Advanced");self.Bind(wx.EVT_CHECKBOX,self.OnToggleAdvanced,self.enable_checkbox);self.OnToggleAdvanced(None)
    def OnToggleAdvanced(self,event):
        # Unchanged
        enabled=self.enable_checkbox.IsChecked();self.scan_workers_spin.Enable(enabled);self.dl_workers_spin.Enable(enabled)