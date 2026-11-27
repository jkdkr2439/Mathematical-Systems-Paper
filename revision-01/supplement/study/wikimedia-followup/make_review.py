"""Build a portable, offline human review packet. Run after analyze.py."""
from pathlib import Path
import hashlib
import html
import json
from math import log1p
from random import Random
from statistics import mean

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
cases=json.loads((OUT/'cases.json').read_text())
rng=Random(284911)
rng.shuffle(cases)
cards=[]
key={}
ns_ms=lambda ns: f'{ns/1e6:.6f}'.rstrip('0').rstrip('.')


def options(choices):
    return '<option value="">Chưa đánh giá</option>'+''.join(
        f'<option value="{value}">{text}</option>' for value,text in choices)


for index,c in enumerate(cases,1):
    name=f'W{index:02}'
    reverse=rng.choice([True,False])
    a,b=(c['reference'],c['selected']) if reverse else (c['selected'],c['reference'])
    vals=c['latency_ns']
    scale=log1p(max(vals)/1e6) or 1
    bars=[]
    for k,ns in enumerate(vals):
        height=100*log1p(ns/1e6)/scale
        desc=f'Yêu cầu {k+1}, giây {c["seconds"][k]}, TTFB {ns_ms(ns)} ms'
        bars.append(f'<div class="bar" title="{desc}" style="height:{height:.3f}%"></div>')
    time0,time1=c['seconds'][0],c['seconds'][-1]
    details=''.join(f'<tr><td>{k+1}</td><td>{t}</td><td>{ns_ms(v)}</td></tr>' for k,(t,v) in enumerate(zip(c['seconds'],vals)))
    cards.append(f'''<article data-case="{name}" id="{name}">
      <div class="head"><h2>Ca {name}</h2><span>Ngày {c['day']:02} · giờ {c['hour']:02} · nhóm {c['group']}</span></div>
      <p>48 yêu cầu theo thứ tự file · giây tương đối {time0}–{time1} · TTFB lớn nhất {ns_ms(max(vals))} ms.</p>
      <figure><div class="bars" aria-label="Độ trễ 48 yêu cầu">{''.join(bars)}</div>
      <div class="band"><span class="a" style="grid-column:{a+1} / span 6">A</span></div>
      <div class="band"><span class="b" style="grid-column:{b+1} / span 6">B</span></div>
      <figcaption>Trục ngang là số thứ tự yêu cầu từ 1 đến 48. A gồm yêu cầu {a+1}–{a+6}, B gồm {b+1}–{b+6}.</figcaption></figure>
      <div class="questions">
      <label>Hai cửa sổ có thuộc cùng một đợt chậm?<select name="episode">{options([('same','Cùng đợt'),('different','Khác đợt'),('unknown','Chưa đủ dữ liệu')])}</select></label>
      <label>Đổi từ A sang B có đổi hướng điều tra?<select name="action">{options([('same','Giữ hướng điều tra'),('different','Đổi hướng điều tra'),('unknown','Chưa đủ dữ liệu')])}</select></label></div>
      <label>Lý do hoặc thông tin còn thiếu<textarea name="reason" rows="2"></textarea></label>
      <details><summary>Xem số liệu từng yêu cầu</summary><table><thead><tr><th>Yêu cầu</th><th>Giây tương đối</th><th>TTFB (ms)</th></tr></thead><tbody>{details}</tbody></table></details>
    </article>''')
    key[name]={k:c[k] for k in ('reason','day','hour','group','regret_ns','overlap','margin_ns','split')}
    key[name]['selected_label']='B' if reverse else 'A'
fingerprint=hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Đánh giá cửa sổ độ trễ CDN</title><style>
*{box-sizing:border-box}body{max-width:850px;margin:0 auto;padding:32px 20px 64px;font:16px/1.5 "Source Sans 3",Arial,sans-serif;color:#202d38;background:#fafafa}
h1,h2{font-family:"STIX Two Text",Georgia,serif;line-height:1.15}h1{font-size:2.1rem;margin:0 0 .4em}h2{margin:0}
article{background:white;margin:22px 0;padding:22px;border:1px solid #cbd5dc;border-radius:5px}figure{margin:18px 0 12px}
.bars,.band{display:grid;grid-template-columns:repeat(48,minmax(0,1fr));gap:1px}.bars{height:86px;align-items:end;border-bottom:1px solid #647788}.bar{background:#516575;min-height:1px}.band{margin-top:4px}.band span{color:white;text-align:center;font-weight:700;line-height:1.35}.a{background:#146b70}.b{background:#81522c}figcaption,.head span{color:#485964;font-size:.9rem}
.head{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}.questions{display:grid;grid-template-columns:1fr 1fr;gap:18px}label{display:block;margin-top:12px}select,textarea{font:inherit;width:100%;margin-top:4px;border:1px solid #8395a1;border-radius:3px;padding:5px}details{margin-top:10px}table{width:100%;border-collapse:collapse}td,th{text-align:right;border-bottom:1px solid #ddd;padding:3px 8px}
button{font:inherit;font-weight:600;background:#194c58;color:white;padding:9px 18px;border:0;border-radius:4px;cursor:pointer}summary{cursor:pointer}@media(max-width:620px){.questions{grid-template-columns:1fr;gap:0}article{padding:14px}}
</style><main><h1>Đánh giá cửa sổ độ trễ CDN</h1>
<p>Với từng ca, so hai cửa sổ trên cùng trace và ghi lại quyết định như khi trực hệ thống. A và B được gán riêng cho từng ca. Nếu cần log ứng dụng hoặc thông tin hạ tầng để kết luận, hãy chọn “Chưa đủ dữ liệu”.</p>
<p>Chiều cao cột dùng thang log(1 + TTFB theo ms) để thấy cả đỉnh và nền. Mỗi biểu đồ có thang riêng. Có bảng số liệu chính xác dưới mỗi ca. Thời gian nguồn chỉ có độ phân giải một giây.</p>
''' + ''.join(cards) + '''
<button id="download">Lưu phiếu trả lời (.json)</button> <span id="status" role="status"></span>
<p>Phiếu hoạt động ngoại tuyến. Hãy tải câu trả lời trước khi đóng trang.</p></main><script>
document.querySelector('#download').onclick=()=>{
 const responses=[...document.querySelectorAll('article')].map(card=>({
   case_id:card.dataset.case,episode:card.querySelector('[name=episode]').value,
   action:card.querySelector('[name=action]').value,reason:card.querySelector('[name=reason]').value
 }));
 const blob=new Blob([JSON.stringify({packet:'PACKET_ID',responses},null,2)],{type:'application/json'});
 const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='cdn-feedback.json';a.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);document.querySelector('#status').textContent='Đã tạo tệp câu trả lời.';
};</script></html>'''
(OUT/'review.html').write_text(page.replace('PACKET_ID',fingerprint),encoding='utf-8')
(OUT/'review-key.json').write_text(json.dumps({'packet':fingerprint,'cases':key},indent=2),encoding='utf-8')
