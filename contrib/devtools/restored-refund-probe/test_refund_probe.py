"""Component diagnosis only; deterministic chain/signing and actual SQLite/coordinator."""
import json,hashlib
from dataclasses import asdict
from pathlib import Path
import pytest
from test_execution_v2 import pair,A
from test_restored_history import setup,TXID
from swapnet.authorization import Principal
from swapnet.fee_bump import bump
from swapnet.errors import SwapError


def test_restored_original_refund_bump_diagnosis(pair):
    c,d,h=setup(pair,'unique');leg=pair.state('alice')['agreement']['long_leg']
    h.add(TXID,0)
    c.tick_one(pair.sid);c.tick_one(pair.sid)
    state=pair.state('alice');assert 'fund_op' not in state and state['refs']['a']=={'txid':TXID,'vout':0}
    assert d.funding_calls==0 and state['recovery_ready']
    # Extend the existing history fixture's original lock into its deterministic
    # observation ledger. No new funding operation or broadcast is performed.
    pair.a.records[TXID]={'terms':leg,'state':'locked','confirmations':3,'preimage':None}
    pair.a.height=leg['lock_value']
    st,j,auth,_=pair.nodes['alice']
    def snap():return {'state':j.load(pair.sid),'ops':j.operations(pair.sid,private=True),'budget':st.db.execute('SELECT held,used FROM mandates').fetchall(),'funding_calls':d.funding_calls,'transactions':dict(pair.a.transactions),'original':dict(pair.a.records[TXID])}
    before=snap();assert before['ops'] and all(x['kind']!='fund' for x in before['ops'])
    assert int(before['ops'][-1]['metadata']['fee_atoms'])<20<=int(leg['max_refund_fee_atoms'])
    # Safety controls must reject and leave every tracked effect unchanged.
    with pytest.raises(SwapError,match='FEE_CAP'):bump(c,Principal('alice'),pair.sid,'refund','101')
    assert snap()==before
    with pytest.raises(SwapError,match='FORBIDDEN'):bump(c,Principal('other'),pair.sid,'refund','20')
    assert snap()==before
    pair.a.height=leg['lock_value']-1
    with pytest.raises(SwapError,match='REFUND_EARLY'):bump(c,Principal('alice'),pair.sid,'refund','20')
    pair.a.height=leg['lock_value'];assert snap()==before
    with pytest.raises(KeyError) as err:bump(c,Principal('alice'),pair.sid,'refund','20')
    assert err.value.args==('fund_op',);assert snap()==before
    # Reopen real SQLite/coordinator and reattach the same saved history driver;
    # the injected/deterministic ledger remains unchanged.
    pair.restart('alice');c=pair.nodes['alice'][3];c.drivers[A]=d;st,j,auth,_=pair.nodes['alice']
    reopened=snap();assert reopened==before
    with pytest.raises(KeyError) as err:bump(c,Principal('alice'),pair.sid,'refund','20')
    assert err.value.args==('fund_op',);assert snap()==before
    Path('probe-result.json').write_text(json.dumps({'result':'REPRODUCED','exception':'KeyError: fund_op','before_and_after_reopen':True,'original_reference':state['refs']['a'],'original_funding_calls':d.funding_calls,'fund_ops':0,'original_refund_sha256':hashlib.sha256(before['ops'][0]['raw'].encode()).hexdigest(),'state_operations_budget_and_transactions_unchanged':True,'caps_crossprincipal_maturity_controls':'PASS','scope':'RealSQLite/coordinator/refundbump; deterministic history/chain/signing. Knownoriginal fixture, no native blockchain/funding orfee-bump repair.'},indent=2))
