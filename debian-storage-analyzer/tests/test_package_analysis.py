# -*- coding: utf-8 -*-

import os
import subprocess
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest

from src.analyzer.package_analyzer import PackageAnalyzer, PackageInfo


class TestPackageAnalyzer:
    """Tests unitaires pour PackageAnalyzer"""
    
    def setup_method(self):
        self.analyzer = PackageAnalyzer()
    
    def test_supported_package_types(self):
        """Property: L'analyseur supporte les types de packages attendus"""
        expected_types = ['deb', 'snap', 'flatpak', 'pip', 'npm']
        assert self.analyzer.supported_types == expected_types
    
    def test_empty_package_analysis(self):
        """Property: L'analyse sans packages retourne des structures vides"""
        with patch('subprocess.run') as mock_run:
            # Simuler des commandes qui ne retournent rien
            mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='')
            
            packages = self.analyzer.get_installed_packages()
            
            # Doit retourner un dictionnaire avec tous les types
            assert isinstance(packages, dict)
            for pkg_type in self.analyzer.supported_types:
                assert pkg_type in packages
                assert isinstance(packages[pkg_type], list)
    
    @given(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_package_type_filtering(self, requested_types):
        """Property: Le filtrage par type de package fonctionne"""
        # Filtrer les types valides
        valid_types = [t for t in requested_types if t in self.analyzer.supported_types]
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='')
            
            if valid_types:
                packages = self.analyzer.get_installed_packages(valid_types)
                
                # Doit retourner seulement les types demandés
                assert set(packages.keys()) == set(valid_types)
            else:
                # Si aucun type valide, utiliser tous les types
                packages = self.analyzer.get_installed_packages(requested_types)
                assert isinstance(packages, dict)


class TestPackageInfo:
    """Tests pour la structure PackageInfo"""
    
    @given(
        st.text(min_size=1, max_size=50),
        st.text(min_size=1, max_size=20),
        st.integers(min_value=0, max_value=1000000),
        st.sampled_from(['deb', 'snap', 'flatpak', 'pip', 'npm']),
        st.text(min_size=0, max_size=200),
        st.lists(st.text(min_size=1, max_size=30), max_size=10),
        st.lists(st.text(min_size=1, max_size=100), max_size=20)
    )
    def test_package_info_creation(self, name, version, size, pkg_type, description, dependencies, files):
        """Property: Création correcte des objets PackageInfo"""
        pkg_info = PackageInfo(
            name=name,
            version=version,
            size=size,
            package_type=pkg_type,
            description=description,
            dependencies=dependencies,
            files=files
        )
        
        assert pkg_info.name == name
        assert pkg_info.version == version
        assert pkg_info.size == size
        assert pkg_info.package_type == pkg_type
        assert pkg_info.description == description
        assert pkg_info.dependencies == dependencies
        assert pkg_info.files == files
        assert pkg_info.install_date is None  # Valeur par défaut


class TestDebPackageAnalysis:
    """Tests spécifiques pour l'analyse des packages .deb"""
    
    def setup_method(self):
        self.analyzer = PackageAnalyzer()
    
    def test_deb_package_parsing(self):
        """Property: Le parsing des packages .deb fonctionne correctement"""
        # Simuler la sortie de dpkg-query
        mock_output = "package1\t1.0.0\t1024\tTest package 1\npackage2\t2.0.0\t2048\tTest package 2\n"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr='')
            
            packages = self.analyzer._get_deb_packages()
            
            assert len(packages) == 2
            
            # Vérifier le premier package
            pkg1 = packages[0]
            assert pkg1.name == 'package1'
            assert pkg1.version == '1.0.0'
            assert pkg1.size == 1024 * 1024  # Converti en octets
            assert pkg1.package_type == 'deb'
            assert pkg1.description == 'Test package 1'
    
    def test_deb_package_size_conversion(self):
        """Property: La conversion de taille des packages .deb est correcte"""
        test_cases = [
            ("pkg1\t1.0\t100\tDesc", 100 * 1024),
            ("pkg2\t1.0\t0\tDesc", 0),
            ("pkg3\t1.0\tunknown\tDesc", 0),  # Taille non numérique
        ]
        
        for mock_output, expected_size in test_cases:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=mock_output + '\n', stderr='')
                
                packages = self.analyzer._get_deb_packages()
                
                if packages:
                    assert packages[0].size == expected_size
    
    def test_deb_command_failure_handling(self):
        """Property: Les échecs de commande .deb sont gérés gracieusement"""
        with patch('subprocess.run') as mock_run:
            # Simuler un échec de commande
            mock_run.side_effect = subprocess.CalledProcessError(1, 'dpkg-query')
            
            packages = self.analyzer._get_deb_packages()
            
            # Doit retourner une liste vide en cas d'échec
            assert packages == []


