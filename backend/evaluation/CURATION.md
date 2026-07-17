# Retrieval Evaluation Curation Guide

The committed dataset is versioned independently from reports. Each question must identify its video, question and source languages, case type, exact relevant segment IDs, and either reviewed evidence or an explicit unanswerable label.

Reviewers inspect the immutable segment text rather than model output. A relevant label is accepted only when the segment directly supports the question; multi-evidence questions list every minimum supporting segment. Unanswerable labels require checking the complete video fixture. Dataset changes increment `version`, regenerate both reports, and record the dataset SHA-256.

Required coverage is Vietnamese and English same-language retrieval, both cross-language directions, keywords, paraphrases, multi-evidence questions, and unanswerable questions. Synthetic model labels may be proposed but cannot use `review.status=reviewed` until a source-text inspection is recorded in `review.rationale`.
