# Báo cáo cá nhân — Day 6

## 1. Dữ liệu và pipeline

### Chủ đề, nguồn/quyền, số trang và quy tắc tính trang

- **Chủ đề:** Thông số kỹ thuật của bộ vi xử lý AMD Ryzen, tập trung vào các dòng Ryzen 3, Ryzen 5, Ryzen 7 và Ryzen 9.
- **Nguồn:** Các trang thông số CPU Database trên TechPowerUp, được lưu dưới dạng HTML bằng tiện ích SingleFile.
- **Corpus:** 30 tài liệu HTML độc lập, tương ứng 30 trang sản phẩm CPU.
- **Quy tắc tính trang:** Với HTML, mỗi tài liệu được biểu diễn thành một `DocumentPage` có `page=1`. Đây là đơn vị nguồn có thể truy vết, không phải số trang vật lý như trong PDF.
- **Manifest:** Ghi nhận document ID, tiêu đề, đường dẫn, URL nguồn, phương pháp thu thập, thời điểm lưu, kích thước file và SHA256.
- **Tình trạng quyền:** Chưa xác minh giấy phép tái sử dụng nội dung. Dữ liệu được dùng trong phạm vi bài lab; không khẳng định đây là dữ liệu có giấy phép mở.

### Chuẩn hóa, lỗi và giới hạn

Pipeline ingestion hỗ trợ HTML và PDF.

Đối với HTML:
- Dùng `HTMLParser` để trích xuất nội dung văn bản.
- Loại bỏ các thành phần không cần thiết như script, style, iframe và navigation.
- Giữ lại cấu trúc cơ bản của nội dung như heading, paragraph, list và table.
- Chuẩn hóa Unicode NFC, newline, khoảng trắng và dòng trống.
- Lưu lại source path, title, loại tài liệu, số ký tự và trạng thái extraction.

Đối với PDF:
- Trích xuất văn bản theo từng trang bằng thư viện pypdf.

Lỗi và giới hạn:
- Một lỗi ingestion trước đó xảy ra do hàm chuẩn hóa trả về `None`; lỗi đã được sửa bằng cách trả về chuỗi đã chuẩn hóa.
- Corpus hiện chỉ gồm HTML từ một nguồn, cùng một nhóm chủ đề CPU.
- Nội dung HTML có thể chứa cấu trúc bảng không hoàn toàn đồng nhất.
- Metadata chuyên biệt được trích xuất từ văn bản đã ingestion; không thay đổi nội dung gốc.
- Corpus không đại diện cho nhiều nguồn hoặc nhiều lĩnh vực khác nhau.

### Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí

- **Embedding model:** `embeddinggemma-2`.
- **Provider/runtime:** llama.cpp server chạy local, sử dụng OpenAI-compatible API.
- **Endpoint:** `http://127.0.0.1:9931/v1`.
- **Số chiều:** 768, được phát hiện động từ embedding response, không hard-code trong chương trình.
- **Vector store:** PostgreSQL 16 + pgvector.
- **Database driver:** psycopg 3.3.8.
- **Similarity metric:** Cosine distance, truy vấn bằng toán tử `<=>` của pgvector; kết quả được biểu diễn thành score trong retrieval trace.
- **Chi phí API:** Không sử dụng API embedding trả phí trong pipeline hiện tại vì embedding chạy local.
- **Chi phí tính toán/điện năng:** Chưa đo.
- **Version llama.cpp và pgvector extension:** Cần ghi nhận chính xác từ môi trường chạy.

Lệnh chạy retrieval benchmark:

```powershell
python -m src.run
```

Lệnh kiểm tra metadata:

```powershell
python -m scripts.test_metadata_all
```

Lệnh kiểm tra embedding:

```powershell
python -m scripts.test_embeddings
```

Lệnh kiểm tra retrieval Q01:

```powershell
python -m scripts.inspect_q01_ranking
```

### Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn

Metadata được lưu cùng chunk, gồm:

- Metadata truy vết: `document_id`, `source`, `page`, `source_path`, `title`.
- Metadata CPU: `series`, `architecture`, `socket`, `codename`, `released`, `memory_type`, `memory_channels`, `memory_bandwidth`, `cache_l1`, `cache_l2`, `cache_l3`, `process_nm`, `base_clock_ghz`, `boost_clock_ghz`, `tdp_w`, `memory_speed_mts`, `cores`, `threads`, `ecc_memory`.

