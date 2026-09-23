"""Make UKBinCollectionData's Selenium councils work inside this container.

Two things upstream does that don't suit a server:

1. `create_webdriver()` calls `ChromeDriverManager().install()`, which downloads
   a chromedriver from the internet on first use. In a container that is slow,
   needs outbound access at collection time, and can drift from the installed
   browser. The image already ships a matching chromedriver, so point it there.

2. Selenium looks for `google-chrome`; Debian installs `chromium`. The
   Dockerfile symlinks one to the other rather than patching option-building we
   don't control.

Both are no-ops off-container, so local development keeps using whatever Chrome
the machine already has.
"""
from __future__ import annotations

import logging
import os
import shutil

log = logging.getLogger(__name__)


def use_system_chromedriver() -> str | None:
    """Point webdriver-manager at the driver in the image. Returns its path."""
    path = os.environ.get("CHROMEDRIVER") or shutil.which("chromedriver")
    if not path:
        log.info("no system chromedriver; leaving webdriver-manager alone")
        return None

    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:                                        # pragma: no cover
        return None

    ChromeDriverManager.install = lambda self, *args, **kwargs: path
    log.info("using system chromedriver at %s", path)
    return path
