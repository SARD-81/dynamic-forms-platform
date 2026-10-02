# BL-DATA-002 — Constraint Matrix

**Status:** FROZEN

Legend:

- **DB** — Django/PostgreSQL constraint/index
- **Service** — application business invariant
- **Permission** — authorization
- **Transaction** — atomic boundary
- **Test** — automated verification required

| Entity / Flow | Rule | DB | Service | Permission | Transaction | Test |
|---|---|:---:|:---:|:---:|:---:|:---:|
| User | email unique | ✓ |  |  |  | ✓ |
| OTPChallenge | attempt_count >= 0 | ✓ | ✓ |  |  | ✓ |
| OTPChallenge | expired/verified challenge rejected |  | ✓ |  |  | ✓ |
| core.Category | (owner, name) unique | ✓ | ✓ | ✓ |  | ✓ |
| Form | public_id unique | ✓ |  |  |  | ✓ |
| Form | PUBLIC/PRIVATE password consistency | ✓ | ✓ |  |  | ✓ |
| Form | owner-only definition management |  | ✓ | ✓ |  | ✓ |
| Form | schema immutable after publish |  | ✓ | ✓ | ✓ | ✓ |
| Form | CLOSED accepts no new Submission |  | ✓ |  | ✓ | ✓ |
| Form | close blocked while active run depends on it |  | ✓ | ✓ | ✓ | ✓ |
| Question | (form, order) unique | ✓ | ✓ |  |  | ✓ |
| Question | order >= 1 | ✓ | ✓ |  |  | ✓ |
| Question | numeric bounds valid | ✓ | ✓ |  |  | ✓ |
| QuestionOption | (question, order) unique | ✓ | ✓ |  |  | ✓ |
| QuestionOption | (question, label) unique | ✓ | ✓ |  |  | ✓ |
| QuestionOption | order >= 1 | ✓ | ✓ |  |  | ✓ |
| FormSubmission | required answers present |  | ✓ |  | ✓ | ✓ |
| FormSubmission | entire write atomic |  | ✓ |  | ✓ | ✓ |
| Answer | (submission, question) unique | ✓ | ✓ |  | ✓ | ✓ |
| Answer | question.form == submission.form |  | ✓ |  | ✓ | ✓ |
| Answer | representation matches question type |  | ✓ |  | ✓ | ✓ |
| AnswerOption | (answer, option) unique | ✓ | ✓ |  | ✓ | ✓ |
| AnswerOption | option.question == answer.question |  | ✓ |  | ✓ | ✓ |
| Process | PUBLIC/PRIVATE password consistency | ✓ | ✓ |  |  | ✓ |
| Process | owner-only definition management |  | ✓ | ✓ |  | ✓ |
| Process | schema immutable after publish |  | ✓ | ✓ | ✓ | ✓ |
| Process | CLOSED blocks new ProcessRun |  | ✓ |  | ✓ | ✓ |
| ProcessStep | (process, order) unique | ✓ | ✓ |  |  | ✓ |
| ProcessStep | (process, form) unique | ✓ | ✓ |  |  | ✓ |
| ProcessStep | order >= 1 | ✓ | ✓ |  |  | ✓ |
| ProcessStep | process.owner == form.owner |  | ✓ |  | ✓ | ✓ |
| ProcessStep | Form PUBLISHED at configuration |  | ✓ |  | ✓ | ✓ |
| ProcessStep | PUBLIC Process uses PUBLIC Form |  | ✓ |  | ✓ | ✓ |
| ProcessRun | public_id unique | ✓ |  |  |  | ✓ |
| ProcessRun | respondent XOR resume-token identity | ✓ | ✓ |  |  | ✓ |
| ProcessRun | non-null resume_token_hash unique | ✓ | ✓ |  |  | ✓ |
| ProcessRun | status/completed_at consistency | ✓ | ✓ |  | ✓ | ✓ |
| ProcessRun | complete only when all step runs complete |  | ✓ |  | ✓ | ✓ |
| ProcessStepRun | (process_run, process_step) unique | ✓ | ✓ |  |  | ✓ |
| ProcessStepRun | submission nullable + unique OneToOne | ✓ | ✓ |  |  | ✓ |
| ProcessStepRun | process_step.process == process_run.process |  | ✓ |  | ✓ | ✓ |
| ProcessStepRun | submission.form == process_step.form |  | ✓ |  | ✓ | ✓ |
| ProcessStepRun | COMPLETED => submission + completed_at | ✓ | ✓ |  | ✓ | ✓ |
| ProcessStepRun | LOCKED/AVAILABLE => no submission/completed_at | ✓ | ✓ |  | ✓ | ✓ |
| Linear Process | cannot skip incomplete previous step |  | ✓ |  | ✓ | ✓ |
| Free Process | incomplete steps may run in any order |  | ✓ |  | ✓ | ✓ |
| Step Completion | current Form availability re-checked |  | ✓ |  | ✓ | ✓ |
| Step Completion | submission + state transitions atomic |  | ✓ |  | ✓ | ✓ |
| ReportSubscription | EMAIL/API destination consistency | ✓ | ✓ | ✓ |  | ✓ |
| View Counter | atomic F() increment |  | ✓ |  | ✓ | ✓ |
| Time | timezone-aware persistence |  | ✓ |  |  | ✓ |

## Mandatory Service-only cross-table invariants

1. `ProcessStepRun.process_step.process_id == ProcessStepRun.process_run.process_id`
2. `ProcessStepRun.submission.form_id == ProcessStepRun.process_step.form_id`
3. `AnswerOption.option.question_id == Answer.question_id`
4. `Answer.question.form_id == FormSubmission.form_id`

## Required Django / migration mapping

Gate 2D/2E must implement and prove, at minimum:

- `UniqueConstraint(fields=["process_run", "process_step"], ...)`
- `OneToOneField(FormSubmission, null=True, ...)`
- `UniqueConstraint(fields=["answer", "option"], ...)`
- a row-local ProcessRun identity XOR `CheckConstraint`
- a conditional `UniqueConstraint` for non-null resume-token digest
- row-local ProcessRun/ProcessStepRun state consistency `CheckConstraint` rules
- `CheckConstraint(order__gte=1)` on Question, QuestionOption, and ProcessStep

The diagram may summarize these checks; the Django models and migrations must contain executable constraints, not comments.
