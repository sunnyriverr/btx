#include <modelnet/relay_reserve.h>
#include <iostream>
#include <stdexcept>
using namespace modelnet;
void require(bool x,const char* s){if(!x)throw std::runtime_error(s);}
int main(){try{
 RelayLimits lim;lim.byte_ceiling=100;lim.ttl_ms=20;RelayTable table(lim);RelayReservation r;std::string err;
 require(table.Reserve("fixture","ng","203.0.113.1:29447",0,r,err),"reserve");
 require(table.AllowForward(r.reservation_id,0,1,err),"open");
 table.Expire(21);table.CloseConn(r.reservation_id);table.Expire(22);
 auto active=table.StatusJson()["active_forwarded"].getInt<int>();
 std::cout<<"expired_active_after_cleanup="<<active<<" remaining="<<table.Size()<<"\n";
 require(active==0&&table.Size()==0,"expired connection cleanup must release active count");
#ifdef CANDIDATE
 RelayTable pending(lim);require(pending.Reserve("fixture","ng","203.0.113.1:29447",0,r,err),"pending reserve");
 require(pending.AllowForward(r.reservation_id,0,1,err),"pending open");
 auto grant=pending.ReserveForwardBytes(r.reservation_id,100,2);require(grant==100,"pending grant");
 pending.Expire(21);require(pending.Has(r.reservation_id),"retain in-flight accounting");
 require(!pending.AllowForward(r.reservation_id,0,21,err),"deny new expired connection");
 require(pending.ReserveForwardBytes(r.reservation_id,1,21)==0,"deny new expired bytes");
 require(pending.FinishForwardBytes(r.reservation_id,grant,7,22),"reconcile actual short write at expiry");
 pending.CloseConn(r.reservation_id);pending.Expire(23);
 require(!pending.Has(r.reservation_id),"expired row removed after close");
 require(pending.StatusJson()["active_forwarded"].getInt<int>()==0,"pending active count clean");
 require(pending.ForwardedBytes()==7,"actual bytes preserved through expiry");
 std::cout<<"pending_expiry_cleanup=PASS forwarded=7 active=0\n";
#endif
 std::cout<<"PASS expiry cleanup\n";return 0;
}catch(const std::exception& e){std::cout<<"FAIL "<<e.what()<<"\n";return 1;}}
