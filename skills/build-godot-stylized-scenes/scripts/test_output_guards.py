#!/usr/bin/env python3
"""Standard-library regression for tree/card write guards and read-only checks."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys
from bundle_paths import fresh_output
ROOT = Path(__file__).resolve().parents[1]

def digests(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    work = fresh_output(parser.parse_args().output)
    # Exercise protected installation targets in a throwaway installation copy,
    # never in the live skill, even if a regression breaks the path checks.
    installed = work / 'installed-skill'
    scripts = installed / 'scripts'
    scripts.mkdir(parents=True)
    for name in ['generate_branching_trees.py', 'bake_bare_forest_card.py', 'bundle_paths.py']:
        shutil.copy2(ROOT / 'scripts' / name, scripts / name)
    original = digests(installed)
    checks = []
    def run(script, output, *, check=False, rejected=False):
        cmd = [sys.executable, str(scripts / script), '--output', str(output)]
        if check:
            cmd.append('--check')
        result = subprocess.run(cmd, cwd=work, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        (work / f'{len(checks):02d}.log').write_text(result.stdout)
        assert (result.returncode != 0) == rejected, result.stdout[-3000:]
        if rejected:
            assert 'Output' in result.stdout and 'ValueError' in result.stdout, 'Unexpected failure reason'
        checks.append({'script': script, 'check_mode': check, 'rejection_expected': rejected, 'exit': result.returncode})

    trees = work / 'trees'
    run('generate_branching_trees.py', trees)
    before = digests(trees)
    run('generate_branching_trees.py', trees, check=True)
    assert digests(trees) == before, '--check changed tree outputs'
    run('generate_branching_trees.py', trees, rejected=True)
    assert digests(trees) == before, 'Existing tree outputs changed on rejection'
    empty = work / 'empty'; empty.mkdir()
    run('generate_branching_trees.py', empty)
    assert digests(empty) == before, 'Existing empty directory should be accepted'
    run('generate_branching_trees.py', installed / 'forbidden-trees', rejected=True)
    assert not (installed / 'forbidden-trees').exists()

    card = work / 'card.svg'  # Parent already exists and contains other files.
    run('bake_bare_forest_card.py', card)
    before_card = card.read_bytes()
    run('bake_bare_forest_card.py', card, check=True)
    assert card.read_bytes() == before_card, '--check changed SVG'
    run('bake_bare_forest_card.py', card, rejected=True)
    assert card.read_bytes() == before_card, 'Existing SVG changed on rejection'
    run('bake_bare_forest_card.py', installed / 'forbidden.svg', rejected=True)
    assert not (installed / 'forbidden.svg').exists()
    if hasattr(os, 'symlink'):
        alias = work / 'skill-alias'; alias.symlink_to(installed, target_is_directory=True)
        run('bake_bare_forest_card.py', alias / 'forbidden.svg', rejected=True)
        run('generate_branching_trees.py', alias / 'forbidden-trees', rejected=True)
    assert digests(installed) == original, 'Throwaway installation was modified'
    result = {'status': 'PASS', 'checks': checks, 'scope': 'Standard-library output guards, no native engine or external packages.'}
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'commands': len(checks)}))

if __name__ == '__main__':
    main()