Các trường metadata lọc chính:
- `series`
- `architecture`

Nguồn giá trị là nội dung HTML gốc của TechPowerUp, được trích xuất bằng `metadata_cpu.py`.

Lý do chọn:
- `series` giúp giới hạn nhóm sản phẩm như Ryzen 3, Ryzen 5, Ryzen 7, Ryzen 9.
- `architecture` giúp giới hạn thế hệ kiến trúc như Zen 4 hoặc Zen 5.
- Hai trường có ý nghĩa trực tiếp với câu hỏi so sánh hoặc truy vấn có điều kiện.
- Các trường còn lại hỗ trợ traceability, mô tả và phân tích thông số.

Đã kiểm tra 30/30 tài liệu trích xuất thành công các trường bắt buộc gồm series, architecture, socket, codename, process_nm, tdp_w, cores, threads và ecc_memory.

---

## 2. Cấu hình và benchmark

### Ba chiến lược A / B / C

| Chiến lược | Phương pháp | Tham số |
|---|---|---|
| A | Fixed-size chunking | 1000 ký tự, overlap 150 ký tự |
| B | Paragraph-aware chunking | Kích thước tối đa 1000 ký tự |
| C | Paragraph-aware + metadata filter | Cùng chunks và embeddings với B; lọc metadata khi retrieval |

Số chunk sau khi chuẩn bị corpus:

| Strategy | Chunk count |
|---|---:|
| A | 274 |
| B | 270 |
| C | 270 |

Khác biệt duy nhất giữa B và C là metadata filtering ở thời điểm retrieval. C tái sử dụng chính xác chunks và embeddings của B để kiểm soát biến so sánh.

### Benchmark questions và cách kiểm chứng evidence

- Tổng số câu hỏi: 20.
- Dev: 15 câu.
- Test: 5 câu.
- Ngôn ngữ câu hỏi: Tiếng Việt.
- Các dạng câu hỏi gồm truy vấn trực tiếp, diễn đạt lại, câu hỏi có điều kiện và câu hỏi có điều kiện metadata.
- Mỗi câu có question ID, split, question, expected answer, gold source ID, gold page và evidence quote.
- Các câu hỏi metadata filter nằm trong nhóm test Q17–Q19:
  - Q17: lọc series Ryzen 7.
  - Q18: lọc Zen 5 và Ryzen 7.
  - Q19: lọc Zen 5 và Ryzen 9.
- Q20 kiểm tra thông tin ECC giữa hai CPU.

Evidence được kiểm chứng bằng cách:
1. Xác định document ID và page/unit tương ứng với gold source.
2. Kiểm tra Hit@1 dựa trên source/page của kết quả đầu tiên.
3. Kiểm tra Evidence Hit@3 bằng cách tìm tất cả evidence quote trong nội dung tối đa ba chunk đầu tiên thuộc gold source/page.
4. Yêu cầu tất cả evidence quote của câu hỏi phải xuất hiện; thiếu bất kỳ quote nào thì Evidence Hit@3 là False.

### Tiêu chí chọn chiến lược

Các tiêu chí so sánh gồm:
- Khả năng truy xuất đúng nguồn tại rank 1.
- Khả năng truy xuất đủ evidence trong top 3.
- Tính mạch lạc của chunk.
- Độ đầy đủ và chính xác của metadata.
- Khả năng tuân thủ metadata filter.
- Chất lượng grounding.
- Tài nguyên và độ phức tạp của pipeline.

Không chọn chiến lược chỉ dựa trên một chỉ số retrieval. Việc kết luận cuối cùng cần xét cả chất lượng evidence, khả năng truy vết và trade-off.

**Lưu ý:** Cần kiểm tra lại ghi chú/thời điểm chốt tiêu chí. Không khẳng định các tiêu chí này đã được chốt trước khi xem test nếu không có bằng chứng ghi nhận từ trước.

---

## 3. Kết quả

### Retrieval

Kết quả đã chạy trên 20 câu hỏi cho cả ba chiến lược.

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---:|---:|---:|---|---|
| A | Dev | 13/15 | 0/15 | 274 | Chưa đo | Local |
| A | Test | 2/5 | 0/5 | 274 | Chưa đo | Local |
| B | Dev | 13/15 | 0/15 | 270 | Chưa đo | Local |
| B | Test | 3/5 | 2/5 | 270 | Chưa đo | Local |
| C | Dev | 13/15 | 0/15 | 270 | Chưa đo | Local |
| C | Test | 3/5 | 2/5 | 270 | Chưa đo | Local |

