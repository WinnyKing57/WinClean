# -*- coding: utf-8 -*-

import os
import subprocess
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import logging


@dataclass
class CleaningSchedule:
    """Planification de nettoyage"""
    name: str
    description: str
    frequency: str  # 'daily', 'weekly', 'monthly'
    time: str  # Format HH:MM
    day_of_week: Optional[int] = None  # 0-6 pour weekly (0=lundi)
    day_of_month: Optional[int] = None  # 1-31 pour monthly
    enabled: bool = True
    applications: List[str] = None  # Applications à nettoyer
    categories: List[str] = None  # Catégories à nettoyer
    safety_level: str = 'safe'  # Niveau de sécurité maximum
    dry_run: bool = False
    notify_user: bool = True


class ScheduledCleaner:
    """Gestionnaire de nettoyage planifié avec systemd/cron"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_dir = os.path.expanduser("~/.config/debian-storage-analyzer")
        self.schedules_file = os.path.join(self.config_dir, "schedules.json")
        self.systemd_user_dir = os.path.expanduser("~/.config/systemd/user")
        
        # Créer les répertoires nécessaires
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.systemd_user_dir, exist_ok=True)
        
        self.schedules = self._load_schedules()
    
    def _load_schedules(self) -> Dict[str, CleaningSchedule]:
        """Charge les planifications depuis le fichier de configuration"""
        schedules = {}
        
        try:
            if os.path.exists(self.schedules_file):
                with open(self.schedules_file, 'r') as f:
                    data = json.load(f)
                    
                    for name, schedule_data in data.items():
                        schedules[name] = CleaningSchedule(**schedule_data)
        
        except (json.JSONDecodeError, IOError, TypeError) as e:
            self.logger.error(f"Erreur lors du chargement des planifications: {e}")
        
        return schedules
    
    def _save_schedules(self):
        """Sauvegarde les planifications dans le fichier de configuration"""
        try:
            data = {}
            for name, schedule in self.schedules.items():
                data[name] = {
                    'name': schedule.name,
                    'description': schedule.description,
                    'frequency': schedule.frequency,
                    'time': schedule.time,
                    'day_of_week': schedule.day_of_week,
                    'day_of_month': schedule.day_of_month,
                    'enabled': schedule.enabled,
                    'applications': schedule.applications,
                    'categories': schedule.categories,
                    'safety_level': schedule.safety_level,
                    'dry_run': schedule.dry_run,
                    'notify_user': schedule.notify_user
                }
            
            with open(self.schedules_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        except IOError as e:
            self.logger.error(f"Erreur lors de la sauvegarde des planifications: {e}")
    
    def add_schedule(self, schedule: CleaningSchedule) -> bool:
        """Ajoute une nouvelle planification"""
        try:
            # Valider la planification
            if not self._validate_schedule(schedule):
                return False
            
            # Ajouter à la liste
            self.schedules[schedule.name] = schedule
            
            # Sauvegarder
            self._save_schedules()
            
            # Créer les tâches système
            if schedule.enabled:
                self._create_system_task(schedule)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout de la planification: {e}")
            return False
    
    def remove_schedule(self, name: str) -> bool:
        """Supprime une planification"""
        try:
            if name in self.schedules:
                schedule = self.schedules[name]
                
                # Supprimer les tâches système
                self._remove_system_task(schedule)
                
                # Supprimer de la liste
                del self.schedules[name]
                
                # Sauvegarder
                self._save_schedules()
                
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression de la planification: {e}")
            return False
    
    def update_schedule(self, name: str, schedule: CleaningSchedule) -> bool:
        """Met à jour une planification existante"""
        try:
            if name in self.schedules:
                old_schedule = self.schedules[name]
                
                # Supprimer l'ancienne tâche système
                self._remove_system_task(old_schedule)
                
                # Valider la nouvelle planification
                if not self._validate_schedule(schedule):
                    return False
                
                # Mettre à jour
                self.schedules[name] = schedule
                
                # Sauvegarder
                self._save_schedules()
                
                # Créer la nouvelle tâche système
                if schedule.enabled:
                    self._create_system_task(schedule)
                
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour de la planification: {e}")
            return False
    
    def enable_schedule(self, name: str) -> bool:
        """Active une planification"""
        try:
            if name in self.schedules:
                schedule = self.schedules[name]
                schedule.enabled = True
                
                self._save_schedules()
                self._create_system_task(schedule)
                
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'activation de la planification: {e}")
            return False
    
    def disable_schedule(self, name: str) -> bool:
        """Désactive une planification"""
        try:
            if name in self.schedules:
                schedule = self.schedules[name]
                schedule.enabled = False
                
                self._save_schedules()
                self._remove_system_task(schedule)
                
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la désactivation de la planification: {e}")
            return False
    
    def _validate_schedule(self, schedule: CleaningSchedule) -> bool:
        """Valide une planification"""
        # Vérifier la fréquence
        if schedule.frequency not in ['daily', 'weekly', 'monthly']:
            return False
        
        # Vérifier le format de l'heure
        try:
            time_parts = schedule.time.split(':')
            if len(time_parts) != 2:
                return False
            
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return False
        
        except (ValueError, IndexError):
            return False
        
        # Vérifier les paramètres spécifiques à la fréquence
        if schedule.frequency == 'weekly':
            if schedule.day_of_week is None or not (0 <= schedule.day_of_week <= 6):
                return False
        
        elif schedule.frequency == 'monthly':
            if schedule.day_of_month is None or not (1 <= schedule.day_of_month <= 31):
                return False
        
        # Vérifier le niveau de sécurité
        if schedule.safety_level not in ['safe', 'moderate', 'risky']:
            return False
        
        return True
    
    def _create_system_task(self, schedule: CleaningSchedule):
        """Crée une tâche système (systemd timer + service)"""
        try:
            # Préférer systemd si disponible
            if self._is_systemd_available():
                self._create_systemd_task(schedule)
            else:
                self._create_cron_task(schedule)
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de la tâche système: {e}")
    
    def _remove_system_task(self, schedule: CleaningSchedule):
        """Supprime une tâche système"""
        try:
            # Essayer de supprimer les deux types de tâches
            self._remove_systemd_task(schedule)
            self._remove_cron_task(schedule)
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression de la tâche système: {e}")
    
    def _is_systemd_available(self) -> bool:
        """Vérifie si systemd est disponible"""
        try:
            result = subprocess.run(['systemctl', '--user', 'status'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _create_systemd_task(self, schedule: CleaningSchedule):
        """Crée une tâche systemd (service + timer)"""
        service_name = f"debian-storage-analyzer-{schedule.name}"
        
        # Créer le fichier service
        service_content = f"""[Unit]
