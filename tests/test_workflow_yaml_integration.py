"""
Integration tests for the workflow script parsing YAML filter and release_types.
"""
import pytest
import subprocess
import tempfile
import os
import json
from pathlib import Path


class TestWorkflowScriptIntegration:
    """Integration tests for release-matching-python-tags.yml workflow script."""

    def test_yaml_parsing_inline_array(self):
        """Test the Python YAML parsing logic used in workflow."""
        yaml_content = """version: 3.14.*
release_types: [stable, beta]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            # Simulate the Python snippet from the workflow
            python_code = f"""
import yaml
with open('{temp_file}', 'r') as f:
    config = yaml.safe_load(f)
    version = config.get('version', '')
    release_types = config.get('release_types', ['stable'])
    if isinstance(release_types, str):
        release_types = [release_types]
    print(f"VERSION_FILTER={{version}}")
    print("RELEASE_TYPES=" + ' '.join(release_types))
"""
            result = subprocess.run(
                ['python3', '-c', python_code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.strip()
            assert 'VERSION_FILTER=3.14.*' in output
            assert 'RELEASE_TYPES=stable beta' in output
        finally:
            os.unlink(temp_file)

    def test_yaml_parsing_multiline_array(self):
        """Test parsing YAML with multi-line array."""
        yaml_content = """version: 3.13.*
