# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import pytest

from src.cleaner.intelligent_cleaner import IntelligentCleaner, CleaningAction, CleaningResult


class TestMultipleSelectionBulkOperations:
    """Tests pour les sélections multiples et opérations en lot"""
    
    def setup_method(self):
        self.cleaner = IntelligentCleaner(dry_run=True)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),
            st.integers(min_value=1, max_value=10000)
        ),
        min_size=2,
        max_size=20
    ))
    def test_bulk_operation_consistency(self, file_specs):
        """Property: Les opérations en lot sont cohérentes avec les opérations individuelles"""
        # Créer des fichiers de test
        actions = []
        created_files = []
        
        for filename, size in file_specs:
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if safe_filename:
                filepath = os.path.join(self.temp_dir, f"{safe_filename}.tmp")
                try:
                    content = "x" * size
                    Path(filepath).write_text(content, encoding='utf-8')
                    created_files.append(filepath)
                    
                    # Créer une action de nettoyage
                    actions.append(CleaningAction(
                        action_type='delete_file',
                        target_path=filepath,
                        size_bytes=len(content.encode('utf-8')),
                        description=f"Supprimer {safe_filename}",
                        safety_level='safe',
                        category='temp',
                        reversible=False
                    ))
                except (OSError, UnicodeEncodeError):
                    continue
        
        if not actions:
            return  # Skip si aucune action créée
        
        # Exécuter les opérations en lot
        bulk_results = self.cleaner.execute_cleaning_actions(actions)
        
        # Vérifications de cohérence
        assert len(bulk_results) == len(actions)
        
        # Chaque résultat doit correspondre à son action
        for i, result in enumerate(bulk_results):
            assert result.action == actions[i]
            assert isinstance(result.success, bool)
            assert result.actual_size_freed >= 0
            assert result.execution_time >= 0
        
        # La somme des tailles libérées doit être cohérente
        total_freed = sum(result.actual_size_freed for result in bulk_results)
        expected_total = sum(action.size_bytes for action in actions)
        assert total_freed == expected_total  # En mode dry-run
    
    @given(st.lists(
        st.sampled_from(['safe', 'moderate', 'risky']),
        min_size=1,
        max_size=10
    ))
    def test_bulk_operation_safety_levels(self, safety_levels):
        """Property: Les opérations en lot respectent les niveaux de sécurité"""
        actions = []
        
        for i, safety_level in enumerate(safety_levels):
            filepath = os.path.join(self.temp_dir, f"test_{i}.tmp")
            Path(filepath).touch()
            
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=1024,
                description=f"Test action {i}",
                safety_level=safety_level,
                category='test',
                reversible=False
            ))
        
        # Exécuter les opérations
        results = self.cleaner.execute_cleaning_actions(actions)
        
        # Vérifier que chaque résultat conserve le niveau de sécurité
        for i, result in enumerate(results):
            assert result.action.safety_level == safety_levels[i]
    
    def test_empty_bulk_operation(self):
        """Property: Les opérations en lot vides sont gérées correctement"""
        results = self.cleaner.execute_cleaning_actions([])
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    @given(st.integers(min_value=1, max_value=100))
    def test_bulk_operation_scalability(self, num_actions):
        """Property: Les opérations en lot sont scalables"""
        actions = []
        
        # Créer de nombreuses actions
        for i in range(num_actions):
            filepath = os.path.join(self.temp_dir, f"bulk_test_{i}.tmp")
            Path(filepath).touch()
            
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=1024,
                description=f"Bulk test {i}",
                safety_level='safe',
                category='test',
                reversible=False
            ))
        
        # Exécuter toutes les actions
        results = self.cleaner.execute_cleaning_actions(actions)
        
        # Vérifications de scalabilité
        assert len(results) == num_actions
        
        # Toutes les actions doivent être traitées
        for result in results:
            assert isinstance(result, CleaningResult)
            assert result.success is True  # En mode dry-run
    
    @given(st.lists(
        st.sampled_from(['cache', 'logs', 'temp', 'duplicates', 'packages']),
        min_size=1,
        max_size=15
    ))
    def test_bulk_operation_categories(self, categories):
        """Property: Les opérations en lot préservent les catégories"""
        actions = []
        
        for i, category in enumerate(categories):
            filepath = os.path.join(self.temp_dir, f"cat_test_{i}.tmp")
            Path(filepath).touch()
            
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=1024,
                description=f"Category test {i}",
                safety_level='safe',
                category=category,
                reversible=False
            ))
        
        # Exécuter les opérations
        results = self.cleaner.execute_cleaning_actions(actions)
        
        # Vérifier que les catégories sont préservées
        for i, result in enumerate(results):
            assert result.action.category == categories[i]
    
    def test_bulk_operation_error_isolation(self):
        """Property: Les erreurs dans les opérations en lot sont isolées"""
        actions = [
            # Action valide
            CleaningAction(
                action_type='delete_file',
                target_path=os.path.join(self.temp_dir, 'valid.tmp'),
                size_bytes=1024,
                description="Valid action",
                safety_level='safe',
                category='test',
                reversible=False
            ),
            # Action invalide (fichier inexistant en mode non dry-run)
            CleaningAction(
                action_type='delete_file',
                target_path='/nonexistent/path/file.tmp',
                size_bytes=1024,
                description="Invalid action",
                safety_level='safe',
                category='test',
                reversible=False
            )
        ]
        
        # Créer le fichier valide
        Path(actions[0].target_path).touch()
        
        # Exécuter les opérations
        results = self.cleaner.execute_cleaning_actions(actions)
        
        # Vérifier que les deux actions ont été traitées
        assert len(results) == 2
        
        # La première devrait réussir (dry-run), la seconde aussi (dry-run)
        # En mode dry-run, toutes les actions "réussissent"
        for result in results:
            assert result.success is True
    
    @given(st.lists(
        st.booleans(),
        min_size=1,
        max_size=10
    ))
    def test_bulk_operation_reversibility(self, reversible_flags):
        """Property: Les opérations en lot respectent les flags de réversibilité"""
        actions = []
        
        for i, reversible in enumerate(reversible_flags):
            filepath = os.path.join(self.temp_dir, f"rev_test_{i}.tmp")
            Path(filepath).touch()
            
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=filepath,
                size_bytes=1024,
                description=f"Reversibility test {i}",
                safety_level='safe',
                category='test',
                reversible=reversible
            ))
        
        # Exécuter les opérations
        results = self.cleaner.execute_cleaning_actions(actions)
        
        # Vérifier que les flags de réversibilité sont préservés
        for i, result in enumerate(results):
            assert result.action.reversible == reversible_flags[i]


