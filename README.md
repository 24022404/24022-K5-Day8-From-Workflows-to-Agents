# Lab 8 — From Workflows to Agents (LogiX-VN: một task, bốn kiến trúc)

AI20K K5, ngày 8. Nhóm xử lý claim hoàn phí vận chuyển của công ty giả lập LogiX-VN bằng **bốn kiến trúc** (workflow, single agent, orchestrator, swarm), rồi dựa trên số đo để chọn kiến trúc **ít tự chủ nhất mà vẫn làm được việc**. Dữ liệu là dữ liệu giả. Không cần GPU, API key hay internet trong giờ lab; chạy được trên Windows, macOS và Linux.

**Loại bài:** Nhóm · **Thời lượng:** 4 giờ tại lớp (13:30–17:30) · **Deadline:** xem [SUBMISSION.md](SUBMISSION.md#deadline-gmt7)

## Mục tiêu học tập

- Cài cùng một claims flow theo bốn shape với cùng chữ ký `run_claim`, và hiểu ranh giới: tiền, approval, idempotency do **code** quyết; model chỉ đọc và soạn chữ.
- Làm cho thao tác ghi tiền an toàn khi chạy lại và khi crash: một claim chỉ có một refund, một audit `refund_committed`.
- Giữ ranh giới bảo mật giữa các agent: handoff theo allowlist, trace không lộ secret hay PII, ticket là dữ liệu chứ không phải lệnh.
- So sánh shape trên cùng claim, cùng seed, cùng bảng giá (pass rate, pass^5, variance, cost/success), rồi viết quyết định kiến trúc bằng số liệu thay vì mặc định "multi-agent tốt hơn".

## Việc nhóm làm

Repo này là starter. Các phần đã chạy được ngay: swarm tham chiếu, world, MockLLM, host (policy, ledger, handoff). Ba shape còn lại do nhóm viết.

| Shape | Việc của nhóm | Ai được ghi refund |
| --- | --- | --- |
| A `workflow` | Các bước Python cố định. Model không tính tiền | Host |
| B `single` | Vòng ReAct, tối đa 8 bước | Host |
| C `orchestrator` | Investigator chỉ đọc. Handoff theo allowlist | Orchestrator / host |
| D `swarm` | Có sẵn, dùng để đối chứng cost và variance | Host vẫn chặn ghi |

Code viết vào `src/lab8/shapes/workflow.py`, `single.py`, `orchestrator.py`. Đầu mỗi file có hướng dẫn từng bước. Giữ nguyên chữ ký hàm:

```python
run_claim(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult
```

## Thứ tự đọc

1. [RULES.md](RULES.md): dùng AI, liêm chính, file không được sửa, nộp muộn.
2. [CHECKPOINTS.md](CHECKPOINTS.md): 5 checkpoint theo lịch buổi lab và cách tự kiểm tra.
3. [src/README.md](src/README.md): cài đặt theo hệ điều hành, lệnh chạy, file được sửa.
4. [docs/business_rules.md](docs/business_rules.md) và [docs/contracts.md](docs/contracts.md): luật nghiệp vụ, `RunResult` và trace mà grader chấm.
5. [RUBRIC.md](RUBRIC.md): 100 điểm chính, must-pass, bonus ghi riêng.
6. [SUBMISSION.md](SUBMISSION.md): tên repo, deliverable, deadline, checklist.

Tài liệu thêm (kiến trúc, metric, bonus, xử lý sự cố): [docs/README.md](docs/README.md).

## Bắt đầu nhanh

Cần Python 3.11–3.13. **Mọi lệnh chạy trong thư mục `src/`.** Lệnh cho từng hệ điều hành (PowerShell, cmd, Git Bash) ở [src/README.md](src/README.md#cài-đặt-theo-hệ-điều-hành).

```bash
cd src
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m lab8.smoke
python -m pytest -q
```

Smoke đúng in ra `lab8.smoke pass`. `python -m pytest -q` (cổng host) phải xanh trước khi chia việc và giữ xanh suốt buổi.

## Cấu trúc repo

| Đường dẫn | Nội dung |
| --- | --- |
| `README.md`, `RULES.md`, `CHECKPOINTS.md`, `RUBRIC.md`, `SUBMISSION.md` | Đề bài, luật, checkpoint, cách chấm, cách nộp |
| `TEAM.md` | Thông tin nhóm, thành viên và **bảng đóng góp** (`check_submission` đọc bảng này) |
| `src/` | Code (`lab8/`), config, dữ liệu public, test, bằng chứng sinh ra (`src/reports/`) |
| `docs/` | Luật nghiệp vụ, contract, kiến trúc, metric, bonus, xử lý sự cố, ghi chú giảng viên |
| `report/team/` | Báo cáo nhóm, ADR, research card, báo cáo từng thành viên |
| `.github/workflows/ci.yml` | CI chạy smoke, pytest, crash suite và benchmark swarm trên 3 hệ điều hành |

## Báo cáo phải nộp

- `report/team/group_report.md`: báo cáo nhóm.
- `report/team/decision_adr.md` và `report/team/research_card.md`: hai file được `check_submission` đọc bằng máy; giữ nguyên tên và các dòng nhãn.
- Mỗi thành viên copy `report/team/MSSV_HoTen.md` thành file riêng đặt tên theo MSSV và họ tên không dấu, ví dụ `report/team/20241234_NguyenVanAn.md`.
- `TEAM.md`: điền thông tin nhóm và bảng đóng góp.

Chi tiết: [SUBMISSION.md](SUBMISSION.md).