release_types:
  - stable
  - rc
  - beta
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            python_code = f"""
import yaml
with open('{temp_file}', 'r') as f:
    config = yaml.safe_load(f)
    version = config.get('version', '')
    release_types = config.get('release_types', ['stable'])
    if isinstance(release_types, str):
        release_types = [release_types]
    print(f"VERSION_FILTER={{version}}")
    print("RELEASE_TYPES=" + ' '.join(release_types))
"""
            result = subprocess.run(
                ['python3', '-c', python_code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.strip()
            assert 'VERSION_FILTER=3.13.*' in output
            assert 'RELEASE_TYPES=stable rc beta' in output
        finally:
            os.unlink(temp_file)

    def test_yaml_parsing_empty_file(self):
        """Test parsing empty YAML file gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_file = f.name
        
        try:
            python_code = f"""
import yaml
with open('{temp_file}', 'r') as f:
    config = yaml.safe_load(f)
    if config is None:
        version = ''
        release_types = ['stable']
    else:
        version = config.get('version', '')
        release_types = config.get('release_types', ['stable'])
    if isinstance(release_types, str):
        release_types = [release_types]
    print(f"VERSION_FILTER={{version}}")
    print("RELEASE_TYPES=" + ' '.join(release_types))
"""
            result = subprocess.run(
                ['python3', '-c', python_code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.strip()
            assert 'VERSION_FILTER=' in output
            assert 'RELEASE_TYPES=stable' in output
        finally:
            os.unlink(temp_file)

    def test_yaml_parsing_with_comments(self):
        """Test that YAML parser correctly handles comments."""
        yaml_content = """# This is a comment
version: 3.14.*
# Another comment
release_types: [stable]  # Inline comment
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            python_code = f"""
import yaml
with open('{temp_file}', 'r') as f:
    config = yaml.safe_load(f)
    version = config.get('version', '')
    release_types = config.get('release_types', ['stable'])
    if isinstance(release_types, str):
        release_types = [release_types]
    print(f"VERSION_FILTER={{version}}")
    print("RELEASE_TYPES=" + ' '.join(release_types))
"""
            result = subprocess.run(
                ['python3', '-c', python_code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.strip()
            assert 'VERSION_FILTER=3.14.*' in output
            assert 'RELEASE_TYPES=stable' in output
        finally:
            os.unlink(temp_file)

    def test_filter_to_command_args_conversion(self):
        """Test converting filter values to shell command arguments."""
        test_cases = [
            (['stable'], 'stable'),
            (['stable', 'beta'], 'stable beta'),
            (['stable', 'rc', 'beta', 'alpha'], 'stable rc beta alpha'),
            ('stable', 'stable'),  # string gets normalized
        ]
        
        for release_types, expected in test_cases:
            python_code = f"""
release_types = {repr(release_types)}
if isinstance(release_types, str):
    release_types = [release_types]
print(' '.join(release_types))
"""
            result = subprocess.run(
                ['python3', '-c', python_code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.strip()
            assert output == expected, f"Expected '{expected}', got '{output}'"

    def test_version_filter_derivation(self):
        """Test deriving filter from latest version."""
        python_code = """
import re
versions = ['3.14.5', '3.13.2', '3.12.10']
latest = max(versions, key=lambda v: tuple(map(int, v.split('.'))))
# Convert latest version like 3.14.5 to 3.14.*
filter_pattern = '.'.join(latest.split('.')[:2]) + '.*'
print(filter_pattern)
"""
        result = subprocess.run(
            ['python3', '-c', python_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout.strip()
        assert output == '3.14.*'


class TestCommandLineIntegration:
    """Test command-line argument parsing for release_types."""

    def test_release_types_cli_parsing(self):
        """Test that CLI arguments are correctly parsed as list."""
        python_code = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--release-types', type=str, nargs='+', default=['stable'])
args = parser.parse_args(['--release-types', 'stable', 'beta', 'rc'])
print(' '.join(args.release_types))
"""
        result = subprocess.run(
            ['python3', '-c', python_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout.strip()
        assert output == 'stable beta rc'

    def test_release_types_cli_default(self):
        """Test CLI default for release_types."""
        python_code = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--release-types', type=str, nargs='+', default=['stable'])
args = parser.parse_args([])
print(' '.join(args.release_types))
"""
        result = subprocess.run(
            ['python3', '-c', python_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout.strip()
        assert output == 'stable'

    def test_release_types_cli_single_value(self):
        """Test CLI with single release type."""
        python_code = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--release-types', type=str, nargs='+', default=['stable'])
args = parser.parse_args(['--release-types', 'alpha'])
print(' '.join(args.release_types))
"""
        result = subprocess.run(
            ['python3', '-c', python_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout.strip()
        assert output == 'alpha'


class TestEdgeCases:
    """Test edge cases in workflow script parsing."""

    def test_yaml_with_special_characters_in_values(self):
        """Test YAML with special characters."""
        yaml_content = """version: "3.14.*"
release_types: ["stable", "beta"]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            python_code = f"""
import yaml
with open('{temp_file}', 'r') as f:
    config = yaml.safe_load(f)
    assert config['version'] == '3.14.*'
    assert config['release_types'] == ['stable', 'beta']
    print('OK')
"""
            result = subprocess.run(
                ['python3', '-c', python_code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            assert 'OK' in result.stdout
        finally:
            os.unlink(temp_file)

    def test_yaml_with_extra_whitespace(self):
        """Test YAML with extra whitespace."""
        yaml_content = """version:   3.14.*
release_types:   [ stable ,  beta  ]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            python_code = f"""
import yaml
with open('{temp_file}', 'r') as f:
    config = yaml.safe_load(f)
    # YAML parser handles whitespace
    assert config['version'] == '3.14.*'
    assert config['release_types'] == ['stable', 'beta']
    print('OK')
"""
            result = subprocess.run(
                ['python3', '-c', python_code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            assert 'OK' in result.stdout
        finally:
            os.unlink(temp_file)

    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML."""
        yaml_content = """version: 3.14.*
release_types: [stable
# Missing closing bracket
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            python_code = f"""
import yaml
try:
    with open('{temp_file}', 'r') as f:
        config = yaml.safe_load(f)
    print('PARSED')
except yaml.YAMLError as e:
    print('YAML_ERROR')
"""
            result = subprocess.run(
                ['python3', '-c', python_code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Invalid YAML should raise an error
            assert 'ERROR' in result.stdout or result.returncode != 0
        finally:
            os.unlink(temp_file)
