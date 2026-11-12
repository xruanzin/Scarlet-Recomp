"""Static regression checks for the Scarlet 1080p window-size change.

Run: python tools/test_scarlet_window_size.py
These do not compile SDL/Vulkan, and cannot prove pixel dimensions on a
particular display; inspect [window] actual drawable in the Windows log.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


class WindowSizeSourceChecks(unittest.TestCase):
    def test_separate_internal_and_window_dimensions(self):
        h = source("runtime/settings.h")
        self.assertIn("int window_w, window_h;", h)
        self.assertIn("int res_mode;", h)

    def test_scarlet_defaults_to_1080p_and_ini_persists(self):
        s = source("runtime/settings.c")
        self.assertIn("#ifdef SCARLET_AOT\n    .window_w = 1920,\n    .window_h = 1080,", s)
        self.assertIn('!strcmp(key, "window_size")', s)
        self.assertIn('sscanf(val, "%dx%d%c"', s)
        self.assertIn('fprintf(f, "window_size = %dx%d\\n"', s)

    def test_window_pixel_scaling_and_monitor_fit(self):
        device = source("runtime/nvn/vulkan/device.c")
        for part in ("SDL_GetWindowPixelDensity(window)", "SDL_GetDisplayUsableBounds",
                     "SDL_GetWindowBordersSize", "SDL_SetWindowSize",
                     "SDL_GetWindowSizeInPixels", "SDL_SyncWindow(window)",
                     "ENV(\"LARECOMP_WINDOW\")"):
            self.assertIn(part, device)

    def test_main_thread_applies_f1_window_requests(self):
        menu = source("runtime/ui/menu.mm")
        self.assertIn('TR("Window size", "Tamanho da janela")', menu)
        self.assertIn("g_want_window_size_apply.store(true);", menu)
        self.assertIn("g_want_window_size_apply.exchange(false)", menu)
        self.assertIn("ui_window_apply_window_size(g_settings.window_w, g_settings.window_h);", menu)

    def test_no_fsr3_present_hook_was_claimed(self):
        device = source("runtime/nvn/vulkan/device.c")
        self.assertIn("rec_QueuePresentKHR(done_sem[img], g_vk.swapchain, img", device)
        self.assertIn("vkCreateSwapchainKHR(g_vk.dev, &ci,", device)


if __name__ == "__main__":
    unittest.main()
