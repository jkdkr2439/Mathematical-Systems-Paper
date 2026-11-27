"""Independent finite diagnostics for the mathematical manuscript. Standard library only."""
from fractions import Fraction as F
from itertools import product,combinations
from pathlib import Path
import argparse,json,hashlib,subprocess,re,random,platform,sys
HERE=Path(__file__).resolve().parent
def basis(rows):
    piv={}
    for row in rows:
        while row:
            j=row.bit_length()-1
            if j in piv:row^=piv[j]
            else:piv[j]=row;break
    return tuple(piv[j] for j in sorted(piv,reverse=True))
def dot(u,x):return (u&x).bit_count()%2
def mv(A,x):return sum(dot(u,x)<<i for i,u in enumerate(A))
def pull(u,A):
    v=0
    for i,a in enumerate(A):
        if u>>i&1:v^=a
    return v
def words(events,b):
    yield ()
    for e,(_,_,c) in enumerate(events):
        if c<=b:
            for w in words(events,b-c):yield (e,)+w
def evolve(x,events,w):
    for e in w:
        A,a,_=events[e];x=mv(A,x)^a
    return x
def affine_checks():
    rng=random.Random(281126);models=states=updates=0
    for n in range(1,5):
        for trial in range(12):
            C=[rng.randrange(1<<n) for _ in range(2)]
            events=[([rng.randrange(1<<n) for _ in range(n)],rng.randrange(1<<n),c) for c in [1,2]]
            spaces=[]
            for b in range(4):
                rows=list(C)
                for A,a,c in events:
                    if c<=b:rows += [pull(u,A) for u in spaces[b-c]]
                B=basis(rows);spaces.append(B);ww=list(words(events,b))
                signatures={};codes={}
                for x in range(1<<n):
                    signature=tuple(mv(C,evolve(x,events,w)) for w in ww)
                    z=mv(B,x)
                    assert z not in codes or codes[z]==signature
                    assert signature not in signatures or signatures[signature]==z
                    codes[z]=signature;signatures[signature]=z;states+=1
                assert len(signatures)==2**len(B)
                for A,a,c in events:
                    if c>b:continue
                    lookup={}
                    for x in range(1<<n):
                        z=mv(B,x);new=mv(spaces[b-c],mv(A,x)^a)
                        assert z not in lookup or lookup[z]==new
                        lookup[z]=new;updates+=1
            models+=1
    return dict(models=models,state_budget_comparisons=states,update_comparisons=updates)
def partitions(n,k):
    # Every unlabelled partition into at most k nonempty cells exactly once.
    def rec(a,largest):
        if len(a)==n:yield tuple(a);return
        for z in range(min(k-1,largest+1)+1):yield from rec(a+[z],max(largest,z))
    yield from rec([0],0)
def cover_count(values,w):
    covered=None;count=0
    for z in sorted(values):
        if covered is None or z>covered:count+=1;covered=z+w-1
    return count
def feasible(part,b,d,w):
    n=len(part)
    for t in range(-b,n):
        for a in set(part):
            ys={j for i in range(n) if part[i]==a and t<=i<=t+b for j in range(i-d,i+d+1)}
            if cover_count(ys,w)>2:return False
    return True
def timing_checks():
    cases=partition_checks=0
    for n in range(1,8):
        for k in [2,3]:
            pp=list(partitions(n,k))
            for b in range(1,6):
                for d in range(3):
                    ceildiv=lambda a,b:(a+b-1)//b
                    W=min(d+ceildiv(n,2*k),d+ceildiv(b,2*k-2),ceildiv(b+2*k*d,2*k-1))
                    found=False
                    for part in pp:
                        partition_checks+=1
                        if feasible(part,b,d,W):found=True;break
                    assert found,(n,k,b,d,W,'upper')
                    if W>1:
                        for part in pp:
                            partition_checks+=1
                            assert not feasible(part,b,d,W-1),(n,k,b,d,W,'lower',part)
                    cases+=1
    return dict(parameter_cases=cases,partition_checks=partition_checks,n_max=7,b_max=5,d_max=2,k=[2,3])
def intervals(n):return [tuple(range(i,j)) for i in range(n) for j in range(i+1,n+1)]
def score(x,a,I):return sum((x[i] for i in I),F(0))-a*len(I)
def robust_checks():
    comparisons=corners=0;n=3;ii=intervals(n)
    for x0 in product([0,1,2],repeat=n):
        x=tuple(map(F,x0))
        for a in [F(0),F(1,2),F(3,2)]:
            for delta,tau in [((F(1,4),)*3,F(0)),((F(1,10),F(1,5),F(0)),F(1,10))]:
                for I in ii:
                    sufficient=all(score(x,a,I)-score(x,a,J)>=sum((delta[i] for i in set(I)^set(J)),F(0))+tau*abs(len(I)-len(J)) for J in ii)
                    truth=True
                    for signs in product([-1,1],repeat=4):
                        xx=tuple(x[i]+signs[i]*delta[i] for i in range(3));aa=a+signs[3]*tau
                        truth &= all(score(xx,aa,I)>=score(xx,aa,J) for J in ii);corners+=1
                    assert sufficient==truth;comparisons+=1
    return dict(certificates= comparisons,corner_instances=corners,scope='Finite exact rational corner checks, not proof by enumeration')
