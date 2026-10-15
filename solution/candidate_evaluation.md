# Đánh giá bản cải tiến

Bản gốc `defense.py` và báo cáo private có chữ ký được giữ nguyên.
`defense_candidate.py` là thử nghiệm riêng, chưa chạy private.

## Thay đổi

- Giữ các kiểm tra baseline, contract và lineage của bản gốc.
- Phát hiện độ lệch 2,5 sigma cho chỉ số có baseline hai phía.
- Với chỉ số chỉ có ngưỡng trên, học median/MAD riêng từng nguồn sau 12 quan sát.
- Dùng baseline làm sàn phương sai, loại vi phạm baseline khỏi mẫu tham chiếu,
  giới hạn lịch sử 128 mẫu và đánh giá sự kiện trước khi cập nhật lịch sử.
- Mỗi sự kiện vẫn chỉ gọi một tool; không dùng ID, seed hay nhãn để quyết định.

## Kết quả quan sát

| Báo cáo | Điểm | TPR | FPR | Credits / budget |
|---|---:|---:|---:|---:|
| practice_report.json | 50.0 | 100.00% | 0.00% | 180.0 / 220.0 |
| candidate_practice_report.json | 49.31 | 100.00% | 2.30% | 180.0 / 220.0 |
| public_report.json | 43.84 | 92.31% | 1.65% | 240.0 / 220.0 |
| candidate_public_report.json | 45.12 | 94.87% | 1.65% | 240.0 / 220.0 |

Public tăng 1,28 điểm, bắt thêm một lỗi; practice phát sinh hai báo nhầm.
Public vẫn vượt 20 credits vì cả hai bản đều kiểm tra toàn bộ sự kiện.
Đây là cải thiện quan sát được trên public, chưa chứng minh khả năng tổng quát
hoặc cải thiện private. Không hạ tiếp ngưỡng theo kết quả public.

Sáu kiểm thử mô phỏng độc lập xác minh cold start, tách nguồn, chống nhiễm
baseline bởi outlier, độ lệch hai phía, lỗi API và giới hạn bộ nhớ.
Chạy: `python solution/test_defense_candidate.py`.

Báo cáo private 31,48 là kết quả của bản gốc; không gán nó cho candidate.
Nếu được phép chấm phiên bản mới, cần đánh giá candidate trên một stream private
mới và tạo báo cáo tương ứng trước khi thay bộ nộp.

## Dấu vân tay mã nguồn tại thời điểm đánh giá

- `defense.py` SHA-256: `259eca298a286ebbfd48ccb9e164f0af91721061cdc6a9325731b1cfa0d946d6`
- `defense_candidate.py` SHA-256: `b09948c805d47a0a995c67d0e7b35d60e3e5dc4c7a14a0e3e69ad86b8b1732a4`
