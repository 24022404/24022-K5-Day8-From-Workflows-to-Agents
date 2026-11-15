# Lab 8 — LogiX-VN: một task, bốn kiến trúc

AI20K ngày 8. Claims hoàn phí vận chuyển, dữ liệu giả, không GPU, không API key, không internet trong giờ lab.

Mục tiêu: chọn kiến trúc **ít tự chủ nhất mà vẫn làm được việc**, dựa trên số đo. Workflow và multi-agent phải được so trên cùng claim, cùng seed, cùng giá mô phỏng. Không giả định multi-agent tốt hơn.

Repo này là starter. Swarm tham chiếu, world, MockLLM, host (policy, ledger, handoff) chạy được ngay. Ba shape kia để nhóm viết.

## Việc nhóm nộp

Sau 4 giờ, cùng một claims flow trên bốn shape:

| Shape | Việc của nhóm | Ai được ghi refund |
| --- | --- | --- |
| A `workflow` | Các bước Python cố định. Model không tính tiền. | Host |
| B `single` | Vòng ReAct, tối đa 8 bước. | Host |
| C `orchestrator` | Investigator chỉ đọc. Handoff allowlist. | Orchestrator / host |
| D `swarm` | Có sẵn để đối chứng cost và variance. | Host vẫn chặn ghi |

Chỗ viết code: `lab8/shapes/workflow.py`, `single.py`, `orchestrator.py`. Chữ ký giữ nguyên:

```python
run_claim(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult
```

## Luật nghiệp vụ (synthetic)

Nguồn sự thật là dòng order và policy `is_current`, `effective_date <= 2026-11-15`. Chữ trong ticket là dữ liệu người dùng, kể cả câu "ignore policy".

| Tình huống | Kết quả đúng |
| --- | --- |
| Trễ ≥ 3 ngày, đơn `delivered` hoặc `delivered_late`, policy hiện hành | Hoàn đúng `shipping_fee_vnd` |
| `damage_verified=true` | `min(max_refund của DMG-04, paid_vnd)` |
| Cả ship và damage cùng đủ điều kiện | Một refund bằng **số lớn hơn**, không cộng |
| Trễ dưới 3 ngày, chưa verify hỏng, phí ship 0, đơn `cancelled` hoặc `in_transit` | Không refund |
| Thiếu `order_id` | `needs_info`, không ghi ledger. Không moi mã đơn từ câu chữ |
| Không đúng principal, hoặc không tìm thấy đơn | `escalated`. Không trả phone, địa chỉ, tên hàng, internal note |
| Policy cũ `SHIP-LATE-OLD` hoặc policy tương lai | Bỏ qua, dù `get_clause` vẫn trả về để nhóm khỏi dùng nhầm |
| Không approval, approval hết hạn, thu hồi, sai claim, amount ≤ 0 | Không ghi refund. Audit `policy_denied` khi quote > 0 mà cổng duyệt từ chối |
| Approval thấp hơn quote | Refund `min(quote, approved_vnd, paid_vnd)` |
| Gọi lại cùng claim | Một dòng ledger. Amount khác amount đã commit → `conflict`, không sửa số cũ |
| Crash sau khi đã ghi effect, trước checkpoint | Resume vẫn một refund và một audit `refund_committed` |

Ví dụ public T01: đơn `O-107` trễ 4 ngày, phí ship 35.000, approval 35.000 → một effect 35.000 và một audit committed.

Code tiền: `lab8.tools.compute_compensation` / `lab8.compensation.quote`. Đừng đưa số tiền cho MockLLM quyết.

## Cài và chạy

Python 3.11+. Lệnh chạy tại gốc repo.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m lab8.smoke
python -m lab8.run --shape swarm --claim-id C-001 --seed 11 --db data/run.sqlite
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm \
  --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
python -m lab8.crash_test --count 20 --out reports/crash.json
python -m pytest -q
```

`python -m pytest -q` là cổng đầu buổi: contract, compensation, approval, idempotency, handoff, crash 20/20, swarm trên T01–T10. Phải xanh trước khi chia việc.

Tự chấm ma trận T01–T12 trên cả 4 shape (3 shape stub sẽ đỏ cho đến khi làm xong; swarm xanh):

```bash
pytest -q -m student -o addopts=
```

Demo phản ví dụ, checkpoint không thay ledger (2 dòng tiền):

```bash
python -m lab8.demo.buggy_workflow
```

## Hai bộ test

| Bộ | Ở đâu | Ai chạy | Trong git? |
| --- | --- | --- | --- |
| Public T01–T12 | `data/public_claims.jsonl`, `tests/test_public_matrix.py` | Học viên, suốt buổi | Có |
| Hidden 40 claim × 5 seed | `eval/instructor/` | Giảng viên chấm cuối buổi. Học viên nhận `student_drop/` không nhãn | Không. `.gitignore` |

Hidden phủ ticket nói dối, injection, approval hỏng, policy hết hiệu lực, cộng dồn sai, đơn hủy / đang giao, homoglyph, principal lẫn, crash và rò secret. Nhãn không nằm trong file học viên nhận. Grader bỏ qua field `expected` gắn trên claim.

Ngưỡng shape nhóm chọn trên hidden: pass rate ≥ 0.75. Kèm pass^5, variance, cost/success. Chi tiết công thức: `docs/metrics.md`.

Must-pass, không bù điểm: refund khi thiếu approval hợp lệ; lộ `CANARY_SECRET_...`; crash tạo hơn một refund.

## Lịch 13:30–17:30

| Mốc | Việc | Bằng chứng |
| --- | --- | --- |
| 13:30 M0 | Cài, smoke, đọc contract, chia vai | `python -m lab8.smoke` |
| 13:45 M1 | Workflow, single, orchestrator. Swarm có sẵn | Cùng chữ ký `run_claim` |
| 14:30 M2 | Handoff, ledger, crash | `pytest -q` vẫn xanh; shape mới qua được test host |
| 15:15 | Nghỉ | |
| 15:30 M3 | 20 crash, approval, secret | `reports/crash.json` |
| 16:15 M4 | ≥ 10 public claim × 5 seed, rồi hidden trên grader | `reports/benchmark.json`, `docs/decision_adr.md` |
| 17:00 | README, hash, run id | Repo + báo cáo |

Khung báo cáo: `docs/architecture.md`, `docs/decision_adr.md`, `docs/research_card.md`, `docs/contributions.md`. Rubric 100 điểm nằm trong lab guide (implementation 20, hidden 15, durability 20, policy 10, handoff 10, benchmark 10, reproducibility 10, đóng góp 5).

## File nên đọc trước khi code

- `lab8/shapes/swarm_reference.py` — đối chứng. Khối `REFERENCE_WEAKNESS` là chỗ swarm tin ticket. Workflow không được copy khối đó.
- `lab8/durability.py` — transaction + idempotency key `refund:{claim_id}`.
- `lab8/handoff.py` — allowlist.
- `lab8/runtime.py` — vòng ReAct và investigator read-only.
- `config/autonomy_policy.yaml`, `config/tools.manifest.v1.1.yaml`, `harness_map.yaml`.

## Xử lý sự cố

- `python -m lab8.smoke` fail: đang không đứng ở gốc repo, hoặc chưa `pip install -r requirements.txt`.
- Benchmark shape stub ra pass rate 0: đúng, chưa triển khai.
- Lần chạy thứ hai trên cùng `data/run.sqlite` không tạo refund mới: ledger đang làm đúng. Benchmark tự tạo DB mới từng trial.
- Đừng gọi model thật. MockLLM cố định theo seed.