Description=Debian Storage Analyzer - {schedule.description}
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -m debian_storage_analyzer.cleaner.scheduled_runner --schedule "{schedule.name}"
Environment=DISPLAY=:0
Environment=HOME={os.path.expanduser('~')}

[Install]
WantedBy=default.target
"""
        
        service_file = os.path.join(self.systemd_user_dir, f"{service_name}.service")
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        # Créer le fichier timer
        timer_content = self._generate_systemd_timer_content(schedule, service_name)
        
        timer_file = os.path.join(self.systemd_user_dir, f"{service_name}.timer")
        with open(timer_file, 'w') as f:
            f.write(timer_content)
        
        # Recharger systemd et activer le timer
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'enable', f"{service_name}.timer"], check=True)
        subprocess.run(['systemctl', '--user', 'start', f"{service_name}.timer"], check=True)
    
    def _generate_systemd_timer_content(self, schedule: CleaningSchedule, service_name: str) -> str:
        """Génère le contenu du fichier timer systemd"""
        content = f"""[Unit]
Description=Timer for {schedule.description}
Requires={service_name}.service

[Timer]
"""
        
        if schedule.frequency == 'daily':
            content += f"OnCalendar=daily\nPersistent=true\n"
        
        elif schedule.frequency == 'weekly':
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            day_name = days[schedule.day_of_week]
            content += f"OnCalendar={day_name} {schedule.time}\nPersistent=true\n"
        
        elif schedule.frequency == 'monthly':
            content += f"OnCalendar=*-*-{schedule.day_of_month:02d} {schedule.time}\nPersistent=true\n"
        
        content += """
