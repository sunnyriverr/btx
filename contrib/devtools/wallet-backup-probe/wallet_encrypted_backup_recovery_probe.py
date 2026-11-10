#!/usr/bin/env python3
"""Disposable supported-backup probe. Planning fixture; not yet executed natively."""
import json
from decimal import Decimal
from pathlib import Path
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal
from test_framework.authproxy import JSONRPCException
from result_contract import classify

class EncryptedBackupRecoveryProbe(BitcoinTestFramework):
    def add_options(self, parser):
        self.add_wallet_options(parser, legacy=False)
        parser.add_argument('--diagnostic-mining',action='store_true',help='Explicit economic/cpu-diagnostic test policy; not default-consensus qualification')
    def set_test_params(self):
        self.num_nodes=1;self.setup_clean_chain=True
        args=['-keypool=4','-modelnet=0','-autoshieldcoinbase=0','-connect=0','-dnsseed=0']
        if self.options.diagnostic_mining:args+=['-matmulvalidation=economic','-matmulrcexecution=cpu-diagnostic']
        self.extra_args=[args]
    def skip_test_if_missing_module(self):self.skip_if_no_wallet();self.skip_if_no_sqlite()
    def run_test(self):
        node=self.nodes[0];record={'diagnostic_mining':self.options.diagnostic_mining}
        # Evidence lives in the disposable framework runtime, never a personal wallet.
        output=Path(self.options.tmpdir)/'recovery-observation.json'
        def save():output.write_text(json.dumps(dict(record,classification=classify(record)),indent=2)+'\n')
        receipt_txids=[]
        def coins(wallet,addresses):
            # Receipt recognition is independent of a locked wallet's coin-selection solvability.
            rows=[]
            for txid in receipt_txids:
                try:tx=wallet.gettransaction(txid)
                except JSONRPCException as e:
                    if e.error['code']==-5:continue
                    raise
                assert tx['confirmations']>=1
                rows += [(f"{txid}:{v['vout']}",v['amount']) for v in tx['details'] if v['category']=='receive' and v.get('address') in addresses]
            return sorted(x[0] for x in rows),sum((x[1] for x in rows),Decimal(0))
        phrase='disposable-regtest-only'
        try:
            node.createwallet(wallet_name='funder',descriptors=True)
            funder=node.get_wallet_rpc('funder');burn=funder.getnewaddress()
            self.generatetoaddress(node,101,burn,sync_fun=self.no_op)
            cases={}
            for name,encrypted in [('encrypted',True),('plain',False)]:
                node.createwallet(wallet_name=name,descriptors=True,**({'passphrase':phrase} if encrypted else {}))
                wallet=node.get_wallet_rpc(name)
                if encrypted:wallet.walletpassphrase(phrase,600)
                known=wallet.getnewaddress();remaining=wallet.getwalletinfo()['keypoolsize']
                assert 0<remaining<=32,'Unexpected external lookahead; inspect before enlarging fixture'
                backup=Path(node.datadir_path)/(name+'-stale.bak');wallet.backupwallet(str(backup))
                for _ in range(remaining+1):far=wallet.getnewaddress()
                assert far!=known
                if encrypted:wallet.walletlock()
                cases[name]={'wallet':wallet,'addresses':[known,far],'backup':backup,'lookahead_remaining':remaining}
            # Separate blocks let unencrypted startup top-up on the known script before seeing far.
            for position in (0,1):
                destinations={c['addresses'][position]:Decimal(position+1) for c in cases.values()}
                receipt_txids.append(funder.sendmany('',destinations))
                self.generatetoaddress(node,1,burn,sync_fun=self.no_op)
            record['funded']=True
            for name,c in cases.items():
                expected,total=coins(c['wallet'],c['addresses']);assert len(expected)==2;assert_equal(total,Decimal(3))
                c['expected']=expected;c['total']=total
                node.unloadwallet(name)
            record['current_control']=True
            plain=cases['plain'];node.restorewallet('plain-restored',str(plain['backup']));pr=node.get_wallet_rpc('plain-restored')
            po,pb=coins(pr,plain['addresses']);assert_equal(po,plain['expected']);assert_equal(pb,plain['total']);record['plain_restore_control']=True
            c=cases['encrypted'];record['expected_outpoints']=c['expected'];record['lookahead_remaining']=c['lookahead_remaining']
            restored=node.restorewallet('encrypted-restored',str(c['backup']));wallet=node.get_wallet_rpc('encrypted-restored')
            record['restore_warnings']=restored.get('warnings',[])
            assert_equal(wallet.getwalletinfo()['unlocked_until'],0);record['restored_locked']=True
            record['after_restore_outpoints']=coins(wallet,c['addresses'])[0]
            before=node.getbestblockhash()
            wallet.walletpassphrase(phrase,600);record['unlock_succeeded']=True
            record['far_ismine_after_unlock']=wallet.getaddressinfo(c['addresses'][1])['ismine']
            record['after_unlock_outpoints']=coins(wallet,c['addresses'])[0]
            if record['after_unlock_outpoints']!=c['expected'] and record['far_ismine_after_unlock']:
                scanned=wallet.rescanblockchain(0)
                record['manual_scan_complete']=scanned.get('stop_height')==node.getblockcount()
                record['after_manual_outpoints'],total=coins(wallet,c['addresses'])
                record['manual_balance_matches']=total==c['total']
            record['same_tip']=before==node.getbestblockhash();record['phase_complete']=True
            wallet.walletlock();assert_equal(wallet.getwalletinfo()['unlocked_until'],0)
        except Exception as e:
            record['error_type']=type(e).__name__;record['error']='Probe stopped; inspect framework log, do not interpret as recovery failure'
            raise
        finally:save()
        assert classify(record)!='INCOMPLETE','Observation did not classify; retain raw evidence'
if __name__=='__main__':EncryptedBackupRecoveryProbe(__file__).main()