Tổng hợp:
- A: Hit@1 = 15/20; Evidence Hit@3 = 0/20.
- B: Hit@1 = 16/20; Evidence Hit@3 = 2/20.
- C: Hit@1 = 16/20; Evidence Hit@3 = 2/20.

Các kết quả này cho thấy B tốt hơn A trên tập test hiện tại. C có kết quả giống B, chưa cho thấy lợi ích bổ sung của metadata filtering trên bộ câu hỏi này.

### Coherence, metadata và grounding

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 và trung bình /2 |
|---|---|---|---|---|
| A | Chưa chấm | Chưa chấm | N/A với câu không filter | Chưa chấm |
| B | Chưa chấm | Chưa chấm | N/A với câu không filter | Chưa chấm |
| C | Chưa chấm | Chưa chấm | Chưa tổng hợp | Chưa chấm |

Các hạng mục trên cần được đánh giá thủ công hoặc bằng báo cáo kiểm chứng riêng. Không suy ra điểm coherence, metadata hay grounding từ Hit@1 và Evidence Hit@3.

### Đường dẫn trace, nhãn thủ công và cách chọn mẫu

Các artifact hiện có:

```text
starter/
├── data/
│   └── benchmark_questions_vi.json
├── results/
│   ├── retrieval_traces.json
│   └── retrieval_summary.json
├── src/
│   ├── ingestion.py
│   ├── metadata_cpu.py
│   ├── chunking.py
│   ├── embeddings.py
│   ├── store.py
│   ├── evaluation.py
│   └── run.py
└── scripts/
```

- `retrieval_traces.json`: lưu kết quả retrieval từng câu hỏi và từng chiến lược.
- `retrieval_summary.json`: lưu kết quả tổng hợp Hit@1 và Evidence Hit@3.
- Nhãn coherence và grounding thủ công: chưa hoàn thành.
- Metadata completeness và filter compliance: cần tổng hợp từ top-3 retrieval traces.

Kế hoạch chọn mẫu thủ công:
- Coherence: chọn 10 vị trí nguồn giống nhau giữa A, B và C; đánh giá từng chunk theo thang 0–2.
- Grounding: đánh giá 5 câu test cho mỗi chiến lược theo thang 0–2.
- Metadata: kiểm tra các trường source, page và trường filter trong top 3.
- Filter compliance: kiểm tra từng kết quả C của câu có filter có đáp ứng đầy đủ điều kiện metadata hay không.

---

## 4. Phân tích và kết luận

### So sánh A–B và B–C

**A so với B:**

B sử dụng paragraph-aware chunking, trong khi A chia theo kích thước ký tự cố định. B tạo ra 270 chunks, ít hơn A với 274 chunks.

Trên test:
- Hit@1 của A: 2/5.
- Hit@1 của B: 3/5.
- Evidence Hit@3 của A: 0/5.
- Evidence Hit@3 của B: 2/5.

Kết quả quan sát cho thấy B có hiệu quả tốt hơn A trên tập test nhỏ hiện tại. Tuy nhiên, chưa thể khẳng định B luôn tốt hơn trong các corpus hoặc tập câu hỏi khác.

**B so với C:**

B và C dùng cùng chunks và embeddings. C chỉ bổ sung metadata filter ở retrieval.

Kết quả dev và test của B và C hiện giống nhau. Điều này cho thấy chưa quan sát được cải thiện metric tổng thể nhờ metadata filtering trên benchmark hiện tại.

Cần kiểm tra riêng filter compliance và các câu Q17–Q19 trước khi kết luận metadata filtering không hữu ích.

### Ví dụ lỗi 1 — Q01: tìm đúng nguồn nhưng không tìm đúng evidence

Q01 hỏi số nhân và số luồng của AMD Ryzen 3 8300G.

Cả A, B và C đều có Hit@1 = True nhưng Evidence Hit@3 = False.

