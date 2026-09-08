import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sgdk_setup.app import SGDKSetupApp


if __name__ == "__main__":
    SGDKSetupApp().run()