class TestSnapPackageAnalysis:
    """Tests spécifiques pour l'analyse des packages Snap"""
    
    def setup_method(self):
        self.analyzer = PackageAnalyzer()
    
    def test_snap_package_parsing(self):
        """Property: Le parsing des packages Snap fonctionne correctement"""
        # Simuler la sortie de snap list
        mock_output = """Name    Version   Rev   Tracking  Publisher   Notes
snap1   1.0       123   stable    publisher1  -
snap2   2.0       456   stable    publisher2  classic
"""
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr='')
            
            packages = self.analyzer._get_snap_packages()
            
            assert len(packages) == 2
            
            # Vérifier le premier package
            pkg1 = packages[0]
            assert pkg1.name == 'snap1'
            assert pkg1.version == '1.0'
            assert pkg1.package_type == 'snap'
            assert pkg1.size == 0  # Snap ne fournit pas facilement la taille
    
    def test_snap_command_not_found(self):
        """Property: L'absence de Snap est gérée gracieusement"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            packages = self.analyzer._get_snap_packages()
            
            assert packages == []


class TestPipPackageAnalysis:
    """Tests spécifiques pour l'analyse des packages pip"""
    
    def setup_method(self):
        self.analyzer = PackageAnalyzer()
    
    def test_pip_package_parsing(self):
        """Property: Le parsing des packages pip fonctionne correctement"""
        # Simuler la sortie JSON de pip list
        mock_output = '[{"name": "package1", "version": "1.0.0"}, {"name": "package2", "version": "2.0.0"}]'
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr='')
            
            packages = self.analyzer._get_pip_packages()
            
            assert len(packages) == 2
            
            # Vérifier le premier package
            pkg1 = packages[0]
            assert pkg1.name == 'package1'
            assert pkg1.version == '1.0.0'
            assert pkg1.package_type == 'pip'
    
    def test_pip_json_parsing_error(self):
        """Property: Les erreurs de parsing JSON pip sont gérées"""
        with patch('subprocess.run') as mock_run:
            # Simuler une sortie JSON invalide
            mock_run.return_value = MagicMock(returncode=0, stdout='invalid json', stderr='')
            
            packages = self.analyzer._get_pip_packages()
            
            assert packages == []