- Gold source: `amd-ryzen-3-8300g`.
- Gold evidence: `# of Cores: 4` và `# of Threads: 8`.
- A xếp chunk `amd-ryzen-3-8300g-p1-fixed-3` ở rank 1; evidence nằm trong `fixed-5`.
- B/C xếp chunk `amd-ryzen-3-8300g-p1-paragraph-3` ở rank 1; evidence nằm trong `paragraph-5`.

Các chunk được xếp hạng cao có phần mô tả narrative liên quan đến 4 cores và 8 threads, nhưng không chứa đúng hai quote của gold evidence. Đây là ví dụ cho thấy tìm đúng document chưa đảm bảo tìm đúng evidence chunk.

### Ví dụ lỗi 2

Cần chọn thêm một câu hỏi có trace cho thấy:
- Hit@1 sai hoặc Evidence Hit@3 sai;
- Có thể xác định rõ gold source và chunk liên quan;
- Có thể giải thích nguyên nhân dựa trên nội dung thực tế của trace.

Không tự chọn một câu khác hoặc suy đoán nguyên nhân khi chưa kiểm tra trace.

### Chiến lược chọn, đánh đổi và điều kiện áp dụng

Kết quả ban đầu nghiêng về B vì:
- Có kết quả tốt hơn A trên test hiện tại.
- Cùng số lượng chunks và embeddings với C.
- Có cấu trúc chunk theo paragraph, thuận tiện cho việc giữ ngữ cảnh nội dung.

Tuy nhiên, cần hoàn thành đánh giá coherence, metadata và grounding trước khi đưa ra quyết định cuối cùng.

Trade-off:
- Fixed-size dễ cấu hình và kiểm soát kích thước chunk, nhưng có thể cắt qua ranh giới ngữ nghĩa.
- Paragraph-aware giữ cấu trúc nội dung tốt hơn, nhưng một số đoạn dài hoặc bảng có thể tạo chunk lớn hoặc lẫn nhiều trường.
- Metadata filtering có thể thu hẹp phạm vi retrieval theo điều kiện rõ ràng, nhưng phụ thuộc vào chất lượng metadata và độ chính xác của filter.

### Hạn chế

- Corpus chỉ gồm 30 trang sản phẩm CPU từ một nguồn.
- Quyền tái sử dụng nội dung chưa được xác minh.
- Bộ test chỉ có 5 câu, nên kết quả chưa đủ để khái quát hóa.
- Gold evidence dựa trên exact substring matching, không nhận diện các diễn đạt tương đương về mặt ngữ nghĩa.
- Thời gian chạy và chi phí tính toán chưa được đo.
- Chấm coherence, metadata và grounding thủ công chưa hoàn thành.
- Chưa có benchmark trên nhiều nguồn hoặc lĩnh vực khác nhau.
- Chưa có kết quả độc lập chứng minh metadata filtering cải thiện chất lượng retrieval.

### Nếu làm lại hoặc mở rộng

- Mở rộng corpus với nhiều nguồn và nhiều loại tài liệu hơn.
- Chuẩn hóa quy tắc evidence annotation để phân biệt exact evidence và acceptable equivalent evidence.
- Tăng số lượng test question nhưng vẫn giữ nguyên nguyên tắc không tuning trên test.
- Bổ sung thống kê filter compliance và metadata completeness.
- Đo riêng thời gian embedding, thời gian retrieval và tổng thời gian pipeline.
- Ghi nhận version đầy đủ của llama.cpp, pgvector và môi trường thực thi.
- Thử nghiệm các cấu hình chunking khác trên dev trước khi khóa cấu hình đánh giá cuối.
- Bổ sung các trường hợp retrieval sai để phân tích nguyên nhân theo từng loại câu hỏi.

---

## 5. Kết luận

Trong thử nghiệm hiện tại, paragraph-aware chunking (B) đạt kết quả tốt hơn fixed-size chunking (A) trên tập test 5 câu. Metadata filtering (C) chưa cho thấy cải thiện so với B về Hit@1 và Evidence Hit@3.

Kết quả Q01 cho thấy một vấn đề quan trọng: retrieval có thể tìm đúng tài liệu nhưng không đưa chunk chứa evidence cần thiết vào top 3. Vì vậy, đánh giá RAG không nên chỉ dựa trên việc tìm đúng document.

Các kết luận hiện tại chỉ áp dụng cho corpus, model, cấu hình và benchmark đã thử nghiệm. Cần hoàn thành đánh giá coherence, metadata và grounding trước khi xác nhận chiến lược cuối cùng.