class TestCleaningSummary:
    """Tests pour les résumés de nettoyage"""
    
    def setup_method(self):
        self.cleaner = IntelligentCleaner(dry_run=True)
    
    @given(st.lists(
        st.tuples(
            st.sampled_from(['cache', 'logs', 'temp', 'duplicates', 'packages']),
            st.sampled_from(['safe', 'moderate', 'risky']),
            st.integers(min_value=1, max_value=1000000),
            st.booleans()
        ),
        min_size=1,
        max_size=20
    ))
    def test_cleaning_summary_accuracy(self, action_specs):
        """Property: Les résumés de nettoyage sont précis"""
        actions = []
        
        for i, (category, safety_level, size, reversible) in enumerate(action_specs):
            actions.append(CleaningAction(
                action_type='delete_file',
                target_path=f'/tmp/test_{i}',
                size_bytes=size,
                description=f"Test action {i}",
                safety_level=safety_level,
                category=category,
                reversible=reversible
            ))
        
        # Générer le résumé
        summary = self.cleaner.get_cleaning_summary(actions)
        
        # Vérifications de précision
        assert summary['total_actions'] == len(actions)
        assert summary['total_size_to_free'] == sum(action.size_bytes for action in actions)
        assert summary['reversible_actions'] == sum(1 for action in actions if action.reversible)
        
        # Vérifier les groupements par catégorie
        expected_categories = {}
        for action in actions:
            if action.category not in expected_categories:
                expected_categories[action.category] = {'count': 0, 'total_size': 0}
            expected_categories[action.category]['count'] += 1
            expected_categories[action.category]['total_size'] += action.size_bytes
        
        assert summary['by_category'] == expected_categories
        
        # Vérifier les groupements par niveau de sécurité
        expected_safety = {}
        for action in actions:
            if action.safety_level not in expected_safety:
                expected_safety[action.safety_level] = {'count': 0, 'total_size': 0}
            expected_safety[action.safety_level]['count'] += 1
            expected_safety[action.safety_level]['total_size'] += action.size_bytes
        
        assert summary['by_safety_level'] == expected_safety
        
        # Vérifier la plus grosse action
        if actions:
            largest_expected = max(actions, key=lambda a: a.size_bytes)
            assert summary['largest_action'] == largest_expected
    
    def test_empty_summary(self):
        """Property: Le résumé d'actions vides est correct"""
        summary = self.cleaner.get_cleaning_summary([])
        
        assert summary['total_actions'] == 0
        assert summary['total_size_to_free'] == 0
        assert summary['by_category'] == {}
        assert summary['by_safety_level'] == {}
        assert summary['reversible_actions'] == 0
        assert summary['largest_action'] is None


