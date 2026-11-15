"""Exercise workflow validation and publishing guards without external services."""
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]


def step_script(filename, heading=None):
    source = (ROOT / '.github/workflows' / filename).read_text()
    if heading:
        source = source.split('      - name: ' + heading + '\n', 1)[1]
    source = source.split('        run: |\n', 1)[1].split('\n      - ', 1)[0]
    return textwrap.dedent(source)


def run_script(script, environment, directory=None):
    return subprocess.run(
        ['bash', '-e', '-c', script], env={**os.environ, **environment},
        cwd=directory, capture_output=True, text=True, check=False,
    ).returncode


class WorkflowTests(unittest.TestCase):
    def test_conventional_titles(self):
        script = step_script('pr-title.yml')
        for title, valid in [('feat(api)!: version change', True), ('ci: change workflows', True),
                             ('docs: update docs', True), ('invalid title', False),
                             ('fix: ', False), ('custom: message', False)]:
            with self.subTest(title=title):
                self.assertEqual(run_script(script, {'PR_TITLE': title}) == 0, valid)

    def test_promotion_requires_the_same_repository_and_digest(self):
        script = step_script('promote-image.yml', 'Check promotion source')
        image = 'ghcr.io/example/app'
        for source, valid in [(image + '@sha256:' + 'a' * 64, True),
                              (image + ':latest', False),
                              ('ghcr.io/other/app@sha256:' + 'a' * 64, False),
                              (image + '@sha256:bad', False)]:
            with self.subTest(source=source):
                self.assertEqual(run_script(script, {'IMAGE': image, 'SOURCE': source}) == 0, valid)

    def test_promotion_copies_the_released_manifest_and_propagates_errors(self):
        script = step_script('promote-image.yml', 'Promote the released manifest')
        for failure in ('', 'buildx'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                log = directory / 'calls'
                docker = directory / 'docker'
                docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
                                  'if [ "$1" = login ]; then cat >/dev/null; fi\n'
                                  '[ "$1" != "$FAILURE" ]\n')
                docker.chmod(0o755)
                source = 'ghcr.io/example/app@sha256:' + 'a' * 64
                environment = {'PATH': str(directory) + os.pathsep + os.environ['PATH'],
                               'CALL_LOG': str(log), 'FAILURE': failure, 'TOKEN': 'fixture-only',
                               'GITHUB_ACTOR': 'fixture', 'IMAGE': 'ghcr.io/example/app', 'SOURCE': source}
                self.assertEqual(run_script(script, environment), 1 if failure else 0)
                calls = log.read_text()
                self.assertIn('--prefer-index=false --tag ghcr.io/example/app:latest ' + source, calls)
                self.assertTrue(calls.rstrip().endswith('logout ghcr.io'))

    def test_python_discovery_handles_paths_patterns_and_test_failures(self):
        script = step_script('python-tests.yml', 'Run Python tests')
        for failing in (False, True):
            with self.subTest(failing=failing), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                tests = directory / 'custom tests'
                tests.mkdir()
                (tests / '__init__.py').touch()
                (tests / 'case_sample.py').write_text(
                    'import unittest\nclass Sample(unittest.TestCase):\n'
                    '    def test_result(self):\n        self.assertTrue(' + str(not failing) + ')\n')
                (tests / 'test_ignored.py').write_text('raise RuntimeError("wrong pattern")\n')
                for top_level in ('', str(directory)):
                    environment = {'TEST_DIRECTORY': str(tests), 'TEST_PATTERN': 'case*.py',
                                   'TOP_LEVEL_DIRECTORY': top_level}
                    self.assertEqual(run_script(script, environment) == 0, not failing)

    def test_legacy_python_inputs_remain_usable_during_migration(self):
        source = (ROOT / '.github/workflows/python-tests.yml').read_text()
        script = source.split('      - name: Run legacy caller tests during migration\n', 1)[1]
        script = script.split('        run: ', 1)[1].split('\n', 1)[0]
        self.assertEqual(run_script(script, {'TEST_COMMAND': 'true'}), 0)
        self.assertNotEqual(run_script(script, {'TEST_COMMAND': 'false | true'}), 0)

    def test_maven_prerequisites_fail_before_verification(self):
        source = (ROOT / '.github/workflows/java-build-publish.yml').read_text()
        self.assertLess(source.index('name: Run project prerequisites'),
                        source.index('run: ./mvnw --batch-mode verify'))
        script = source.split('      - name: Run project prerequisites\n', 1)[1]
        script = script.split('        run: ', 1)[1].split('\n', 1)[0]
        self.assertNotEqual(run_script(script, {'CHECK_COMMAND': 'false'}), 0)

    def test_language_test_workflows_delegate_with_publication_disabled(self):
        for language, implementation in [('java', 'java-build-publish.yml'),
                                         ('npm', 'npm-build-publish.yml')]:
            with self.subTest(language=language):
                source = (ROOT / '.github/workflows' / (language + '-tests.yml')).read_text()
                self.assertIn('  workflow_call:', source)
                self.assertIn('uses: ./.github/workflows/' + implementation, source)
                self.assertIn('      publish: false', source)
                self.assertNotIn('      publish:\n', source)
                self.assertNotIn('      repository:', source)
                self.assertNotIn('command:', source)
        npm = (ROOT / '.github/workflows/npm-tests.yml').read_text()
        self.assertIn('      test-script: test', npm)
        self.assertIn("      build-script: ''", npm)
        python = (ROOT / '.github/workflows/python-tests.yml').read_text()
        self.assertNotIn('      repository:', python)
        self.assertIn('      test-directory:\n        type: string\n        default: tests', python)
        maven = (ROOT / '.github/workflows/java-build-publish.yml').read_text()
        self.assertIn('run: ./mvnw --batch-mode verify', maven)

    def test_package_publish_requires_release_context_and_token(self):
        for filename, heading, token, executable in [
            ('npm-build-publish.yml', 'Publish package', 'NODE_AUTH_TOKEN', 'npm'),
            ('java-build-publish.yml', 'Publish artifacts', 'MAVEN_TOKEN', 'mvnw'),
        ]:
            with self.subTest(workflow=filename), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                marker = directory / 'published'
                stub = directory / executable
                stub.write_text('#!/bin/sh\ntouch "$MARKER"\n')
                stub.chmod(0o755)
                script = step_script(filename, heading)
                environment = {'PATH': str(directory) + os.pathsep + os.environ['PATH'],
                               'MARKER': str(marker), token: 'fixture-only'}
                self.assertNotEqual(run_script(script, {**environment, 'EVENT_NAME': 'pull_request'}, directory), 0)
                self.assertFalse(marker.exists())
                self.assertNotEqual(run_script(script, {**environment, 'EVENT_NAME': 'push', token: ''}, directory), 0)
                self.assertFalse(marker.exists())
                self.assertEqual(run_script(script, {**environment, 'EVENT_NAME': 'push'}, directory), 0)
                self.assertTrue(marker.exists())


if __name__ == '__main__':
    unittest.main()