[Install]
WantedBy=timers.target
"""
        
        return content
    
    def _remove_systemd_task(self, schedule: CleaningSchedule):
        """Supprime une tâche systemd"""
        service_name = f"debian-storage-analyzer-{schedule.name}"
        
        try:
            # Arrêter et désactiver le timer
            subprocess.run(['systemctl', '--user', 'stop', f"{service_name}.timer"], 
                         capture_output=True)
            subprocess.run(['systemctl', '--user', 'disable', f"{service_name}.timer"], 
                         capture_output=True)
            
            # Supprimer les fichiers
            service_file = os.path.join(self.systemd_user_dir, f"{service_name}.service")
            timer_file = os.path.join(self.systemd_user_dir, f"{service_name}.timer")
            
            if os.path.exists(service_file):
                os.remove(service_file)
            
            if os.path.exists(timer_file):
                os.remove(timer_file)
            
            # Recharger systemd
            subprocess.run(['systemctl', '--user', 'daemon-reload'], capture_output=True)
        
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    
    def _create_cron_task(self, schedule: CleaningSchedule):
        """Crée une tâche cron"""
        try:
            # Générer la ligne cron
            cron_line = self._generate_cron_line(schedule)
            
            # Obtenir le crontab actuel
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            # Ajouter la nouvelle ligne si elle n'existe pas déjà
            marker = f"# debian-storage-analyzer-{schedule.name}"
            if marker not in current_crontab:
                new_crontab = current_crontab + f"\n{marker}\n{cron_line}\n"
                
                # Écrire le nouveau crontab
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=new_crontab)
        
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Erreur lors de la création de la tâche cron: {e}")
    
    def _generate_cron_line(self, schedule: CleaningSchedule) -> str:
        """Génère une ligne cron"""
        time_parts = schedule.time.split(':')
        minute = time_parts[1]
        hour = time_parts[0]
        
        if schedule.frequency == 'daily':
            return f"{minute} {hour} * * * /usr/bin/python3 -m debian_storage_analyzer.cleaner.scheduled_runner --schedule \"{schedule.name}\""
        
        elif schedule.frequency == 'weekly':
            return f"{minute} {hour} * * {schedule.day_of_week} /usr/bin/python3 -m debian_storage_analyzer.cleaner.scheduled_runner --schedule \"{schedule.name}\""
        
        elif schedule.frequency == 'monthly':
            return f"{minute} {hour} {schedule.day_of_month} * * /usr/bin/python3 -m debian_storage_analyzer.cleaner.scheduled_runner --schedule \"{schedule.name}\""
        
        return ""
    
    def _remove_cron_task(self, schedule: CleaningSchedule):
        """Supprime une tâche cron"""
        try:
            # Obtenir le crontab actuel
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                return
            
            current_crontab = result.stdout
            marker = f"# debian-storage-analyzer-{schedule.name}"
            
            # Supprimer les lignes correspondantes
            lines = current_crontab.split('\n')
            new_lines = []
            skip_next = False
            
            for line in lines:
                if line.strip() == marker:
                    skip_next = True
                    continue
                
                if skip_next and line.strip().startswith('/usr/bin/python3 -m debian_storage_analyzer.cleaner.scheduled_runner'):
                    skip_next = False
                    continue
                
                new_lines.append(line)
                skip_next = False
            
            # Écrire le nouveau crontab
            new_crontab = '\n'.join(new_lines)
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_crontab)
        
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Erreur lors de la suppression de la tâche cron: {e}")
    
    def get_schedules(self) -> Dict[str, CleaningSchedule]:
        """Retourne toutes les planifications"""
        return self.schedules.copy()
    
    def get_schedule(self, name: str) -> Optional[CleaningSchedule]:
        """Retourne une planification spécifique"""
        return self.schedules.get(name)
    
    def get_next_execution_times(self) -> Dict[str, datetime]:
        """Retourne les prochaines heures d'exécution pour chaque planification"""
        next_times = {}
        now = datetime.now()
        
        for name, schedule in self.schedules.items():
            if not schedule.enabled:
                continue
            
            next_time = self._calculate_next_execution_time(schedule, now)
            if next_time:
                next_times[name] = next_time
        
        return next_times
    
    def _calculate_next_execution_time(self, schedule: CleaningSchedule, from_time: datetime) -> Optional[datetime]:
        """Calcule la prochaine heure d'exécution d'une planification"""
        try:
            time_parts = schedule.time.split(':')
            target_hour = int(time_parts[0])
            target_minute = int(time_parts[1])
            
            if schedule.frequency == 'daily':
                # Prochaine exécution aujourd'hui ou demain
                next_time = from_time.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                if next_time <= from_time:
                    next_time += timedelta(days=1)
                return next_time
            
            elif schedule.frequency == 'weekly':
                # Prochaine exécution cette semaine ou la semaine prochaine
                days_ahead = schedule.day_of_week - from_time.weekday()
                if days_ahead < 0:  # Le jour est déjà passé cette semaine
                    days_ahead += 7
                
                next_time = from_time + timedelta(days=days_ahead)
                next_time = next_time.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                
                if next_time <= from_time:
                    next_time += timedelta(weeks=1)
                
                return next_time
            
            elif schedule.frequency == 'monthly':
                # Prochaine exécution ce mois-ci ou le mois prochain
                next_time = from_time.replace(day=schedule.day_of_month, hour=target_hour, 
                                            minute=target_minute, second=0, microsecond=0)
                
                if next_time <= from_time:
                    # Passer au mois suivant
                    if from_time.month == 12:
                        next_time = next_time.replace(year=from_time.year + 1, month=1)
                    else:
                        next_time = next_time.replace(month=from_time.month + 1)
                
                return next_time
        
        except (ValueError, IndexError):
            return None
        
        return None
    
    def create_default_schedules(self):
        """Crée des planifications par défaut"""
        default_schedules = [
            CleaningSchedule(
                name="daily_cache_cleanup",
                description="Nettoyage quotidien des caches",
                frequency="daily",
                time="02:00",
                applications=["firefox", "chrome", "chromium"],
                categories=["cache"],
                safety_level="safe",
                dry_run=False,
                notify_user=False
            ),
            CleaningSchedule(
                name="weekly_temp_cleanup",
                description="Nettoyage hebdomadaire des fichiers temporaires",
                frequency="weekly",
                time="03:00",
                day_of_week=6,  # Dimanche
                categories=["temp", "logs"],
                safety_level="safe",
                dry_run=False,
                notify_user=True
            ),
            CleaningSchedule(
                name="monthly_deep_cleanup",
                description="Nettoyage mensuel approfondi",
                frequency="monthly",
                time="04:00",
                day_of_month=1,
                categories=["cache", "temp", "logs", "packages"],
                safety_level="moderate",
                dry_run=False,
                notify_user=True
            )
        ]
        
        for schedule in default_schedules:
            if schedule.name not in self.schedules:
                self.add_schedule(schedule)
    
    def get_system_task_status(self, schedule_name: str) -> Dict[str, any]:
        """Retourne le statut de la tâche système pour une planification"""
        status = {
            'systemd_available': self._is_systemd_available(),
            'systemd_active': False,
            'cron_active': False,
            'last_execution': None,
            'next_execution': None
        }
        
        # Vérifier le statut systemd
        if status['systemd_available']:
            try:
                service_name = f"debian-storage-analyzer-{schedule_name}"
                result = subprocess.run(['systemctl', '--user', 'is-active', f"{service_name}.timer"], 
                                      capture_output=True, text=True)
                status['systemd_active'] = result.returncode == 0
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        # Vérifier le statut cron
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                marker = f"# debian-storage-analyzer-{schedule_name}"
                status['cron_active'] = marker in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return status