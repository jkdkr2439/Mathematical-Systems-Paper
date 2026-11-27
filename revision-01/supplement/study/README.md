# Computational study accompanying section 22

The four endpoints are latency-window selection, import-window selection, reconstruction of a sampled integer and reproduction of a register output. All scripts use local inputs by default except the explicitly named source downloaders.

| Branch | Engine or observations | Recorded outcome |
|---|---|---|
| Server queue | SimPy 4.1.2 | 100 FIFO traces at three rounding levels, in [windows.jsonl](runs/01/windows.jsonl). |
| CDN replay | Wikimedia 2019 text-cache traces | 400 pilot batches and 1,800 held-out batches; [nine time slices and tolerance results](wikimedia-followup/results/summary.json). |
| Power | pandapower 3.5.6, included 33-bus case | 384 converged AC load flows, 24 synthetic demand profiles; window outcomes use the same file as the queue. |
| Sensor | ns.py 0.4.3 using SimPy | [2,304 protocol scenarios](runs/01/network.jsonl), covering 576 input triples for each schedule and load combination. |
| Hardware | PyRTL 1.0.3 | [1,280 trajectories](runs/01/hardware.jsonl) comparing a full 16-bit RTL model with a four-bit initial representation. |

The first two rows are two tests of the server-latency branch. The reference TTFB values are published observations. The power, network, register and FIFO workloads are computational examples. The JSON summaries and case packet accompany the written results. No human assessments have been collected.

## Reproduce

Use Python 3.12 with assertions enabled. The recorded environment was Windows with Python 3.12.10. From this directory in PowerShell run:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install --only-binary=:all: -r requirements.lock
.venv/Scripts/python.exe check_replay.py --out replay-new
```

Supply a new directory for each run. The final command works offline after installation. It compares every simulated trajectory, the CDN batch decisions, the selected case records and the CDN counts with the distributed outputs. Floating-point load-flow results may depend on the numerical environment. Runtime benchmarks are machine-dependent and are recorded separately. The [first benchmark](wikimedia-followup/results/benchmark.json) and [repeat](wikimedia-followup/replay/benchmark.json) are paired timings on the same machine.

For the CDN-only replay the standard library suffices:

```sh
python wikimedia-followup/analyze.py --out cdn-new
```

The [fixed study design](wikimedia-followup/design.json) precedes examination of the held-out data. The [pilot inputs](runs/wikimedia-pilot-01/) and [held-out inputs](wikimedia-followup/inputs/) store relative seconds and TTFB, with source locations and acquisition receipts. Day and hour are relative to the trace release. The holdout windows use days 02, 09 and 18 and cuts at hours 00, 08 and 16. For each cut use the first 9,600 records. Within a published second retain file order. The measurements were released by the Wikimedia Foundation. [Official data and schema](https://analytics.wikimedia.org/published/datasets/caching/2019/)

To acquire the inputs again, use a fresh copy of the supplement without the held-out input directory. Run `python wikimedia-followup/fetch.py` for the holdout. Run `python wikimedia_pilot.py --out new-pilot` for the pilot. The network-free replay is the default for checking this publication.

## Operator review

Open [the eight-case offline review packet](wikimedia-followup/results/review.html) in a browser. A reviewer records whether A and B indicate the same slow episode and whether switching windows changes the investigation. Either question permits “insufficient information.” The page exports the answers as JSON locally. Use [the assignment key](wikimedia-followup/results/review-key.json) after the assessment. The cases were chosen to illustrate disagreements and controls, so their frequencies do not estimate population frequencies.

## Hướng dẫn tiếng Việt

Chạy `check_replay.py` theo lệnh trên để đối chiếu các phép mô phỏng và log CDN với tệp đã phát hành. Bảng tổng hợp mô phỏng nằm trong [summary.json](runs/01/summary.json). Phần CDN dùng số liệu Wikimedia công bố, giữ riêng ba ngày để đối chiếu. Phiếu tám ca bằng tiếng Việt có thể mở và lưu câu trả lời ngay trên máy. Phần nghiên cứu hiện có dữ liệu về độ trễ, kết quả lựa chọn và thời gian tính; tác động đến quá trình điều tra sự cố còn chờ đánh giá thực tế.