def conflict_checks():
    cells=0
    for n in range(2,9):
        ii=intervals(n);best=[]
        for i in range(n):
            x=[int(j!=i) for j in range(n)];vals=[sum(x[j] for j in I)-2*len(I) for I in ii]
            winners={I for I,v in zip(ii,vals) if v==max(vals)}
            assert winners=={(j,) for j in range(n) if j!=i};best.append(winners)
        for mask in range(1,1<<n):
            joint=set(ii)
            for i in range(n):
                if mask>>i&1:joint &=best[i]
            assert bool(joint)==(mask!=(1<<n)-1);cells+=1
    return dict(n_max=8,nonempty_cells=cells)
def greedy_checks():
    rng=random.Random(82);checks=0
    for n in range(2,6):
        for _ in range(20):
            old=basis([rng.randrange(1<<n)]);rows=[rng.randrange(1<<n) for j in range(7)];costs=[rng.randrange(8) for j in rows]
            target=len(basis([*old,*rows]));current=old;total=0
            for i in sorted(range(7),key=lambda i:costs[i]):
                new=basis([*current,rows[i]])
                if len(new)>len(current):current=new;total+=costs[i]
            brute=min(sum(costs[i] for i in range(7) if mask>>i&1) for mask in range(128)
                      if len(basis([*old,*[rows[i] for i in range(7) if mask>>i&1]]))==target)
            assert total==brute;checks+=1
    return dict(instances=checks,subsets_per_instance=128)
def float_checks():
    g=lambda p,x:(1/64+p)-(p-x)
    a=g(.1,.1);b=g(.5,.1);assert a!=b
    for p in [F(.1),F(.5)]:assert (F(1,64)+p)-(p-F(.1))==F(1,64)+F(.1)
    return dict(first=a,second=b,first_hex=a.hex(),second_hex=b.hex(),scope='Observed Python binary64 operations; not all IEEE implementations')
def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--lean',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if not __debug__:
        p.error('Verification requires assertions. Run Python without -O or -OO.')
    if a.lean:
        a.lean = a.lean.resolve(strict=True)
    a.out.mkdir(parents=True,exist_ok=False)
    results={}
    for name,fn in [('affine',affine_checks),('timing',timing_checks),('robust',robust_checks),('conflict',conflict_checks),('measurement',greedy_checks),('floating_point',float_checks)]:
        results[name]=fn();print(name,json.dumps(results[name]),flush=True)
    if a.lean:
        receipts=[]
        for filename in ('Observation.lean', 'Policies.lean', 'Transfer.lean'):
            source = HERE / filename
            run=subprocess.run([str(a.lean),source.name],cwd=HERE,capture_output=True,text=True,encoding='utf-8',timeout=120)
            log = '\n'.join(stream.rstrip('\n') for stream in (run.stdout, run.stderr) if stream) + '\n'
            (a.out / (source.stem + '.log')).write_text(log, encoding='utf-8', newline='\n')
            assert run.returncode==0 and 'sorryAx' not in log
            assert not re.search(r'\b(sorry|admit|axiom|unsafe|native_decide)\b',source.read_text(encoding='utf-8'))
            axioms={name:[x.strip() for x in deps.split(',') if x.strip()] for name,deps in re.findall(r"'([^']+)' depends on axioms:\s*\[([^\]]*)\]",log,re.S)}
            for name in re.findall(r"'([^']+)' does not depend on any axioms",log):axioms[name]=[]
            requested = re.findall(r'^#print axioms (\w+)$', source.read_text(encoding='utf-8'), re.M)
            assert requested and sorted(requested) == sorted(name.rsplit('.',1)[-1] for name in axioms)
            assert all(set(v)<={'propext','Classical.choice','Quot.sound'} for v in axioms.values())
            receipts.append(dict(file=source.name,source_sha256=hashfile(source),log_sha256=hashfile(a.out/(source.stem+'.log')),declarations=len(axioms),axioms=axioms))
        results['lean']=dict(version=subprocess.run([str(a.lean),'--version'],capture_output=True,text=True,check=True).stdout.strip(),binary_sha256=hashfile(a.lean),receipts=receipts)
    results['status']='PASS';results['python']=platform.python_version();results['source_sha256']=hashfile(Path(__file__))
    (a.out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('PASS independent mathematical diagnostics')
if __name__=='__main__':main()
