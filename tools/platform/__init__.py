import platform

# Expose OS-specific UI tools depending on current platform
if platform.system() == "Windows":
    from tools.platform.windows_ui import list_windows, focus_window, click_at, type_text
elif platform.system() == "Darwin":
    from tools.platform.macos_ui import list_windows, focus_window, click_menu_item, type_text
elif platform.system() == "Linux":
    from tools.platform.linux_desktop import take_screenshot
