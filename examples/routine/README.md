# Demo examples — ROUTINE risk

All content here is **fictional and de-identified**. No real names, phone
numbers, email addresses, student IDs, or contact details appear anywhere in
this repository.

Load one from the UI via **Load example**, or from the API:

```bash
curl http://localhost:8000/api/examples
curl -X POST http://localhost:8000/api/messages \
  -H 'Content-Type: application/json' \
  -d @examples/routine/curriculum_night.json
```

| File | Scenario | Risk |
| --- | --- | --- |
| `curriculum_night.json` | Family Curriculum Night invitation + RSVP deadline | routine |
| `permission_form_reminder.json` | Field trip permission form deadline | routine |
| `book_drive_volunteer.json` | Book fair volunteer sign-up | routine |
| `second_topic_attendance.json` | Second, unrelated routine message (proves reuse) | routine |
