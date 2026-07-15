# Synthetic document fixtures

Parser tests generate minimal PDF, DOCX, MD, TXT, XLSX, and PPTX files in pytest temporary directories. No real customer document or sensitive text is committed to the repository.

Each fixture contains a unique anchor and location metadata that the parser test can verify.
