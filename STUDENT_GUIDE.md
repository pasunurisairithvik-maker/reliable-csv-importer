# Learn and own this project
1. Run the example twice. Explain why accepted rows become skipped rows.
2. Read parse_rows, validate, import_csv, then the HTTP handlers in that order.
3. Understand a primary key, a transaction, parameterized SQL, and integer cents.
4. Run tests and deliberately break duplicate handling; observe the failing test.

## Two changes to implement yourself
- Add a category column, migrate the schema, and test missing/invalid categories.
- Add a download endpoint for rejected records, with a test verifying the exported report.

## Interview questions
Why not store price as a float? Why reject changed duplicate IDs? What happens on row 100 if the database fails? How is a malformed whole file different from one invalid row? What happens with two simultaneous uploads? How would PostgreSQL and streaming change the design?

## Truthful resume wording after understanding and contributing
Describe exactly what you implemented or improved, and cite actual tests/measurements. For example: "Extended a Python CSV import service with category validation and regression tests." Do not claim AWS, customers, scale, or improvements that you have not measured.
