"""Real CLI code paths, synthetic data only; no simulated production evidence."""
import json
from pathlib import Path
import pytest
from app.orb.adaptive.cli import main


@pytest.mark.parametrize('path,expected,filled',[
    ('fade','TARGET_FIRST',True),('reclaim','TARGET_FIRST',True),
    ('fade-fails','STOP_FIRST',True),('gap-filled','NO_ENTRY',False)])
def test_demo_command_outputs_trace_and_honest_result(tmp_path,path,expected,filled):
    assert main(['demo','--path',path,'--out',str(tmp_path)])==0
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['source_origin']=='SYNTHETIC'
    assert result['entry_filled']==filled
    position=result['end_state']['position']
    assert (position['label'] if position else 'NO_ENTRY')==expected
    assert 'null' in (tmp_path/'trace.jsonl').read_text()
    for name in ('trace.html','trace.md','policy.json','limits.json'):
        assert (tmp_path/name).stat().st_size>0


def test_cli_replay_and_outcome_side_datasets(tmp_path):
    assert main(['demo','--path','fade','--out',str(tmp_path)])==0
    args=['--data',str(tmp_path/'input.synthetic.json'),'--policy',str(tmp_path/'policy.json'),
          '--limits',str(tmp_path/'limits.json')]
    for command in ('replay','label-structural','label-actions'):
        target=tmp_path/(command+'.json')
        extra=['--anchor-minute','565'] if command=='label-actions' else []
        assert main([command,*args,'--out',str(target),*extra])==0
        assert isinstance(json.loads(target.read_text()),list)
    assert main(['replay',*args,'--data',str(tmp_path/'does-not-exist.json'),'--out',str(tmp_path/'bad.json')])==2


def test_secret_generator_no_overwrite_or_shared_proof(tmp_path):
    assert main(['generate-local-secrets','--out',str(tmp_path)])==0
    key=(tmp_path/'review-key.bin').read_bytes();token=(tmp_path/'api-token.txt').read_bytes()
    assert len(key)==48 and len(token)>=32
    assert main(['generate-local-secrets','--out',str(tmp_path)])==2
    assert (tmp_path/'review-key.bin').read_bytes()==key
    assert not tuple(tmp_path.glob('*proof*'))
