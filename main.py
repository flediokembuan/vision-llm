"""
Entry point aplikasi. Jalankan dengan:

    python main.py
"""

import os

import webview

import config
from api import Api


def main():
    api = Api()

    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")

    window = webview.create_window(
        config.WINDOW_TITLE,
        ui_path,
        js_api=api,
        width=config.WINDOW_WIDTH,
        height=config.WINDOW_HEIGHT,
        min_size=(1024, 680),
    )

    def on_closed():
        api.pose_detector.stop()
        api.camera.stop()

    window.events.closed += on_closed

    webview.start(debug=False)


if __name__ == "__main__":
    main()
