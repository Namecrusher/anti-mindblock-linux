import sys
import os
import subprocess
import re
import shutil
import threading
import time
import json

from pynput import keyboard
from PIL import Image, UnidentifiedImageError
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QAction, QMenu
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt

australiamode = False


def run_command(command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()

def extract_profile_names(text):
        pattern = r"Profile for '(.+)'"
        matches = re.findall(pattern, text)
        return matches

def get_active_monitors():
    xrandr_output = subprocess.run(['xrandr'], capture_output=True, text=True)
    if xrandr_output.returncode == 0:
        lines = xrandr_output.stdout.splitlines()
        active_monitors = []
        for line in lines:
            if ' connected' in line:
                parts = line.split()
                monitor_name = parts[0]
                active_monitors.append(monitor_name)
        return active_monitors

def get_monitor_orientation(monitor_info):
    pattern = r"\(\S+ (\S+)"
    match = re.search(pattern, monitor_info)
    if match:
        orientation = match.group(1)
        return orientation

def extract_tablet_info(text):
        pattern = r"Tablet area: \[(\d+(\.\d+)?)x(\d+(\.\d+)?)@<(\d+(\.\d+)?), (\d+(\.\d+)?)>:(-?\d+°)\]"
        match = re.search(pattern, text)
        if match:
            width = float(match.group(1))
            height = float(match.group(3))
            x_coord = float(match.group(5))
            y_coord = float(match.group(7))
            rotation = int(match.group(9)[:-1])
            
            return width, height, x_coord, y_coord, rotation

def process_image(image_path, temp_image_path, rotate=False, transparency=False):
    try:
        if rotate:
            with Image.open(image_path) as img:
                img_rotated = img.rotate(180)
                img_rotated.save(image_path)
        if transparency:
            with Image.open(image_path) as img:
                transparent_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
                transparent_img.save(image_path)
        if not rotate and not transparency:
            # Restore process
            shutil.copy2(temp_image_path, image_path)
    except Exception as e:
        print(f"Error processing file {image_path}: {e}")

def focus_window(window_title):
    subprocess.run(["xdotool", "search", "--name", window_title, "windowactivate"])

def press_keys(keys):
    for key in keys:
        subprocess.run(["xdotool", "keydown", key])
    for key in keys:
        subprocess.run(["xdotool", "keyup", key])

tabletnames = extract_profile_names(run_command("otd getallsettings"))
active_monitors = get_active_monitors()




class MainUI(QMainWindow):
    def __init__(self):
        super(MainUI, self).__init__()
        loadUi("australia.ui", self)
        self.rotateScreen.clicked.connect(self.rotatetabletanddisplay)
        for i in range(len(tabletnames)):
            self.tabletselect.addItem(tabletnames[i])
        for i in range(len(active_monitors)):
            self.displayselect.addItem(active_monitors[i])
        self.browse.clicked.connect(self.browse_directory)
        self.scanfolder.clicked.connect(self.scanskins)
        self.backupskin.clicked.connect(self.backup_skin)
        self.revertnumbers.clicked.connect(self.restore_skin)
        self.rotatenumbers.clicked.connect(self.rotate_images)
        self.activateaustralia.clicked.connect(self.activate_australia_mode)
        self.deactivateaustralia.clicked.connect(self.deactivate_australia_mode)
        self.actionSave_Config.triggered.connect(self.save_config)
        self.actionLoad_Config.triggered.connect(self.load_config)
        self.hotkeybutton.clicked.connect(self.hotkeybuttonpress)

    def run(self):
        with keyboard.GlobalHotKeys({
                '<ctrl>+<shift>+a': self.activate_australia_mode,
                '<ctrl>+<shift>+d': self.deactivate_australia_mode}) as h:
            h.join()
    def hotkeybuttonpress(self):
        hotkey_thread = threading.Thread(target=self.run, daemon=True)       
        hotkey_thread.start()  


    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.osudirectory.setText(directory)

    def scanskins(self):
        osu_directory = self.osudirectory.text()
        skins_directory = os.path.join(osu_directory, 'Skins')
        user_cfg_path = os.path.join(osu_directory, f'osu!.{run_command("echo $USER")}.cfg')
        if os.path.exists(user_cfg_path):
                with open(user_cfg_path, 'r') as file:
                    for line in file:
                        if line.strip().startswith('Skin ='):
                            current_skin = line.split('=')[1].strip()

        else:
            print("fix ur osu path")
        if os.path.exists(skins_directory):
            skins = [name for name in os.listdir(skins_directory) if os.path.isdir(os.path.join(skins_directory, name))]
            skins.sort()
            self.osuskin.clear()
            for skin in skins:
                self.osuskin.addItem(skin)
            self.osuskin.setCurrentIndex(self.osuskin.findText(current_skin))
    
    def backup_skin(self):
        current_skin = self.osuskin.currentText()
        osu_directory = self.osudirectory.text()
        skins_directory = os.path.join(osu_directory, 'Skins')
        current_skin_directory = os.path.join(skins_directory, current_skin)
        backup_path = current_skin_directory + '_backup'
        if not os.path.exists(backup_path):
            def perform_backup():
                shutil.copytree(current_skin_directory, backup_path)
                print("Backup created at:", backup_path)
            backup_thread = threading.Thread(target=perform_backup)
            backup_thread.start()
        else:
            print("Backup already exists.")

    def restore_skin(self):      
        current_skin = self.osuskin.currentText()
        osu_directory = self.osudirectory.text()
        skins_directory = os.path.join(osu_directory, 'Skins')
        current_skin_directory = os.path.join(skins_directory, current_skin)       
        backup_path = current_skin_directory + '_backup'
        if os.path.exists(backup_path):
            shutil.rmtree(current_skin_directory)
            shutil.copytree(backup_path, current_skin_directory)
            print("Skin restored from backup.")
            osu_window_title = "osu!"
            focus_window(osu_window_title)
            time.sleep(0.5)
            keys_to_press = ["Control_L", "Alt_L", "Shift_L", "s"]
            press_keys(keys_to_press)

    def rotate_images(self):
        current_skin = self.osuskin.currentText()
        restore=False
        osu_directory = self.osudirectory.text()
        skins_directory = os.path.join(osu_directory, 'Skins')
        skin_path = os.path.join(skins_directory, current_skin)
        print(f"Attempting to access skin path: {skin_path}")
        if not skin_path:
            print("No skin path provided.")
            return

        rotate_prefixes = ["default-", "cursor", "spinner", "slider", "play-skip", "hit", "ranking", "section"]
        transparency_prefixes = ["score", "scorebar"]

        skin_ini_path = os.path.join(skin_path, "skin.ini")
        if os.path.exists(skin_ini_path):
            with open(skin_ini_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith('HitCirclePrefix:'):
                        rotate_prefixes.append(line.split(':')[1].strip() + '-')
                    if line.startswith('ScorePrefix:'):
                        transparency_prefixes.append(line.split(':')[1].strip())

        temp_folder_path = os.path.join(skin_path, "temp_australia_mode")
        if not os.path.exists(temp_folder_path):
            os.makedirs(temp_folder_path)

        for root, dirs, files in os.walk(skin_path):
            if root.endswith("temp_australia_mode"):  # Ignore temp directory itself
                continue
            for file in files:
                if file.endswith(".png"):
                    image_path = os.path.join(root, file)
                    temp_image_path = os.path.join(temp_folder_path, file)
                    if any(file.startswith(prefix) for prefix in rotate_prefixes) and not any(file.startswith(prefix) for prefix in transparency_prefixes):
                        process_image(image_path, temp_image_path, rotate=not restore)
                    elif any(file.startswith(prefix) for prefix in transparency_prefixes):
                        process_image(image_path, temp_image_path, transparency=True, rotate=not restore)


    def rotatetabletanddisplay(self):
        selectedtablet = self.tabletselect.currentText()
        selectedmonitor = self.displayselect.currentText()
        orientation = get_monitor_orientation(run_command("xrandr --verbose | grep -w " + self.displayselect.currentText()))
        tablet_info = extract_tablet_info(run_command('otd getareas "' + selectedtablet + '"'))
        tablet_width, tablet_height, tablet_x, tablet_y, tablet_rotation = tablet_info
        tablet_rotation = (tablet_rotation + 180)%360
        os.system("otd settabletarea "+ '"' + str(selectedtablet) + '" ' + str(tablet_width) + " " + str(tablet_height) + " " + str(tablet_x) + " " + str(tablet_y) + " " + str(tablet_rotation))
        if orientation == "normal":
            os.system("xrandr --output " + selectedmonitor + " --rotate inverted")
        elif orientation == "inverted":
            os.system("xrandr --output " + selectedmonitor + " --rotate normal")
        elif orientation == "left":
            os.system("xrandr --output " + selectedmonitor + " --rotate right")
        else:
            os.system("xrandr --output " + selectedmonitor + " --rotate left")
    

    def deactivate_australia_mode(self):
        global australiamode
        if australiamode == True:
            australiamode = False
            self.restore_skin()
            self.rotatetabletanddisplay()
            osu_window_title = "osu!"
            focus_window(osu_window_title)
            time.sleep(0.5)
            keys_to_press = ["Control_L", "Alt_L", "Shift_L", "s"]
            press_keys(keys_to_press)

    def activate_australia_mode(self):
        global australiamode
        if australiamode == False:
            australiamode = True
            self.rotate_images()
            self.rotatetabletanddisplay()
            osu_window_title = "osu!"
            focus_window(osu_window_title)
            time.sleep(0.5)
            keys_to_press = ["Control_L", "Alt_L", "Shift_L", "s"]
            press_keys(keys_to_press)


    def save_config(self):
        config = {
            'osudir': self.osudirectory.text(),
            'display': self.displayselect.currentText(),
            'tablet': self.tabletselect.currentText(),
            # Add more config options as needed
        }
        with open('config.json', 'w') as f:
            json.dump(config, f)

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            # Apply loaded config to your application    
            self.osudirectory.setText(config['osudir'])
            self.tabletselect.setCurrentIndex(self.tabletselect.findText(config['tablet']))
            self.displayselect.setCurrentIndex(self.displayselect.findText(config['display']))
            self.scanskins()
        except FileNotFoundError:
            print('Config file not found.')

    

    


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = MainUI()
    ui.show()
    app.exec_()


          