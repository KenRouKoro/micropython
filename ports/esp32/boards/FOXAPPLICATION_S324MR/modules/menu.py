import asyncio
import time

class Menu:
    def __init__(self, bsp):
        self.bsp = bsp
        self.oled = bsp.oled
        self.items = []
        self.current_index = 0
        self.window_start = 0
        self.visible_lines = 3 # 128x32 display, maybe 3-4 lines of text. 32px / 8px/line = 4 lines.
        self.in_edit_mode = False
        self.stack = [] # Stack for submenus: (items, current_index, window_start)
        
        # Screen Saver
        self.screen_saver_enabled = True
        self.screen_saver_timeout = 60 # seconds
        self.screen_on = True
        self.last_interaction_time = time.time()
        
        # Acceleration
        self.key_press_start_time = 0
        self.acceleration_factor = 1
        
    def add_item(self, text, callback=None, type="action", value=None, min_val=None, max_val=None, step=1, options=None, submenu=None, format_cb=None, key=None):
        """
        Add a menu item.
        
        Args:
            text: Display text
            callback: Function to call when activated (for action) or value changed (for data)
            type: 'action', 'bool', 'int', 'float', 'option', 'submenu', 'progress'
            value: Initial value
            min_val: Minimum value for int/float/progress
            max_val: Maximum value for int/float/progress
            step: Step size for int/float
            options: List of strings for 'option' type
            submenu: List of items for 'submenu' type
            format_cb: Optional function to format value for display (takes value, returns string)
            key: Optional internal key to identify this item (e.g. for config sync)
        """
        item = {
            "text": text,
            "callback": callback,
            "type": type,
            "value": value,
            "min": min_val,
            "max": max_val,
            "step": step,
            "options": options,
            "submenu": submenu,
            "format_cb": format_cb,
            "key": key
        }
        self.items.append(item)

    def add_submenu(self, text, key=None):
        """Helper to create a submenu item and return a list proxy to add items to it."""
        submenu_items = []
        self.add_item(text, type="submenu", submenu=submenu_items, key=key)
        return MenuProxy(submenu_items)
        
    def set_screen_saver(self, enabled, timeout=60):
        """Configure screen saver settings."""
        self.screen_saver_enabled = enabled
        self.screen_saver_timeout = timeout
        self._reset_interaction()

    def _reset_interaction(self):
        """Reset the interaction timer and ensure screen is on."""
        self.last_interaction_time = time.time()
        if not self.screen_on:
            self.screen_on = True
            if self.oled:
                self.oled.poweron()
                self.draw() # Redraw content

    def update_value(self, item_index, new_value):
        """Helper to update a value of an item dynamically (e.g. for progress bars)."""
        if 0 <= item_index < len(self.items):
             self.items[item_index]["value"] = new_value
             self.draw()

    def update_value_by_key(self, key, new_value):
        """Find an item by key in any (sub)menu and update its value."""
        if self._update_recursive(self.items, key, new_value):
            self.draw()

    def _update_recursive(self, items, key, value):
        for item in items:
            if item.get("key") == key:
                item["value"] = value
                return True
            if item["type"] == "submenu" and item["submenu"]:
                if self._update_recursive(item["submenu"], key, value):
                    return True
        return False

    def show_progress_dialog(self, title, value, max_value=100):
        """
        Draw a modal-like progress dialog centered on screen.
        Does not block, just draws once. Caller should call this in a loop.
        """
        if not self.oled or not self.screen_on:
            return
            
        self.oled.fill(0)
        
        # Center title
        title_width = len(title) * 8
        title_x = max(0, (128 - title_width) // 2)
        self.oled.text(title, title_x, 4)
        
        # Draw Progress Bar
        bar_x = 14
        bar_y = 18
        bar_w = 100
        bar_h = 8
        
        percent = max(0.0, min(1.0, value / max_value)) if max_value > 0 else 0
        
        self.oled.rect(bar_x, bar_y, bar_w, bar_h, 1) # Frame
        self.oled.fill_rect(bar_x + 2, bar_y + 2, int((bar_w - 4) * percent), bar_h - 4, 1) # Fill with padding
        
        self.oled.show()

    def draw(self):
        if not self.oled or not self.screen_on:
            return
            
        self.oled.fill(0)
        
        current_y = 0
        idx = self.window_start
        while idx < len(self.items) and current_y < 32:
            item = self.items[idx]
            line_height = 8
            if item["type"] == "progress":
                line_height = 16
            
            # Check if this item fits
            if current_y + line_height > 32:
                break
                
            prefix = ">" if idx == self.current_index else " "
            # Indicate edit mode (override prefix)
            if idx == self.current_index and self.in_edit_mode:
                prefix = "*"
            
            if item["type"] == "progress":
                # Draw Progress Bar
                # Line 1: Text + Value
                val = item["value"]
                min_v = item["min"] if item["min"] is not None else 0
                max_v = item["max"] if item["max"] is not None else 100
                percent = 0
                if max_v > min_v:
                    percent = (val - min_v) / (max_v - min_v)
                percent = max(0.0, min(1.0, percent))
                
                # Format value
                val_str = str(val)
                if item.get("format_cb"):
                    val_str = item["format_cb"](val)
                
                self.oled.text(f"{prefix}{item['text']}:{val_str}", 0, current_y)
                
                # Line 2: The Bar
                bar_x = 8 # Indent
                bar_y = current_y + 10
                bar_w = 110
                bar_h = 4
                self.oled.rect(bar_x, bar_y, bar_w, bar_h, 1) # Frame
                self.oled.fill_rect(bar_x, bar_y, int(bar_w * percent), bar_h, 1) # Fill
                
            else:
                # Standard Text Item
                display_text = item["text"]
                
                # Format value display based on type
                if item.get("format_cb"):
                    val_str = item["format_cb"](item["value"])
                    display_text = f"{item['text']}:{val_str}"
                elif item["type"] == "bool":
                    val_str = "ON" if item["value"] else "OFF"
                    display_text = f"{item['text']}:{val_str}"
                elif item["type"] == "int":
                    display_text = f"{item['text']}:{item['value']}"
                elif item["type"] == "float":
                    display_text = f"{item['text']}:{item['value']:.2f}"
                elif item["type"] == "option":
                    opt_idx = item["value"]
                    if item["options"] and 0 <= opt_idx < len(item["options"]):
                        display_text = f"{item['text']}:{item['options'][opt_idx]}"
                    else:
                        display_text = f"{item['text']}:{opt_idx}"
                elif item["type"] == "submenu":
                    display_text = f"{item['text']} >"
                
                self.oled.text(f"{prefix}{display_text}", 0, current_y)
            
            current_y += line_height
            idx += 1
            
        self.oled.show()

    async def _call_callback(self, cb, *args):
        """Helper to call callback which might be async or sync."""
        if not cb:
            return
        
        # Try to call it
        res = cb(*args)
        
        # If it returns a generator or awaitable (which async def does in MicroPython), await it
        if hasattr(res, "send"): 
            await res

    async def handle_input(self):
        # Check keys for activity
        key_pressed = False
        if (self.bsp.key_up.value() == 0 or 
            self.bsp.key_down.value() == 0 or 
            self.bsp.key_ok.value() == 0 or 
            self.bsp.key_cancel.value() == 0):
            key_pressed = True
            
        if key_pressed:
            if not self.screen_on:
                self._reset_interaction()
                await asyncio.sleep(0.3) 
                return True
            else:
                self._reset_interaction()

        if not self.screen_on:
            return False

        if self.in_edit_mode:
            await self._handle_edit_input()
        else:
            await self._handle_nav_input()
        
        return key_pressed

    async def _handle_nav_input(self):
        # Navigation Mode
        if self.bsp.key_up.value() == 0:
            self.current_index = max(0, self.current_index - 1)
            if self.current_index < self.window_start:
                self.window_start = self.current_index
            self.draw()
            await asyncio.sleep(0.2)
            
        if self.bsp.key_down.value() == 0:
            self.current_index = min(len(self.items) - 1, self.current_index + 1)
            # Simple scrolling logic
            if self.current_index >= self.window_start + 4:
                self.window_start = self.current_index - 3
            self.draw()
            await asyncio.sleep(0.2)
            
        if self.bsp.key_ok.value() == 0:
            item = self.items[self.current_index]
            if item["type"] == "action":
                if item["callback"]:
                    await asyncio.sleep(0.2)
                    await self._call_callback(item["callback"])
                    self.draw()
            elif item["type"] == "submenu":
                if item["submenu"]:
                    self.stack.append((self.items, self.current_index, self.window_start))
                    self.items = item["submenu"]
                    self.current_index = 0
                    self.window_start = 0
                    self.draw()
            else:
                self.in_edit_mode = True
                self.key_press_start_time = 0 # Reset acceleration timer
                self.draw()
            await asyncio.sleep(0.2)
            
        if self.bsp.key_cancel.value() == 0:
            if self.stack:
                self.items, self.current_index, self.window_start = self.stack.pop()
                self.draw()
                await asyncio.sleep(0.2)
            else:
                pass

    async def _handle_edit_input(self):
        # Edit Mode
        item = self.items[self.current_index]
        changed = False
        
        # Acceleration Logic
        current_time = time.ticks_ms()
        if self.bsp.key_up.value() == 0 or self.bsp.key_down.value() == 0:
            if self.key_press_start_time == 0:
                self.key_press_start_time = current_time
                self.acceleration_factor = 1
            else:
                duration = time.ticks_diff(current_time, self.key_press_start_time)
                if duration > 1000: # After 1 second
                    self.acceleration_factor = min(4, 1 + (duration - 1000) // 500) # Increase factor every 500ms, max 4
        else:
            self.key_press_start_time = 0
            self.acceleration_factor = 1

        step = item["step"] * int(self.acceleration_factor)
        
        if self.bsp.key_up.value() == 0:
            if item["type"] == "bool":
                item["value"] = not item["value"]
            elif item["type"] in ["int", "progress"]:
                item["value"] += step
                if item["max"] is not None:
                    item["value"] = min(item["max"], item["value"])
            elif item["type"] == "float":
                item["value"] += step
                if item["max"] is not None:
                    item["value"] = min(item["max"], item["value"])
            elif item["type"] == "option":
                item["value"] = (item["value"] + 1) % len(item["options"])
            changed = True
            self.draw()
            await asyncio.sleep(0.15 if self.acceleration_factor == 1 else 0.05) 
            
        if self.bsp.key_down.value() == 0:
            if item["type"] == "bool":
                item["value"] = not item["value"]
            elif item["type"] in ["int", "progress"]:
                item["value"] -= step
                if item["min"] is not None:
                    item["value"] = max(item["min"], item["value"])
            elif item["type"] == "float":
                item["value"] -= step
                if item["min"] is not None:
                    item["value"] = max(item["min"], item["value"])
            elif item["type"] == "option":
                item["value"] = (item["value"] - 1 + len(item["options"])) % len(item["options"])
            changed = True
            self.draw()
            await asyncio.sleep(0.15 if self.acceleration_factor == 1 else 0.05)
            
        if self.bsp.key_ok.value() == 0 or self.bsp.key_cancel.value() == 0:
            self.in_edit_mode = False
            self.draw()
            await asyncio.sleep(0.2)
            
        if changed and item["callback"]:
             await self._call_callback(item["callback"], item["value"])

    async def run(self):
        self.draw()
        while True:
            if self.screen_saver_enabled and self.screen_on:
                if time.time() - self.last_interaction_time > self.screen_saver_timeout:
                    print("Screen saver activated")
                    self.screen_on = False
                    if self.oled:
                        self.oled.poweroff()
            
            # Check if any key is pressed first to avoid busy loop overhead if possible
            # But handle_input already checks keys.
            # To optimize, we can increase sleep time when idle.
            
            activity = await self.handle_input()
            if not activity:
                await asyncio.sleep(0.1) # Sleep longer if no activity
            else:
                await asyncio.sleep(0.02) # Faster response when active

class MenuProxy:
    """Helper class to add items to a submenu list."""
    def __init__(self, items_list):
        self.items = items_list

    def add_item(self, text, callback=None, type="action", value=None, min_val=None, max_val=None, step=1, options=None, submenu=None, format_cb=None, key=None):
        item = {
            "text": text,
            "callback": callback,
            "type": type,
            "value": value,
            "min": min_val,
            "max": max_val,
            "step": step,
            "options": options,
            "submenu": submenu,
            "format_cb": format_cb,
            "key": key
        }
        self.items.append(item)
        
    def add_submenu(self, text, key=None):
        submenu_items = []
        self.add_item(text, type="submenu", submenu=submenu_items, key=key)
        return MenuProxy(submenu_items)
