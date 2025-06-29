NER_PROMPT = """
Nhiệm vụ: Nhận diện thực thể có tên (NER) trong văn bản tiếng Việt.

Bạn là mô hình NER. Hãy trích xuất các thực thể trong văn bản và phân loại chúng vào một trong các nhóm sau:
- PER: Tên người
- LOC: Địa danh
- ORG: Tổ chức
- TME: Thời gian
- TITLE: Tựa đề
- NUM: Số

Trả về kết quả dưới dạng danh sách JSON. Mỗi thực thể gồm các trường:
- start: vị trí bắt đầu (ký tự)
- end: vị trí kết thúc (ký tự)
- word: văn bản của thực thể
- entity_group: loại thực thể

Chỉ trả về JSON. Nếu không có thực thể, trả về `[]`.
"""