class TestPackageSummary:
    """Tests pour le résumé des packages"""
    
    def setup_method(self):
        self.analyzer = PackageAnalyzer()
    
    def test_empty_package_summary(self):
        """Property: Le résumé de packages vides est correct"""
        empty_packages = {pkg_type: [] for pkg_type in self.analyzer.supported_types}
        
        summary = self.analyzer.get_package_summary(empty_packages)
        
        assert summary['total_packages'] == 0
        assert summary['total_size'] == 0
        assert len(summary['by_type']) == len(self.analyzer.supported_types)
        assert summary['largest_packages'] == []
        assert summary['most_dependencies'] == []
    
    @given(st.integers(min_value=1, max_value=20))
    def test_package_summary_calculations(self, num_packages):
        """Property: Les calculs du résumé sont corrects"""
        # Créer des packages de test
        test_packages = {
            'deb': [
                PackageInfo(
                    name=f'deb-pkg-{i}',
                    version='1.0.0',
                    size=1000 * (i + 1),
                    package_type='deb',
                    description=f'Deb package {i}',
                    dependencies=[f'dep-{j}' for j in range(i)],
                    files=[]
                )
                for i in range(num_packages)
            ],
            'pip': [
                PackageInfo(
                    name=f'pip-pkg-{i}',
                    version='2.0.0',
                    size=500 * (i + 1),
                    package_type='pip',
                    description=f'Pip package {i}',
                    dependencies=[],
                    files=[]
                )
                for i in range(num_packages // 2)
            ]
        }
        
        # Ajouter les autres types vides
        for pkg_type in self.analyzer.supported_types:
            if pkg_type not in test_packages:
                test_packages[pkg_type] = []
        
        summary = self.analyzer.get_package_summary(test_packages)
        
        # Vérifications
        expected_total = num_packages + (num_packages // 2)
        assert summary['total_packages'] == expected_total
        
        # Vérifier les comptes par type
        assert summary['by_type']['deb']['count'] == num_packages
        assert summary['by_type']['pip']['count'] == num_packages // 2
        
        # Vérifier que les pourcentages totalisent ~100%
        total_percentage = sum(
            type_info['percentage'] 
            for type_info in summary['by_type'].values()
        )
        if summary['total_size'] > 0:
            assert abs(total_percentage - 100.0) < 0.1
    
    def test_largest_packages_identification(self):
        """Property: L'identification des plus gros packages fonctionne"""
        test_packages = {
            'deb': [
                PackageInfo('small-pkg', '1.0', 100, 'deb', 'Small', [], []),
                PackageInfo('large-pkg', '1.0', 10000, 'deb', 'Large', [], []),
                PackageInfo('medium-pkg', '1.0', 1000, 'deb', 'Medium', [], []),
            ]
        }
        
        # Ajouter les autres types vides
        for pkg_type in self.analyzer.supported_types:
            if pkg_type not in test_packages:
                test_packages[pkg_type] = []
        
        summary = self.analyzer.get_package_summary(test_packages)
        
        # Le plus gros package devrait être en premier
        if summary['largest_packages']:
            largest = summary['largest_packages'][0]
            assert largest['name'] == 'large-pkg'
            assert largest['size'] == 10000


class TestPackageSearch:
    """Tests pour la recherche de packages"""
    
    def setup_method(self):
        self.analyzer = PackageAnalyzer()
    
    @given(st.text(min_size=1, max_size=20))
    def test_package_search_by_name(self, search_term):
        """Property: La recherche de packages par nom fonctionne"""
        # Créer des packages de test
        test_packages = {
            'deb': [
                PackageInfo(f'test-{search_term}-pkg', '1.0', 100, 'deb', 'Test', [], []),
                PackageInfo('other-package', '1.0', 100, 'deb', 'Other', [], []),
            ],
            'pip': [
                PackageInfo(f'{search_term}-python', '1.0', 100, 'pip', 'Python', [], []),
            ]
        }
        
        # Ajouter les autres types vides
        for pkg_type in self.analyzer.supported_types:
            if pkg_type not in test_packages:
                test_packages[pkg_type] = []
        
        found_packages = self.analyzer.find_package_by_name(search_term, test_packages)
        
        # Doit trouver les packages contenant le terme de recherche
        assert len(found_packages) >= 2
        
        for pkg in found_packages:
            assert search_term.lower() in pkg.name.lower()


class TestPackageConflicts:
    """Tests pour la détection de conflits entre packages"""
    
    def setup_method(self):
        self.analyzer = PackageAnalyzer()
    
    def test_package_conflict_detection(self):
        """Property: La détection de conflits entre packages fonctionne"""
        # Créer des packages avec des noms similaires mais des types différents
        test_packages = {
            'deb': [
                PackageInfo('python3', '3.9', 1000, 'deb', 'Python from deb', [], []),
            ],
            'snap': [
                PackageInfo('python3', '3.10', 2000, 'snap', 'Python from snap', [], []),
            ],
            'pip': [
                PackageInfo('unique-package', '1.0', 100, 'pip', 'Unique', [], []),
            ]
        }
        
        # Ajouter les autres types vides
        for pkg_type in self.analyzer.supported_types:
            if pkg_type not in test_packages:
                test_packages[pkg_type] = []
        
        conflicts = self.analyzer.get_package_conflicts(test_packages)
        
        # Doit détecter le conflit python3
        assert len(conflicts) >= 1
        
        python_conflict = next((c for c in conflicts if 'python' in c['base_name']), None)
        assert python_conflict is not None
        assert python_conflict['conflict_type'] == 'multiple_package_types'
        assert len(python_conflict['packages']) == 2


class PackageAnalysis(RuleBasedStateMachine):
    """Machine à états pour tester l'analyse de packages"""
    
    def __init__(self):
        super().__init__()
        self.analyzer = PackageAnalyzer()
        self.mock_packages = {pkg_type: [] for pkg_type in self.analyzer.supported_types}
    
    @rule(pkg_type=st.sampled_from(['deb', 'snap', 'flatpak', 'pip', 'npm']),
          name=st.text(min_size=1, max_size=30),
          version=st.text(min_size=1, max_size=20),
          size=st.integers(min_value=0, max_value=100000))
    def add_package(self, pkg_type, name, version, size):
        """Ajouter un package simulé"""
        # Nettoyer le nom pour éviter les caractères problématiques
        clean_name = "".join(c for c in name if c.isalnum() or c in ".-_")
        if clean_name:
            pkg_info = PackageInfo(
                name=clean_name,
                version=version,
                size=size,
                package_type=pkg_type,
                description=f"Mock {pkg_type} package",
                dependencies=[],
                files=[]
            )
            self.mock_packages[pkg_type].append(pkg_info)
    
    @rule()
    def generate_summary(self):
        """Générer un résumé des packages"""
        summary = self.analyzer.get_package_summary(self.mock_packages)
        
        # Vérifier la cohérence du résumé
        expected_total = sum(len(packages) for packages in self.mock_packages.values())
        assert summary['total_packages'] == expected_total
        
        # Vérifier les comptes par type
        for pkg_type, packages in self.mock_packages.items():
            assert summary['by_type'][pkg_type]['count'] == len(packages)
    
    @rule(search_term=st.text(min_size=1, max_size=10))
    def search_packages(self, search_term):
        """Rechercher des packages"""
        found = self.analyzer.find_package_by_name(search_term, self.mock_packages)
        
        # Tous les packages trouvés doivent contenir le terme de recherche
        for pkg in found:
            assert search_term.lower() in pkg.name.lower()
    
    @invariant()
    def package_data_consistency(self):
        """Invariant: Les données de packages sont cohérentes"""
        for pkg_type, packages in self.mock_packages.items():
            for pkg in packages:
                assert pkg.package_type == pkg_type
                assert pkg.size >= 0
                assert len(pkg.name) > 0
                assert len(pkg.version) > 0


# Test de la machine à états
TestPackageAnalysis = PackageAnalysis.TestCase


if __name__ == '__main__':
    pytest.main([__file__])