#!/usr/bin/env python3
"""
Pi Player System Test
Tests all components of the Pi Player system
"""

import json
import os
import sys
import time
import requests
import subprocess
from pathlib import Path

# Enable development mode for testing
os.environ["PI_PLAYER_DEV"] = "true"

from config import config
from logger_setup import get_component_logger

# Test logger
logger = get_component_logger("test_system", console=True)


class PiPlayerTester:
    """Test suite for Pi Player system"""
    
    def __init__(self):
        self.api_url = f"http://localhost:{config.API_PORT}"
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if success else "FAIL"
        logger.info(f"[{status}] {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
    
    def test_imports(self):
        """Test that all modules can be imported"""
        logger.info("Testing module imports...")
        
        try:
            import config
            self.log_test("Config Import", True)
        except Exception as e:
            self.log_test("Config Import", False, str(e))
        
        try:
            import telemetry
            self.log_test("Telemetry Import", True)
        except Exception as e:
            self.log_test("Telemetry Import", False, str(e))
        
        try:
            import media_downloader
            self.log_test("Media Downloader Import", True)
        except Exception as e:
            self.log_test("Media Downloader Import", False, str(e))
        
        try:
            import media_player
            self.log_test("Media Player Import", True)
        except Exception as e:
            self.log_test("Media Player Import", False, str(e))
        
        try:
            import pi_server
            self.log_test("Pi Server Import", True)
        except Exception as e:
            self.log_test("Pi Server Import", False, str(e))
    
    def test_config(self):
        """Test configuration setup"""
        logger.info("Testing configuration...")
        
        # Test directory creation
        dirs_exist = all([
            config.BASE_DIR.exists(),
            config.MEDIA_CACHE_DIR.exists(),
            config.LOGS_DIR.exists()
        ])
        self.log_test("Directory Creation", dirs_exist, "All required directories exist")
        
        # Test file type detection
        self.log_test("Video Detection", config.is_video_file("test.mp4"))
        self.log_test("Audio Detection", config.is_audio_file("test.mp3"))
        self.log_test("Image Detection", config.is_image_file("test.jpg"))
    
    def test_telemetry(self):
        """Test telemetry collection"""
        logger.info("Testing telemetry collection...")
        
        try:
            from telemetry import get_stats
            stats = get_stats()
            
            required_keys = ["timestamp", "system", "uptime", "playlist"]
            has_required = all(key in stats for key in required_keys)
            self.log_test("Telemetry Collection", has_required, f"Got {len(stats)} fields")
            
            # Test individual components
            if "system" in stats:
                sys_keys = ["cpu", "memory", "disk"]
                has_sys_keys = all(key in stats["system"] for key in sys_keys)
                self.log_test("System Stats", has_sys_keys)
            
        except Exception as e:
            self.log_test("Telemetry Collection", False, str(e))
    
    def test_media_downloader(self):
        """Test media downloader functionality"""
        logger.info("Testing media downloader...")
        
        try:
            from media_downloader import needs_download, sha256_file
            
            # Test checksum function with a dummy file
            test_file = config.BASE_DIR / "test_file.txt"
            test_file.write_text("test content")
            
            checksum = sha256_file(test_file)
            self.log_test("Checksum Calculation", checksum is not None, f"SHA256: {checksum[:16]}...")
            
            # Test needs_download logic
            item = {"filename": "nonexistent.txt", "checksum": "dummy"}
            needs_dl, reason = needs_download(item)
            self.log_test("Download Logic", needs_dl, f"Reason: {reason}")
            
            # Cleanup
            test_file.unlink(missing_ok=True)
            
        except Exception as e:
            self.log_test("Media Downloader", False, str(e))
    
    def start_test_server(self):
        """Start the API server for testing"""
        logger.info("Starting test API server...")
        
        try:
            # Import and start server in background
            import uvicorn
            from pi_server import app
            
            # Start server process
            self.server_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "pi_server:app", 
                "--host", config.API_HOST,
                "--port", str(config.API_PORT),
                "--log-level", "warning"
            ], cwd=config.BASE_DIR)
            
            # Wait for server to start
            time.sleep(5)
            
            # Test if server is responding
            try:
                response = requests.get(f"{self.api_url}/health", timeout=5)
                if response.status_code == 200:
                    self.log_test("API Server Start", True, "Server is responding")
                    return True
                else:
                    self.log_test("API Server Start", False, f"Status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                self.log_test("API Server Start", False, str(e))
            
        except Exception as e:
            self.log_test("API Server Start", False, str(e))
        
        return False
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        logger.info("Testing API endpoints...")
        
        # Test health endpoint
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            self.log_test("Health Endpoint", response.status_code == 200, 
                         f"Response: {response.json()['status']}")
        except Exception as e:
            self.log_test("Health Endpoint", False, str(e))
        
        # Test telemetry endpoint
        try:
            response = requests.get(f"{self.api_url}/telemetry", timeout=10)
            self.log_test("Telemetry Endpoint", response.status_code == 200,
                         f"Got telemetry data with {len(response.json())} fields")
        except Exception as e:
            self.log_test("Telemetry Endpoint", False, str(e))
        
        # Test playlist endpoints
        try:
            # GET playlist (should be empty initially)
            response = requests.get(f"{self.api_url}/playlist", timeout=5)
            self.log_test("Get Playlist", response.status_code == 200)
            
            # POST playlist
            test_playlist = {
                "version": "test-1.0",
                "loop": True,
                "items": [
                    {
                        "filename": "test.jpg",
                        "url": "https://picsum.photos/800/600",
                        "duration": 5
                    }
                ]
            }
            
            response = requests.post(f"{self.api_url}/playlist", 
                                   json=test_playlist, timeout=5)
            self.log_test("Post Playlist", response.status_code == 200,
                         "Playlist update accepted")
            
        except Exception as e:
            self.log_test("Playlist Endpoints", False, str(e))
    
    def test_media_player_logic(self):
        """Test media player logic without actually playing"""
        logger.info("Testing media player logic...")
        
        try:
            from media_player import MediaPlayer
            
            player = MediaPlayer()
            
            # Test playlist loading (should handle missing file gracefully)
            changed = player.load_playlist()
            self.log_test("Playlist Loading", True, f"Changed: {changed}")
            
            # Test command generation for different file types
            test_video = config.MEDIA_CACHE_DIR / "test.mp4"
            test_video.touch()  # Create empty file
            
            cmd = player.get_player_command(test_video, {"duration": 30})
            has_vlc = "cvlc" in cmd[0]
            self.log_test("Video Command Generation", has_vlc, f"Command: {cmd[0]}")
            
            # Test image command
            test_image = config.MEDIA_CACHE_DIR / "test.jpg" 
            test_image.touch()
            
            cmd = player.get_player_command(test_image, {"duration": 10})
            has_feh = "feh" in cmd[0]
            self.log_test("Image Command Generation", has_feh, f"Command: {cmd[0]}")
            
            # Cleanup
            test_video.unlink(missing_ok=True)
            test_image.unlink(missing_ok=True)
            
        except Exception as e:
            self.log_test("Media Player Logic", False, str(e))
    
    def test_logging(self):
        """Test logging functionality"""
        logger.info("Testing logging...")
        
        try:
            from logger_setup import get_component_logger
            
            test_logger = get_component_logger("test_component", console=False)
            test_logger.info("Test log message")
            
            # Check if log file was created
            log_file = config.get_log_path("test_component.log")
            log_exists = log_file.exists()
            self.log_test("Log File Creation", log_exists, f"Path: {log_file}")
            
            if log_exists:
                log_content = log_file.read_text()
                has_message = "Test log message" in log_content
                self.log_test("Log Content", has_message)
            
        except Exception as e:
            self.log_test("Logging", False, str(e))
    
    def stop_test_server(self):
        """Stop the test server"""
        if hasattr(self, 'server_process'):
            logger.info("Stopping test server...")
            self.server_process.terminate()
            self.server_process.wait(timeout=10)
    
    def run_all_tests(self):
        """Run all tests"""
        logger.info("Starting Pi Player system tests...")
        logger.info("=" * 60)
        
        # Run tests
        self.test_imports()
        self.test_config()
        self.test_telemetry()
        self.test_media_downloader()
        self.test_logging()
        self.test_media_player_logic()
        
        # API tests require server
        server_started = self.start_test_server()
        if server_started:
            self.test_api_endpoints()
            self.stop_test_server()
        else:
            logger.warning("Skipping API tests - server failed to start")
        
        # Summary
        logger.info("=" * 60)
        logger.info("Test Summary:")
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        logger.info(f"Passed: {passed}/{total} tests")
        
        if passed < total:
            logger.error("Some tests failed:")
            for result in self.test_results:
                if not result["success"]:
                    logger.error(f"  - {result['test']}: {result['message']}")
        else:
            logger.info("All tests passed!")
        
        return passed == total


def main():
    """Main test function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Pi Player System Tester")
        print("Usage: python3 test_system.py [--help]")
        print("Tests all Pi Player components and functionality")
        return 0
    
    tester = PiPlayerTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())