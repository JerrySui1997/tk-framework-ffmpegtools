# framework.py

import sgtk

class FFmpegFramework(sgtk.platform.Framework):
    
    def init_framework(self):
        """Framework initialization - simple setup only"""
        self.logger.info("=== FFmpeg Framework Initialization Started ===")
        self.logger.info("Framework disk location: %s" % self.disk_location)
        self.logger.info("=== FFmpeg Framework Initialization Complete ===")
    
    def destroy_framework(self):
        """Framework cleanup"""
        self.logger.info("=== FFmpeg Framework Destruction Started ===")
        self.logger.info("=== FFmpeg Framework Destruction Complete ===")