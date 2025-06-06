#!/usr/bin/env python3
"""
Backup script for .pkl files from storage/recognized_faces_prod
Maintains 7-day backup rotation for each instance
Author: AI Assistant
Usage: python backup_script.py
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class BackupManager:
    """Manages backup operations for .pkl files"""
    
    def __init__(self, source_dir: str = "storage/recognized_faces_prod", 
                 backup_dir: str = "storage/backups", max_backups: int = 7):
        self.source_dir = Path(source_dir)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Setup logging - only errors to file, everything to console
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Console handler - for all messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        
        # File handler - only for errors
        file_handler = logging.FileHandler('storage/logs/backup_errors.log')
        file_handler.setLevel(logging.ERROR)
        file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def ensure_backup_directory_exists(self) -> None:
        """Create backup directory if it doesn't exist"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Backup directory ensured: {self.backup_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create backup directory: {e}")
            raise

    def find_pkl_file(self, instance_path: Path) -> Optional[Path]:
        """Find the .pkl file in an instance directory"""
        try:
            pkl_files = list(instance_path.glob("*.pkl"))
            
            if len(pkl_files) == 0:
                self.logger.warning(f"No .pkl file found in {instance_path}")
                return None
            elif len(pkl_files) > 1:
                self.logger.warning(f"Multiple .pkl files found in {instance_path}: {pkl_files}")
                # Return the first one found
                return pkl_files[0]
            else:
                self.logger.info(f"Found .pkl file: {pkl_files[0]}")
                return pkl_files[0]
                
        except Exception as e:
            self.logger.error(f"Error searching for .pkl file in {instance_path}: {e}")
            return None

    def get_backup_dates(self, instance_backup_dir: Path) -> List[str]:
        """Get list of backup dates for an instance, sorted by date"""
        try:
            if not instance_backup_dir.exists():
                return []
            
            date_dirs = [d.name for d in instance_backup_dir.iterdir() 
                        if d.is_dir() and self.is_valid_date_format(d.name)]
            return sorted(date_dirs)
            
        except Exception as e:
            self.logger.error(f"Error getting backup dates for {instance_backup_dir}: {e}")
            return []

    def is_valid_date_format(self, date_str: str) -> bool:
        """Check if string is in YYYY-MM-DD format"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def cleanup_old_backups(self, instance_backup_dir: Path) -> None:
        """Remove oldest backups if more than max_backups exist"""
        try:
            backup_dates = self.get_backup_dates(instance_backup_dir)
            
            if len(backup_dates) >= self.max_backups:
                # Calculate how many to remove
                to_remove = len(backup_dates) - self.max_backups + 1
                oldest_dates = backup_dates[:to_remove]
                
                for old_date in oldest_dates:
                    old_backup_path = instance_backup_dir / old_date
                    if old_backup_path.exists():
                        shutil.rmtree(old_backup_path)
                        self.logger.info(f"Removed old backup: {old_backup_path}")
                        
        except Exception as e:
            self.logger.error(f"Error cleaning up old backups: {e}")

    def backup_instance(self, instance_name: str) -> bool:
        """Backup .pkl file for a specific instance"""
        try:
            instance_path = self.source_dir / instance_name
            
            if not instance_path.exists() or not instance_path.is_dir():
                self.logger.warning(f"Instance directory not found: {instance_path}")
                return False

            # Find .pkl file
            pkl_file = self.find_pkl_file(instance_path)
            if not pkl_file:
                return False

            # Create backup directory structure
            instance_backup_dir = self.backup_dir / instance_name
            current_backup_dir = instance_backup_dir / self.current_date
            
            # Clean up old backups before creating new one
            self.cleanup_old_backups(instance_backup_dir)
            
            # Create current backup directory
            current_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy .pkl file to backup location
            backup_file_path = current_backup_dir / pkl_file.name
            shutil.copy2(pkl_file, backup_file_path)
            
            self.logger.info(f"Successfully backed up {pkl_file} to {backup_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error backing up instance {instance_name}: {e}")
            return False

    def backup_all_instances(self) -> None:
        """Backup .pkl files from all instances"""
        try:
            if not self.source_dir.exists():
                self.logger.error(f"Source directory does not exist: {self.source_dir}")
                return

            self.ensure_backup_directory_exists()
            
            # Get all instance directories
            instances = [d.name for d in self.source_dir.iterdir() if d.is_dir()]
            
            if not instances:
                self.logger.warning("No instance directories found in source directory")
                return

            self.logger.info(f"Found {len(instances)} instances to backup: {instances}")
            
            success_count = 0
            for instance in instances:
                if self.backup_instance(instance):
                    success_count += 1
            
            self.logger.info(f"Backup completed. Successfully backed up {success_count}/{len(instances)} instances")
            
        except Exception as e:
            self.logger.error(f"Error during backup process: {e}")
            raise

    def get_backup_status(self) -> dict:
        """Get status of all backups"""
        status = {}
        try:
            if not self.backup_dir.exists():
                return status
                
            for instance_dir in self.backup_dir.iterdir():
                if instance_dir.is_dir():
                    instance_name = instance_dir.name
                    backup_dates = self.get_backup_dates(instance_dir)
                    status[instance_name] = {
                        'backup_count': len(backup_dates),
                        'backup_dates': backup_dates,
                        'latest_backup': backup_dates[-1] if backup_dates else None
                    }
                    
        except Exception as e:
            self.logger.error(f"Error getting backup status: {e}")
            
        return status


def main():
    """Main function to run backup process"""
    try:
        backup_manager = BackupManager()
        
        print("=== Face Recognition Backup Script ===")
        print(f"Starting backup process at {datetime.now()}")
        print(f"Source: {backup_manager.source_dir}")
        print(f"Backup destination: {backup_manager.backup_dir}")
        print(f"Max backups per instance: {backup_manager.max_backups}")
        print("-" * 50)
        
        # Run backup
        backup_manager.backup_all_instances()
        
        # Show backup status
        print("\n=== Backup Status ===")
        status = backup_manager.get_backup_status()
        for instance, info in status.items():
            print(f"{instance}:")
            print(f"  - Backup count: {info['backup_count']}")
            print(f"  - Latest backup: {info['latest_backup']}")
            print(f"  - All dates: {', '.join(info['backup_dates'])}")
        
        print(f"\nBackup process completed at {datetime.now()}")
        
    except Exception as e:
        print(f"Fatal error during backup: {e}")
        logging.error(f"Fatal error during backup: {e}")
        exit(1)


if __name__ == "__main__":
    main() 