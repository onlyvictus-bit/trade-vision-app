import importlib.util
from pathlib import Path
import subprocess
import pytest


def installer_module():
    # Source bundle test. Host installed suite has no installer at repository
    # root; integration behavior is then tested by the remaining AFRE suite.
    here=Path(__file__).resolve()
    target=next((p/'install_afre.py' for p in here.parents if (p/'install_afre.py').exists()),None)
    if target is None:pytest.skip('Bundle installer tested only from release bundle')
    spec=importlib.util.spec_from_file_location('afre_installer_test',target)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def repo_fixture(tmp_path,module):
    repo=tmp_path/'repo';repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    for relative in module.EXPORTS:
        path=repo/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('app = object()\n' if path.name=='main.py' else 'BASELINE_SENTINEL = True\n')
    subprocess.run(['git','-C',str(repo),'add','.'],check=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=TEST','-c','user.email=test@example.invalid','commit','-qm','test fixture'],check=True)
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    bundle=tmp_path/'bundle';path=bundle/'overlay'/'apps/api/app/orb/adaptive'
    path.mkdir(parents=True);(path/'example.py').write_text('VALID = True\n')
    return repo,bundle,head


def test_installer_dry_run_apply_idempotence_and_backup(tmp_path):
    m=installer_module();repo,bundle,head=repo_fixture(tmp_path,m)
    original=(repo/'apps/api/app/main.py').read_bytes()
    report=m.install(repo,bundle,expected_commit=head)
    assert report['changes']==6 and (repo/'apps/api/app/main.py').read_bytes()==original
    done=m.install(repo,bundle,apply=True,expected_commit=head)
    backup=Path(done['backup_directory'])
    assert (backup/'apps/api/app/main.py').read_bytes()==original
    assert m.install(repo,bundle,apply=True,expected_commit=head)['changes']==0


def test_installer_refuses_local_edits_and_wrong_commit(tmp_path):
    m=installer_module();repo,bundle,head=repo_fixture(tmp_path,m)
    with pytest.raises(ValueError):m.install(repo,bundle,expected_commit='wrong')
    target=repo/'apps/api/app/main.py';target.write_text('LOCAL_WORK = True\n')
    with pytest.raises(ValueError):m.install(repo,bundle,apply=True,expected_commit=head)
    assert target.read_text()=='LOCAL_WORK = True\n'


def test_rollback_preserves_post_install_edits_and_restores_exact_baseline(tmp_path, monkeypatch):
    m=installer_module();repo,bundle,head=repo_fixture(tmp_path,m)
    module_path=Path(m.__file__).with_name('rollback_afre.py')
    monkeypatch.syspath_prepend(str(module_path.parent))
    spec=importlib.util.spec_from_file_location('afre_rollback_test',module_path)
    rb=importlib.util.module_from_spec(spec);spec.loader.exec_module(rb)
    baseline={r:(repo/r).read_bytes() for r in m.EXPORTS}
    done=m.install(repo,bundle,apply=True,expected_commit=head)
    backup=Path(done['backup_directory'])
    assert rb.rollback(repo,backup)['restore_or_remove']==6
    target=repo/'apps/api/app/main.py';installed=target.read_bytes()
    target.write_bytes(installed+b'LOCAL_EDIT = True\n')
    with pytest.raises(ValueError):rb.rollback(repo,backup,apply=True)
    target.write_bytes(installed)
    assert rb.rollback(repo,backup,apply=True)['database_touched'] is False
    assert all((repo/r).read_bytes()==data for r,data in baseline.items())
    assert not (repo/'apps/api/app/orb/adaptive/example.py').exists()


def test_installer_refuses_symlink_destination_escape(tmp_path):
    m=installer_module();repo,bundle,head=repo_fixture(tmp_path,m)
    outside=tmp_path/'outside';outside.mkdir()
    target=repo/'apps/api/app/orb/adaptive'
    try:target.symlink_to(outside,target_is_directory=True)
    except OSError:pytest.skip('OS requires symlink privilege')
    with pytest.raises(ValueError,match='UNSAFE_SYMLINK_DESTINATION'):
        m.install(repo,bundle,apply=True,expected_commit=head)
    assert not tuple(outside.iterdir())
