"""
Requirements evaluation engine.
"""
import yaml
from pathlib import Path
from typing import Dict, List, Set, Optional
from django.conf import settings


class RequirementNode:
    """Represents a requirement node in the tree."""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.type = config.get('type', 'LEAF')
        self.children = []
        
        if self.type in ['ALL_OF', 'ANY_OF', 'N_OF']:
            if 'requirements' in config:
                for child_config in config['requirements']:
                    if isinstance(child_config, dict):
                        child_name = child_config.get('name', '')
                        self.children.append(RequirementNode(child_name, child_config))
                    elif isinstance(child_config, str):
                        # Simple course code
                        self.children.append(RequirementNode(child_config, {'type': 'LEAF', 'courses': [child_config]}))
        
        if self.type == 'N_OF':
            self.n = config.get('n', 1)
        else:
            self.n = None
    
    def evaluate(self, completed_codes: Set[str], in_progress_codes: Set[str], equivalencies: Dict[str, List[str]] = None) -> Dict:
        """
        Evaluate requirement status.
        
        Returns:
        {
            'status': 'satisfied' | 'partial' | 'missing',
            'satisfied_by': [course_codes],
            'still_needed': [requirements],
            'in_progress_that_would_satisfy': [course_codes]
        }
        """
        if equivalencies is None:
            equivalencies = {}
        
        # Expand codes with equivalencies
        def expand_code(code: str) -> Set[str]:
            result = {code}
            if code in equivalencies:
                result.update(equivalencies[code])
            return result
        
        if self.type == 'LEAF':
            # Leaf node: list of course codes
            courses = self.config.get('courses', [])
            satisfied_codes = []
            in_progress_codes_found = []
            
            for course in courses:
                expanded = expand_code(course)
                if expanded & completed_codes:
                    satisfied_codes.append(course)
                elif expanded & in_progress_codes:
                    in_progress_codes_found.append(course)
            
            if satisfied_codes:
                status = 'satisfied'
            elif in_progress_codes_found:
                status = 'partial'
            else:
                status = 'missing'
            
            return {
                'status': status,
                'satisfied_by': satisfied_codes,
                'still_needed': [c for c in courses if c not in satisfied_codes],
                'in_progress_that_would_satisfy': in_progress_codes_found
            }
        
        elif self.type == 'ALL_OF':
            # All children must be satisfied
            child_results = [child.evaluate(completed_codes, in_progress_codes, equivalencies) for child in self.children]
            
            all_satisfied = all(r['status'] == 'satisfied' for r in child_results)
            any_partial = any(r['status'] == 'partial' for r in child_results)
            
            if all_satisfied:
                status = 'satisfied'
            elif any_partial or any(r['status'] == 'satisfied' for r in child_results):
                status = 'partial'
            else:
                status = 'missing'
            
            satisfied_by = []
            still_needed = []
            in_progress_that_would_satisfy = []
            
            for result in child_results:
                satisfied_by.extend(result['satisfied_by'])
                still_needed.extend(result['still_needed'])
                in_progress_that_would_satisfy.extend(result['in_progress_that_would_satisfy'])
            
            result = {
                'status': status,
                'satisfied_by': list(set(satisfied_by)),
                'still_needed': list(set(still_needed)),
                'in_progress_that_would_satisfy': list(set(in_progress_that_would_satisfy)),
                'children': child_results,
                'name': self.name
            }
            return result
        
        elif self.type == 'ANY_OF':
            # At least one child must be satisfied
            child_results = [child.evaluate(completed_codes, in_progress_codes, equivalencies) for child in self.children]
            
            any_satisfied = any(r['status'] == 'satisfied' for r in child_results)
            any_partial = any(r['status'] == 'partial' for r in child_results)
            
            if any_satisfied:
                status = 'satisfied'
            elif any_partial:
                status = 'partial'
            else:
                status = 'missing'
            
            # For ANY_OF, we take the first satisfied or partial
            satisfied_by = []
            still_needed = []
            in_progress_that_would_satisfy = []
            
            for result in child_results:
                if result['status'] == 'satisfied':
                    satisfied_by = result['satisfied_by']
                    break
                elif result['status'] == 'partial' and not satisfied_by:
                    satisfied_by = result['satisfied_by']
                    in_progress_that_would_satisfy = result['in_progress_that_would_satisfy']
            
            # Still needed: all unsatisfied requirements
            for result in child_results:
                if result['status'] != 'satisfied':
                    still_needed.extend(result['still_needed'])
            
            result = {
                'status': status,
                'satisfied_by': list(set(satisfied_by)),
                'still_needed': list(set(still_needed)),
                'in_progress_that_would_satisfy': list(set(in_progress_that_would_satisfy)),
                'children': child_results,
                'name': self.name
            }
            return result
        
        elif self.type == 'N_OF':
            # N of the children must be satisfied
            child_results = [child.evaluate(completed_codes, in_progress_codes, equivalencies) for child in self.children]
            
            satisfied_count = sum(1 for r in child_results if r['status'] == 'satisfied')
            partial_count = sum(1 for r in child_results if r['status'] == 'partial' for r in child_results)
            
            if satisfied_count >= self.n:
                status = 'satisfied'
            elif satisfied_count + partial_count >= self.n:
                status = 'partial'
            else:
                status = 'missing'
            
            satisfied_by = []
            still_needed = []
            in_progress_that_would_satisfy = []
            
            for result in child_results:
                satisfied_by.extend(result['satisfied_by'])
                if result['status'] != 'satisfied':
                    still_needed.extend(result['still_needed'])
                in_progress_that_would_satisfy.extend(result['in_progress_that_would_satisfy'])
            
            result = {
                'status': status,
                'satisfied_by': list(set(satisfied_by)),
                'still_needed': list(set(still_needed)),
                'in_progress_that_would_satisfy': list(set(in_progress_that_would_satisfy)),
                'children': child_results,
                'satisfied_count': satisfied_count,
                'needed_count': self.n,
                'name': self.name
            }
            return result
        
        return {
            'status': 'missing',
            'satisfied_by': [],
            'still_needed': [],
            'in_progress_that_would_satisfy': []
        }


class RequirementsEngine:
    """Main requirements evaluation engine."""
    
    def __init__(self, requirements_file: str = None, equivalencies_file: str = None):
        self.requirements_dir = Path(settings.REQUIREMENTS_DIR)
        
        if requirements_file is None:
            requirements_file = self.requirements_dir / 'core_v1.yaml'
        else:
            requirements_file = Path(requirements_file)
        
        if equivalencies_file is None:
            equivalencies_file = self.requirements_dir / 'equivalencies.yaml'
        else:
            equivalencies_file = Path(equivalencies_file)
        
        # Load requirements
        with open(requirements_file, 'r') as f:
            requirements_data = yaml.safe_load(f)
        
        # Load equivalencies
        self.equivalencies = {}
        if equivalencies_file.exists():
            with open(equivalencies_file, 'r') as f:
                equivalencies_data = yaml.safe_load(f) or {}
                self.equivalencies = equivalencies_data.get('equivalencies', {})
        
        # Build requirement tree
        self.root = RequirementNode('root', requirements_data)
    
    def evaluate(self, completed_codes: Set[str], in_progress_codes: Set[str] = None) -> Dict:
        """
        Evaluate all requirements.
        
        Args:
            completed_codes: Set of completed course codes (base codes only)
            in_progress_codes: Set of in-progress course codes
        
        Returns:
            Evaluation result dictionary
        """
        if in_progress_codes is None:
            in_progress_codes = set()
        
        return self.root.evaluate(completed_codes, in_progress_codes, self.equivalencies)