class BulkCleaningOperations(RuleBasedStateMachine):
    """Machine à états pour tester les opérations de nettoyage en lot"""
    
    def __init__(self):
        super().__init__()
        self.cleaner = IntelligentCleaner(dry_run=True)
        self.temp_dir = tempfile.mkdtemp()
        self.actions = []
        self.executed_results = []
    
    def teardown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @rule(filename=st.text(min_size=1, max_size=20),
          size=st.integers(min_value=1, max_value=10000),
          category=st.sampled_from(['cache', 'logs', 'temp', 'duplicates']),
          safety_level=st.sampled_from(['safe', 'moderate', 'risky']))
    def add_cleaning_action(self, filename, size, category, safety_level):
        """Ajouter une action de nettoyage"""
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        if safe_filename:
            filepath = os.path.join(self.temp_dir, f"{safe_filename}.tmp")
            try:
                Path(filepath).touch()
                
                action = CleaningAction(
                    action_type='delete_file',
                    target_path=filepath,
                    size_bytes=size,
                    description=f"Clean {safe_filename}",
                    safety_level=safety_level,
                    category=category,
                    reversible=False
                )
                
                self.actions.append(action)
            except OSError:
                pass
    
    @rule()
    def execute_bulk_cleaning(self):
        """Exécuter le nettoyage en lot"""
        if self.actions:
            results = self.cleaner.execute_cleaning_actions(self.actions)
            self.executed_results.extend(results)
            
            # Vérifier la cohérence
            assert len(results) == len(self.actions)
            
            for i, result in enumerate(results):
                assert result.action == self.actions[i]
    
    @rule()
    def generate_summary(self):
        """Générer un résumé des actions"""
        if self.actions:
            summary = self.cleaner.get_cleaning_summary(self.actions)
            
            # Vérifier la cohérence du résumé
            assert summary['total_actions'] == len(self.actions)
            assert summary['total_size_to_free'] == sum(a.size_bytes for a in self.actions)
    
    @invariant()
    def actions_are_valid(self):
        """Invariant: Toutes les actions sont valides"""
        for action in self.actions:
            assert isinstance(action, CleaningAction)
            assert action.size_bytes >= 0
            assert action.safety_level in ['safe', 'moderate', 'risky']
            assert action.category in ['cache', 'logs', 'temp', 'duplicates']
    
    @invariant()
    def results_match_actions(self):
        """Invariant: Les résultats correspondent aux actions"""
        if self.executed_results:
            # Chaque résultat doit avoir une action correspondante
            for result in self.executed_results:
                assert isinstance(result, CleaningResult)
                assert result.action in self.actions


# Test de la machine à états
TestBulkCleaningOperations = BulkCleaningOperations.TestCase


if __name__ == '__main__':
    pytest.main([__file__])